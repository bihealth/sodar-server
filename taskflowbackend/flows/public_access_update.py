from config import settings

from .base_flow import BaseLinearFlow

# from apis.irods_utils import get_project_path, get_project_group_name
from tasks import irods_tasks


PROJECT_ROOT = settings.TASKFLOW_IRODS_PROJECT_ROOT
PUBLIC_GROUP = 'public'


class Flow(BaseLinearFlow):
    """Flow for granting or revoking public access in a collection"""

    def validate(self):
        self.required_fields = [
            'path',
            'access',
        ]
        return super().validate()

    def build(self, force_fail=False):

        ########
        # Setup
        ########
        access_name = 'read' if self.flow_data['access'] else 'null'

        ##############
        # iRODS Tasks
        ##############

        self.add_task(
            irods_tasks.SetAccessTask(
                name='Set collection user group access',
                irods=self.irods,
                inject={
                    'access_name': access_name,
                    'path': self.flow_data['path'],
                    'user_name': PUBLIC_GROUP,
                },
            )
        )
