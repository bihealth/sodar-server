"""SODAR Django site tasks for Taskflow"""

import logging

from taskflowbackend.tasks.base_task import BaseTask


logger = logging.getLogger('__name__')


class SODARBaseTask(BaseTask):
    """Base taskflow SODAR task"""

    def __init__(
        self, name, project, force_fail=False, inject=None, *args, **kwargs
    ):
        super().__init__(
            name, force_fail=force_fail, inject=inject, *args, **kwargs
        )
        self.target = 'sodar'
        self.name = '<SODAR> {} ({})'.format(name, self.__class__.__name__)
        self.project = project

    '''
    def execute(self, *args, **kwargs):
        # Raise Exception for testing revert()
        # NOTE: This doesn't work if done in pre_execute() or post_execute()
        if self.force_fail:
            raise Exception('force_fail=True')

    def post_execute(self, *args, **kwargs):
        logger.info(
            '{}: {}'.format(
                'force_fail' if self.force_fail else 'Executed', self.name
            )
        )

    def post_revert(self, *args, **kwargs):
        logger.error('Reverted: {}'.format(self.name))
    '''
