"""Tests for views in the timeline app"""

from django.core.urlresolvers import reverse

# Projectroles dependency
from projectroles.models import Role, OMICS_CONSTANTS
from projectroles.plugins import get_backend_api
from projectroles.tests.test_models import ProjectMixin, RoleAssignmentMixin

from .test_models import TestProjectEventBase, ProjectEventMixin,\
    ProjectEventStatusMixin


# Omics constants
PROJECT_ROLE_OWNER = OMICS_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_ROLE_DELEGATE = OMICS_CONSTANTS['PROJECT_ROLE_DELEGATE']
PROJECT_ROLE_CONTRIBUTOR = OMICS_CONSTANTS['PROJECT_ROLE_CONTRIBUTOR']
PROJECT_ROLE_GUEST = OMICS_CONSTANTS['PROJECT_ROLE_GUEST']
PROJECT_ROLE_STAFF = OMICS_CONSTANTS['PROJECT_ROLE_STAFF']
PROJECT_TYPE_CATEGORY = OMICS_CONSTANTS['PROJECT_TYPE_CATEGORY']
PROJECT_TYPE_PROJECT = OMICS_CONSTANTS['PROJECT_TYPE_PROJECT']


class TestViewsBase(
        TestProjectEventBase, ProjectEventMixin, ProjectEventStatusMixin,
        ProjectMixin, RoleAssignmentMixin):
    """Base class for view testing"""

    def setUp(self):
        super(TestViewsBase, self).setUp()
        self.timeline = get_backend_api('timeline_backend')

        # Init roles
        self.role_owner = Role.objects.get_or_create(
            name=PROJECT_ROLE_OWNER)[0]
        self.role_delegate = Role.objects.get_or_create(
            name=PROJECT_ROLE_DELEGATE)[0]
        self.role_staff = Role.objects.get_or_create(
            name=PROJECT_ROLE_STAFF)[0]
        self.role_contributor = Role.objects.get_or_create(
            name=PROJECT_ROLE_CONTRIBUTOR)[0]
        self.role_guest = Role.objects.get_or_create(
            name=PROJECT_ROLE_GUEST)[0]

        # Init superuser
        self.user = self.make_user('superuser')
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save()

        # Init project
        self.project = self._make_project(
            'TestProject', PROJECT_TYPE_PROJECT, None)
        self.owner_as = self._make_assignment(
            self.project, self.user, self.role_owner)

        # Init default event
        self.event = self.timeline.add_event(
            project=self.project,
            app_name='projectroles',
            user=self.user,
            event_name='test_event',
            description='description',
            extra_data={'test_key': 'test_val'})


class TestListView(TestViewsBase):
    """Tests for the timeline list view"""

    def test_render(self):
        """Test to ensure the home view renders correctly"""
        with self.login(self.user):
            response = self.client.get(
                reverse('project_timeline',
                kwargs={'project': self.project.pk}))
            self.assertEqual(response.status_code, 200)


class TestTaskflowSetStatusAPIView(TestViewsBase):
    """Tests for the taskflow status setting API view"""

    def setUp(self):
        super(TestTaskflowSetStatusAPIView, self).setUp()

        # Init default event
        self.event_init = self.timeline.add_event(
            project=self.project,
            app_name='projectroles',
            user=self.user,
            event_name='test_event',
            description='description',
            extra_data={'test_key': 'test_val'},
            status_type='INIT')

    def test_set_status(self):
        """Test setting the status of the event"""
        values = {
            'event_pk': self.event_init.pk,
            'status_type': 'OK',
            'status_desc': ''}

        response = self.client.post(
            reverse('taskflow_timeline_event_status_set'),
            values)

        self.assertEqual(response.status_code, 200)

    def test_set_invalid_event(self):
        """Test setting the status of the event with an invalid event pk"""
        values = {
            'event_pk': self.event_init.pk + 1,
            'status_type': 'OK',
            'status_desc': ''}

        response = self.client.post(
            reverse('taskflow_timeline_event_status_set'),
            values)

        self.assertEqual(response.status_code, 404)

    def test_set_invalid_status(self):
        """Test setting the status of the event with an invalid status type"""
        values = {
            'event_pk': self.event_init.pk,
            'status_type': 'ahL4VeerAeth4ohh',
            'status_desc': ''}

        response = self.client.post(
            reverse('taskflow_timeline_event_status_set'),
            values)

        self.assertEqual(response.status_code, 400)
