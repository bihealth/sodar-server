import logging
from taskflow import task


logger = logging.getLogger('taskflowbackend.tasks')


class ForceFailException(Exception):
    pass


class BaseTask(task.Task):
    """Common base task"""

    def __init__(
        self, name, force_fail=False, verbose=True, inject=None, *args, **kwargs
    ):
        super().__init__(name, inject=inject)
        self.name = name
        self.force_fail = force_fail
        self.verbose = verbose
        self.data_modified = False
        self.execute_data = {}

    def execute(self, *args, **kwargs):
        # Raise Exception for testing revert()
        # NOTE: This doesn't work if done in pre_execute() or post_execute()
        if self.force_fail:
            raise ForceFailException

    def post_execute(self, *args, **kwargs):
        if self.verbose:
            logger.info(
                '{}: {}'.format(
                    'force_fail' if self.force_fail else 'Executed', self.name
                )
            )

    def post_revert(self, *args, **kwargs):
        if self.verbose:
            logger.info('Reverted: {}'.format(self.name))
