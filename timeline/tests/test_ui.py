"""UI tests for the timeline app"""

from django.conf import settings
from django.urls import reverse

# Projectroles dependency
from projectroles.models import Role, OMICS_CONSTANTS
from projectroles.plugins import get_backend_api
from projectroles.tests.test_models import ProjectMixin, RoleAssignmentMixin
from projectroles.tests.test_ui import TestUIBase, LiveUserMixin

from .test_models import TestProjectEventBase, ProjectEventMixin,\
    ProjectEventStatusMixin


# Omics settings
PROJECT_ROLE_OWNER = OMICS_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_ROLE_DELEGATE = OMICS_CONSTANTS['PROJECT_ROLE_DELEGATE']
PROJECT_ROLE_CONTRIBUTOR = OMICS_CONSTANTS['PROJECT_ROLE_CONTRIBUTOR']
PROJECT_ROLE_GUEST = OMICS_CONSTANTS['PROJECT_ROLE_GUEST']
PROJECT_ROLE_STAFF = OMICS_CONSTANTS['PROJECT_ROLE_STAFF']
PROJECT_TYPE_CATEGORY = OMICS_CONSTANTS['PROJECT_TYPE_CATEGORY']
PROJECT_TYPE_PROJECT = OMICS_CONSTANTS['PROJECT_TYPE_PROJECT']


class TestListView(
        TestUIBase, ProjectEventMixin, ProjectEventStatusMixin):
    """Tests for the timeline list view UI"""

    def setUp(self):
        super(TestListView, self).setUp()

        self.timeline = get_backend_api('timeline_backend')

        # Init default event
        self.event = self.timeline.add_event(
            project=self.project,
            app_name='projectroles',
            user=self.superuser,
            event_name='test_event',
            description='description',
            extra_data={'test_key': 'test_val'},
            status_type='OK')

        # Init classified event
        self.classified_event = self.timeline.add_event(
            project=self.project,
            app_name='projectroles',
            user=self.superuser,
            event_name='classified_event',
            description='description',
            extra_data={'test_key': 'test_val'},
            classified=True)

    def test_event_visibility(self):
        """Test visibility of events in the timeline event list"""
        expected = [
            (self.superuser, 2),
            (self.as_owner.user, 2),
            (self.as_delegate.user, 2),
            (self.as_staff.user, 1),
            (self.as_contributor.user, 1),
            (self.as_guest.user, 1)]

        url = reverse('project_timeline', kwargs={'project': self.project.pk})
        self.assert_element_count(expected, url, 'omics-tl-list-event')

    def test_event_visibility_details(self):
        """Test visibility of events on the project details page"""
        expected = [
            (self.superuser, 1),
            (self.as_owner.user, 1),
            (self.as_delegate.user, 1),
            (self.as_staff.user, 1),
            (self.as_contributor.user, 1),
            (self.as_guest.user, 1)]

        url = reverse('project_detail', kwargs={'pk': self.project.pk})
        self.assert_element_count(expected, url, 'omics-tl-list-event')
