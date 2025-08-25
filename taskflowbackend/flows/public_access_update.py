from django.conf import settings

from taskflowbackend.flows.base_flow import BaseLinearFlow
from taskflowbackend.tasks import irods_tasks


PUBLIC_GROUP = 'public'


class Flow(BaseLinearFlow):
    """Flow for granting or revoking public access in a collection"""

    def validate(self):
        self.required_fields = ['path', 'access']
        self.require_lock = False  # Project lock not required for this flow
        return super().validate()

    def build(self, force_fail=False):
        access_name = 'read' if self.flow_data['access'] else 'null'
        ticket_str = self.flow_data.get('ticket_str')

        self.add_task(
            irods_tasks.SetAccessTask(
                name='Set collection user group access',
                irods=self.irods,
                inject={
                    'access_name': access_name,
                    'path': self.flow_data['path'],
                    'user_name': PUBLIC_GROUP,
                    'irods_backend': self.irods_backend,
                },
                force_fail=force_fail if not ticket_str else False,
            )
        )
        # Update access ticket depending on anonymous accesss
        if (
            self.flow_data['access']
            and settings.PROJECTROLES_ALLOW_ANONYMOUS
            and ticket_str
        ):
            self.add_task(
                irods_tasks.IssueTicketTask(
                    name=f'Issue access ticket "{ticket_str}" for collection',
                    irods=self.irods,
                    inject={
                        'access_name': access_name,
                        'path': self.flow_data['path'],
                        'ticket_str': ticket_str,
                        'irods_backend': self.irods_backend,
                    },
                    force_fail=force_fail,
                )
            )
        elif ticket_str:
            self.add_task(
                irods_tasks.DeleteTicketTask(
                    name=f'Delete access ticket "{ticket_str}" from collection',
                    irods=self.irods,
                    inject={
                        'access_name': access_name,
                        'path': self.flow_data['path'],
                        'ticket_str': ticket_str,
                        'irods_backend': self.irods_backend,
                    },
                    force_fail=force_fail,
                )
            )
