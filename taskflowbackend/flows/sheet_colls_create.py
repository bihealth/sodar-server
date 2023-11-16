import os

from django.conf import settings

# Samplesheets dependency
from samplesheets import tasks_taskflow as ss_tasks

from taskflowbackend.flows.base_flow import BaseLinearFlow
from taskflowbackend.tasks import irods_tasks


PUBLIC_GROUP = 'public'


class Flow(BaseLinearFlow):
    """Flow for creating a directory structure for a sample sheet in iRODS"""

    def validate(self):
        self.required_fields = ['colls']
        return super().validate()

    def build(self, force_fail=False):
        sample_path = self.irods_backend.get_sample_path(self.project)
        project_group = self.irods_backend.get_user_group_name(self.project)
        access_lookup = self.irods_backend.get_access_lookup(self.irods)

        self.add_task(
            irods_tasks.CreateCollectionTask(
                name='Create collection for sample sheet samples',
                irods=self.irods,
                inject={'path': sample_path},
            )
        )
        self.add_task(
            irods_tasks.SetInheritanceTask(
                name='Set inheritance for sample sheet collection {}'.format(
                    sample_path
                ),
                irods=self.irods,
                inject={'path': sample_path, 'inherit': True},
            )
        )
        self.add_task(
            irods_tasks.SetAccessTask(
                name='Set project user group read access for sample sheet '
                'collection {}'.format(sample_path),
                irods=self.irods,
                inject={
                    'access_name': 'read',
                    'path': sample_path,
                    'user_name': project_group,
                    'access_lookup': access_lookup,
                    'irods_backend': self.irods_backend,
                },
            )
        )
        for c in self.flow_data['colls']:
            coll_path = os.path.join(sample_path, c)
            self.add_task(
                irods_tasks.CreateCollectionTask(
                    name='Create collection {}'.format(coll_path),
                    irods=self.irods,
                    inject={'path': coll_path},
                )
            )
        # If project is public, add public access to sample repository
        if self.project.public_guest_access:
            self.add_task(
                irods_tasks.SetAccessTask(
                    name='Set public access to sample collection',
                    irods=self.irods,
                    inject={
                        'access_name': 'read',
                        'path': sample_path,
                        'user_name': PUBLIC_GROUP,
                        'access_lookup': access_lookup,
                        'irods_backend': self.irods_backend,
                    },
                )
            )
        # Create access ticket depending on anonymous accesss
        if (
            self.project.public_guest_access
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
                        'access_name': 'read',
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
