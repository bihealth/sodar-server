"""Tests for the API in the timeline app"""

from django.forms.models import model_to_dict
from django.urls import reverse

# Projectroles dependency
from projectroles.models import OMICS_CONSTANTS
from projectroles.plugins import get_backend_api

from .test_models import TestProjectEventBase, ProjectEventMixin,\
    ProjectEventStatusMixin
from ..models import ProjectEvent, ProjectEventStatus, ProjectEventObjectRef,\
    DEFAULT_MESSAGES


# Global constants from settings
PROJECT_ROLE_OWNER = OMICS_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_ROLE_DELEGATE = OMICS_CONSTANTS['PROJECT_ROLE_DELEGATE']
PROJECT_ROLE_CONTRIBUTOR = OMICS_CONSTANTS['PROJECT_ROLE_CONTRIBUTOR']
PROJECT_ROLE_GUEST = OMICS_CONSTANTS['PROJECT_ROLE_GUEST']
PROJECT_ROLE_STAFF = OMICS_CONSTANTS['PROJECT_ROLE_STAFF']
PROJECT_TYPE_CATEGORY = OMICS_CONSTANTS['PROJECT_TYPE_CATEGORY']
PROJECT_TYPE_PROJECT = OMICS_CONSTANTS['PROJECT_TYPE_PROJECT']


class TestTimelineAPI(
        TestProjectEventBase, ProjectEventMixin, ProjectEventStatusMixin):

    def setUp(self):
        super(TestTimelineAPI, self).setUp()
        self.timeline = get_backend_api('timeline_backend')

        # Init user
        # self.user = self.make_user('user')

    def test_add_event(self):
        """Test adding an event"""

        # Assert precondition
        self.assertEqual(ProjectEvent.objects.all().count(), 0)
        self.assertEqual(ProjectEventStatus.objects.all().count(), 0)

        event = self.timeline.add_event(
            project=self.project,
            app_name='projectroles',
            user=self.user_owner,
            event_name='test_event',
            description='description',
            extra_data={'test_key': 'test_val'})

        # Assert object status after insert
        self.assertEqual(ProjectEvent.objects.all().count(), 1)
        self.assertEqual(ProjectEventStatus.objects.all().count(), 1)  # Init

        expected = {
            'id': event.pk,
            'project': self.project.pk,
            'app': 'projectroles',
            'user': self.user_owner.pk,
            'event_name': 'test_event',
            'description': 'description',
            'classified': False,
            'extra_data': {'test_key': 'test_val'},
            'omics_uuid': event.omics_uuid}

        self.assertEqual(model_to_dict(event), expected)

        # Test Init status
        status = event.get_current_status()

        expected_status = {
            'id': status.pk,
            'event': event.pk,
            'status_type': 'INIT',
            'description': DEFAULT_MESSAGES['INIT'],
            'extra_data': {}}

        self.assertEqual(model_to_dict(status), expected_status)

    def test_add_event_with_status(self):
        """Test adding an event with status"""

        # Assert preconditions
        self.assertEqual(ProjectEvent.objects.all().count(), 0)
        self.assertEqual(ProjectEventStatus.objects.all().count(), 0)

        event = self.timeline.add_event(
            project=self.project,
            app_name='projectroles',
            user=self.user_owner,
            event_name='test_event',
            description='description',
            extra_data={'test_key': 'test_val'},
            status_type='OK',
            status_desc='OK',
            status_extra_data={})

        status = event.get_current_status()

        # Assert object status after insert
        self.assertEqual(ProjectEvent.objects.all().count(), 1)
        self.assertEqual(ProjectEventStatus.objects.all().count(), 2)

        expected_event = {
            'id': event.pk,
            'project': self.project.pk,
            'app': 'projectroles',
            'user': self.user_owner.pk,
            'event_name': 'test_event',
            'description': 'description',
            'classified': False,
            'extra_data': {'test_key': 'test_val'},
            'omics_uuid': event.omics_uuid}

        self.assertEqual(model_to_dict(event), expected_event)

        expected_status = {
            'id': status.pk,
            'event': event.pk,
            'status_type': 'OK',
            'description': 'OK',
            'extra_data': {}}

        self.assertEqual(model_to_dict(status), expected_status)

    def test_add_event_invalid_app(self):
        """Test adding an event with an invalid app name"""

        # Assert preconditions
        self.assertEqual(ProjectEvent.objects.all().count(), 0)
        self.assertEqual(ProjectEventStatus.objects.all().count(), 0)

        with self.assertRaises(ValueError):
            self.timeline.add_event(
                project=self.project,
                app_name='NON-EXISTING APP NAME',
                user=self.user_owner,
                event_name='test_event',
                description='description',
                extra_data={'test_key': 'test_val'})

        # Assert object status
        self.assertEqual(ProjectEvent.objects.all().count(), 0)
        self.assertEqual(ProjectEventStatus.objects.all().count(), 0)

    def test_add_event_invalid_status(self):
        """Test adding an event with an invalid status type"""

        # Assert preconditions
        self.assertEqual(ProjectEvent.objects.all().count(), 0)
        self.assertEqual(ProjectEventStatus.objects.all().count(), 0)

        with self.assertRaises(ValueError):
            self.timeline.add_event(
                project=self.project,
                app_name='projectroles',
                user=self.user_owner,
                event_name='test_event',
                description='description',
                status_type='NON-EXISTING STATUS TYPE',
                extra_data={'test_key': 'test_val'})

        # Assert object status
        self.assertEqual(ProjectEvent.objects.all().count(), 0)
        self.assertEqual(ProjectEventStatus.objects.all().count(), 0)

    def test_add_object(self):
        """Test adding an object to an event"""

        # Assert precondition
        self.assertEqual(ProjectEventObjectRef.objects.all().count(), 0)

        event = self.timeline.add_event(
            project=self.project,
            app_name='projectroles',
            user=self.user_owner,
            event_name='test_event',
            description='event with {obj}',
            extra_data={'test_key': 'test_val'})

        temp_obj = self.project.get_owner()

        ref = event.add_object(
            obj=temp_obj,
            label='obj',
            name='assignment',
            extra_data={'test_key': 'test_val'})

        # Assert object status after insert
        self.assertEqual(ProjectEventObjectRef.objects.all().count(), 1)

        expected = {
            'id': ref.pk,
            'event': event.pk,
            'label': 'obj',
            'name': 'assignment',
            'object_model': temp_obj.__class__.__name__,
            'object_pk': temp_obj.pk,
            'extra_data': {'test_key': 'test_val'}}

        self.assertEqual(model_to_dict(ref), expected)

    def test_get_object_url(self):
        """Test get_object_url()"""

        event = self.timeline.add_event(
            project=self.project,
            app_name='projectroles',
            user=self.user_owner,
            event_name='test_event',
            description='description',
            extra_data={'test_key': 'test_val'})

        # Add user as an object reference
        self.ref_obj = event.add_object(
            obj=self.user_owner,
            label='user',
            name=self.user_owner.username)

        url = self.timeline.get_object_url(self.project.pk, self.user_owner)
        expected = reverse('object_timeline', kwargs={
            'project': self.project.pk,
            'object_model': self.user_owner.__class__.__name__,
            'object_pk': self.user_owner.pk})
        self.assertEqual(url, expected)

    def test_get_project_events(self):
        """Test get_project_events()"""

        event_normal = self.timeline.add_event(
            project=self.project,
            app_name='projectroles',
            user=self.user_owner,
            event_name='test_event',
            description='description',
            extra_data={'test_key': 'test_val'})

        event_classified = self.timeline.add_event(
            project=self.project,
            app_name='projectroles',
            user=self.user_owner,
            event_name='test_event',
            description='description',
            classified=True,
            extra_data={'test_key': 'test_val'})

        # Test non-classified first
        events = self.timeline.get_project_events(
            self.project, classified=False)

        self.assertEqual(events.count(), 1)
        self.assertEqual(events[0], event_normal)

        # Test with classified
        events = self.timeline.get_project_events(
            self.project, classified=True)

        self.assertEqual(events.count(), 2)
        self.assertIn(event_classified, events)

    def test_get_object_url(self):
        """Test get_object_url()"""

        expected_url = reverse('object_timeline', kwargs={
            'project': self.project.pk,
            'object_model': self.user_owner.__class__.__name__,
            'object_pk': self.user_owner.pk})
        url = self.timeline.get_object_url(
            self.project.pk, self.user_owner)

        self.assertEqual(expected_url, url)

    def test_get_object_link(self):
        """Test get_object_link()"""

        expected_url = reverse('object_timeline', kwargs={
            'project': self.project.pk,
            'object_model': self.user_owner.__class__.__name__,
            'object_pk': self.user_owner.pk})

        link = self.timeline.get_object_link(
            self.project.pk, self.user_owner)

        self.assertIn(expected_url, link)
