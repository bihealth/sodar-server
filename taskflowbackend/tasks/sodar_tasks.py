"""SODAR tasks for Taskflow"""

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
        self.name = '<SODAR> {} ({})'.format(name, self.__class__.__name__)
        self.project = project
