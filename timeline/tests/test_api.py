"""Tests for the API in the timeline Django app"""

from django.conf import settings
from django.forms.models import model_to_dict

# Projectroles dependency
from projectroles.plugins import get_backend_api

from .test_models import TestProjectEventBase, ProjectEventMixin,\
    ProjectEventStatusMixin
from ..models import ProjectEvent, ProjectEventStatus, ProjectEventObjectRef,\
    DEFAULT_MESSAGES


# Global constants from settings
CONSTANTS = settings.OMICS_CONSTANTS
PROJECT_ROLE_OWNER = CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_ROLE_DELEGATE = CONSTANTS['PROJECT_ROLE_DELEGATE']
PROJECT_ROLE_CONTRIBUTOR = CONSTANTS['PROJECT_ROLE_CONTRIBUTOR']
PROJECT_ROLE_GUEST = CONSTANTS['PROJECT_ROLE_GUEST']
PROJECT_ROLE_STAFF = CONSTANTS['PROJECT_ROLE_STAFF']
PROJECT_TYPE_CATEGORY = CONSTANTS['PROJECT_TYPE_CATEGORY']
PROJECT_TYPE_PROJECT = CONSTANTS['PROJECT_TYPE_PROJECT']


class TestTimelineAPI(
        TestProjectEventBase, ProjectEventMixin, ProjectEventStatusMixin):

    def setUp(self):
        super(TestTimelineAPI, self).setUp()
        self.timeline = get_backend_api('timeline_backend')

    def test_add_event(self):
        """Test adding an event"""

        # Assert precondition
        self.assertEquals(ProjectEvent.objects.all().count(), 0)
        self.assertEquals(ProjectEventStatus.objects.all().count(), 0)

        event = self.timeline.add_event(
            project=self.project,
            app_name='projectroles',
            user=self.user_owner,
            event_name='test_event',
            description='description',
            extra_data={'test_key': 'test_val'})

        # Assert object status after insert
        self.assertEquals(ProjectEvent.objects.all().count(), 1)
        self.assertEquals(ProjectEventStatus.objects.all().count(), 1)  # Init

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

        self.assertEquals(model_to_dict(event), expected)

        # Test Init status
        status = event.get_current_status()

        expected_status = {
            'id': status.pk,
            'event': event.pk,
            'status_type': 'INIT',
            'description': DEFAULT_MESSAGES['INIT'],
            'extra_data': {}}

        self.assertEquals(model_to_dict(status), expected_status)

    def test_add_event_with_status(self):
        """Test adding an event with status"""

        # Assert precondition
        self.assertEquals(ProjectEvent.objects.all().count(), 0)
        self.assertEquals(ProjectEventStatus.objects.all().count(), 0)

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
        self.assertEquals(ProjectEvent.objects.all().count(), 1)
        self.assertEquals(ProjectEventStatus.objects.all().count(), 2)

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

        self.assertEquals(model_to_dict(event), expected_event)

        expected_status = {
            'id': status.pk,
            'event': event.pk,
            'status_type': 'OK',
            'description': 'OK',
            'extra_data': {}}

        self.assertEquals(model_to_dict(status), expected_status)

    def test_add_object(self):
        """Test adding an object to an event"""

        # Assert precondition
        self.assertEquals(ProjectEventObjectRef.objects.all().count(), 0)

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
        self.assertEquals(ProjectEventObjectRef.objects.all().count(), 1)

        expected = {
            'id': ref.pk,
            'event': event.pk,
            'label': 'obj',
            'name': 'assignment',
            'object_model': temp_obj.__class__.__name__,
            'object_pk': temp_obj.pk,
            'extra_data': {'test_key': 'test_val'}}

        self.assertEquals(model_to_dict(ref), expected)
