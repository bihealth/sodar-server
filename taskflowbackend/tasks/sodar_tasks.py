"""SODAR tasks for Taskflow"""

import logging

from copy import deepcopy

from taskflowbackend.tasks.base_task import BaseTask


logger = logging.getLogger(__name__)


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


class TimelineEventExtraDataUpdateTask(SODARBaseTask):
    """
    Task for TimelineEvent extra data updating. Updates existing extra data
    with the provided dictionary. May overwrite data in case of identical keys.
    """

    og_data = {}

    def execute(self, tl_event, extra_data, *args, **kwargs):
        # Store original data for revert
        self.og_data = deepcopy(tl_event.extra_data)
        data = tl_event.extra_data.copy()
        data.update(extra_data)
        tl_event.extra_data = data
        tl_event.save()
        self.data_modified = True
        super().execute(*args, **kwargs)

    def revert(self, tl_event, extra_data, *args, **kwargs):
        if self.data_modified:
            tl_event.extra_data = self.og_data
            tl_event.save()
