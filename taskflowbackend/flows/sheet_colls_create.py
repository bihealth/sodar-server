from irods.path import iRODSPath

from django.conf import settings

# Projectroles dependency
from projectroles.models import SODAR_CONSTANTS

# Samplesheets dependency
from samplesheets import tasks_taskflow as ss_tasks

from taskflowbackend.constants import (
    IRODS_ACCESS_READ_OBJ,
    IRODS_TICKET_MODE_READ,
    IRODS_GROUP_PUBLIC,
)
from taskflowbackend.flows.base_flow import BaseLinearFlow
from taskflowbackend.tasks import irods_tasks


# SODAR constants
PROJECT_ROLE_GUEST = SODAR_CONSTANTS['PROJECT_ROLE_GUEST']


class Flow(BaseLinearFlow):
    """Flow for creating a directory structure for a sample sheet in iRODS"""

    def validate(self) -> bool:
        self.required_fields = ['colls']
        return super().validate()

    def build(self, force_fail: bool = False):
        sample_path = self.irods_backend.get_sample_path(self.project)
        project_group = self.irods_backend.get_group_name(self.project)

        self.add_task(
            irods_tasks.CreateCollectionTask(
                name='Create collection for sample sheet samples',
                irods=self.irods,
                inject={'path': sample_path},
            )
        )
        self.add_task(
            irods_tasks.SetInheritanceTask(
                name=f'Set inheritance for sample sheet collection '
                f'{sample_path}',
                irods=self.irods,
                inject={'path': sample_path, 'inherit': True},
            )
        )
        self.add_task(
            irods_tasks.SetAccessTask(
                name=f'Set project user group read_object access for sample '
                f'sheet collection {sample_path}',
                irods=self.irods,
                inject={
                    'access_name': IRODS_ACCESS_READ_OBJ,
                    'path': sample_path,
                    'user_name': project_group,
                    'irods_backend': self.irods_backend,
                },
            )
        )
        for c in self.flow_data['colls']:
            coll_path = iRODSPath(sample_path, c)
            self.add_task(
                irods_tasks.CreateCollectionTask(
                    name=f'Create collection {coll_path}',
                    irods=self.irods,
                    inject={'path': coll_path},
                )
            )
        # If project is public, add public access to sample repository
        if self.project.get_public_access_name() == PROJECT_ROLE_GUEST:
            self.add_task(
                irods_tasks.SetAccessTask(
                    name='Set public read_object access to sample collection',
                    irods=self.irods,
                    inject={
                        'access_name': IRODS_ACCESS_READ_OBJ,
                        'path': sample_path,
                        'user_name': IRODS_GROUP_PUBLIC,
                        'irods_backend': self.irods_backend,
                    },
                )
            )
        # Create access ticket depending on anonymous accesss
        if (
            self.project.get_public_access_name() == PROJECT_ROLE_GUEST
            and settings.PROJECTROLES_ALLOW_ANONYMOUS
            and self.flow_data.get('ticket_str')
        ):
            self.add_task(
                irods_tasks.IssueTicketTask(
                    name='Issue access ticket "{}" for collection'.format(
                        self.flow_data['ticket_str']
                    ),
                    irods=self.irods,
                    inject={
                        'access_name': IRODS_TICKET_MODE_READ,
                        'path': sample_path,
                        'ticket_str': self.flow_data['ticket_str'],
                        'irods_backend': self.irods_backend,
                    },
                )
            )
        self.add_task(
            ss_tasks.SetIrodsCollStatusTask(
                name='Set iRODS collection structure status to True',
                project=self.project,
                inject={'irods_status': True},
                force_fail=force_fail,
            ),
        )
