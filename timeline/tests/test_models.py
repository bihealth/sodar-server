"""Tests for models in the timeline app"""

from test_plus.test import TestCase

from django.forms.models import model_to_dict

# Projectroles dependency
from projectroles.models import Role, OMICS_CONSTANTS
from projectroles.tests.test_models import ProjectMixin, RoleAssignmentMixin

from ..models import ProjectEvent, ProjectEventObjectRef, ProjectEventStatus


# Global constants from settings
PROJECT_ROLE_OWNER = OMICS_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_ROLE_DELEGATE = OMICS_CONSTANTS['PROJECT_ROLE_DELEGATE']
PROJECT_ROLE_CONTRIBUTOR = OMICS_CONSTANTS['PROJECT_ROLE_CONTRIBUTOR']
PROJECT_ROLE_GUEST = OMICS_CONSTANTS['PROJECT_ROLE_GUEST']
PROJECT_ROLE_STAFF = OMICS_CONSTANTS['PROJECT_ROLE_STAFF']
PROJECT_TYPE_CATEGORY = OMICS_CONSTANTS['PROJECT_TYPE_CATEGORY']
PROJECT_TYPE_PROJECT = OMICS_CONSTANTS['PROJECT_TYPE_PROJECT']


class ProjectEventMixin:
    """Helper mixin for ProjectEvent creation"""
    @classmethod
    def _make_event(
            cls, project, app, user, event_name, description, classified,
            extra_data):
        values = {
            'project': project,
            'app': app,
            'user': user,
            'event_name': event_name,
            'description': description,
            'classified': classified,
            'extra_data': extra_data}
        result = ProjectEvent(**values)
        result.save()
        return result


class ProjectEventObjectRefMixin:
    """Helper mixin for ProjectEventObjectRef creation"""
    @classmethod
    def _make_object_ref(cls, event, obj, label, name, extra_data):
        values = {
            'event': event,
            'label': label,
            'name': name,
            'object_model': obj.__class__.__name__,
            'object_pk': obj.pk,
            'extra_data': extra_data}
        result = ProjectEventObjectRef(**values)
        result.save()
        return result


class ProjectEventStatusMixin:
    """Helper mixin for ProjectEventStatus creation"""
    @classmethod
    def _make_event_status(cls, event, status_type, description, extra_data):
        values = {
            'event': event,
            'status_type': status_type,
            'description': description,
            'extra_data': extra_data}
        result = ProjectEventStatus(**values)
        result.save()
        return result


class TestProjectEventBase(TestCase, ProjectMixin, RoleAssignmentMixin):
    def setUp(self):
        # Make owner user
        self.user_owner = self.make_user('owner')

        # Init project, role and assignment
        self.project = self._make_project(
            'TestProject', PROJECT_TYPE_PROJECT, None)
        self.role_owner = Role.objects.get_or_create(
            name=PROJECT_ROLE_OWNER)[0]
        self.role_delegate = Role.objects.get_or_create(
            name=PROJECT_ROLE_DELEGATE)[0]
        self.assignment_owner = self._make_assignment(
            self.project, self.user_owner, self.role_owner)


class TestProjectEvent(
        TestProjectEventBase, ProjectEventMixin, ProjectEventStatusMixin):

    def setUp(self):
        super(TestProjectEvent, self).setUp()

        self.event = self._make_event(
            project=self.project,
            app='projectroles',
            user=self.user_owner,
            event_name='test_event',
            description='description',
            classified=False,
            extra_data={'test_key': 'test_val'})

    def test_initialization(self):
        expected = {
            'id': self.event.pk,
            'project': self.project.pk,
            'app': 'projectroles',
            'user': self.user_owner.pk,
            'event_name': 'test_event',
            'description': 'description',
            'classified': False,
            'extra_data': {'test_key': 'test_val'},
            'omics_uuid': self.event.omics_uuid}

        self.assertEqual(model_to_dict(self.event), expected)

    def test__str__(self):
        expected = 'TestProject: test_event/owner'
        self.assertEqual(str(self.event), expected)

    def test__repr__(self):
        expected = "ProjectEvent('TestProject', 'test_event', " \
            "'owner')"
        self.assertEqual(repr(self.event), expected)


class TestProjectEventObjectRef(
        TestProjectEventBase, ProjectEventMixin, ProjectEventObjectRefMixin):

    def setUp(self):
        super(TestProjectEventObjectRef, self).setUp()

        self.event = self._make_event(
            project=self.project,
            app='projectroles',
            user=self.user_owner,
            event_name='test_event',
            description='description',
            classified=False,
            extra_data={'test_key': 'test_val'})

        self.obj_ref = self._make_object_ref(
            event=self.event,
            obj=self.assignment_owner,
            label='test_label',
            name='test_name',
            extra_data={'test_key': 'test_val'})

    def test_initialization(self):
        expected = {
            'id': self.obj_ref.pk,
            'event': self.event.pk,
            'label': 'test_label',
            'name': 'test_name',
            'object_model': 'RoleAssignment',
            'object_pk': self.assignment_owner.pk,
            'extra_data': {'test_key': 'test_val'}}

        self.assertEqual(model_to_dict(self.obj_ref), expected)

    def test__str__(self):
        expected = 'TestProject: test_event/owner (test_name)'
        self.assertEqual(str(self.obj_ref), expected)

    def test__repr__(self):
        expected = "ProjectEventObjectRef('TestProject', 'test_event', " \
            "'owner', 'test_name')"
        self.assertEqual(repr(self.obj_ref), expected)

    def test_add_object(self):
        """Test the add_object() function of ProjectEvent"""

        # Init new user and role
        new_user = self.make_user('new_user')
        new_as = self._make_assignment(
            self.project, new_user, self.role_delegate)

        new_obj = self.event.add_object(
            obj=new_as,
            label='new_label',
            name='new_name')

        expected = {
            'id': new_obj.pk,
            'event': self.event.pk,
            'label': 'new_label',
            'name': 'new_name',
            'object_pk': new_as.pk,
            'object_model': 'RoleAssignment',
            'extra_data': {}}

        self.assertEqual(model_to_dict(new_obj), expected)

    def test_get_object_events(self):
        """Test get_object_events() in ProjectEventManager"""
        events = ProjectEvent.objects.get_object_events(
            project_pk=self.project.pk,
            object_model=self.obj_ref.object_model,
            object_pk=self.obj_ref.object_pk)

        self.assertEqual(events.count(), 1)
        self.assertEqual(events[0], self.event)


class TestProjectEventStatus(
        TestProjectEventBase, ProjectEventMixin, ProjectEventStatusMixin):

    def setUp(self):
        super(TestProjectEventStatus, self).setUp()

        self.event = self._make_event(
            project=self.project,
            app='projectroles',
            user=self.user_owner,
            event_name='test_event',
            description='description',
            classified=False,
            extra_data={'test_key': 'test_val'})

        self.event_status_submit = self._make_event_status(
            event=self.event,
            status_type='SUBMIT',
            description='SUBMIT',
            extra_data={'test_key': 'test_val'})

        self.event_status_ok = self._make_event_status(
            event=self.event,
            status_type='OK',
            description='OK',
            extra_data={'test_key': 'test_val'})

    def test_initialization(self):
        expected = {
            'id': self.event_status_ok.pk,
            'event': self.event.pk,
            'status_type': 'OK',
            'description': 'OK',
            'extra_data': {'test_key': 'test_val'}}

        self.assertEqual(model_to_dict(self.event_status_ok), expected)

    def test__str__(self):
        expected = 'TestProject: test_event/owner (OK)'
        self.assertEqual(str(self.event_status_ok), expected)

    def test__repr__(self):
        expected = "ProjectEventStatus('TestProject', 'test_event', " \
            "'owner', 'OK')"
        self.assertEqual(repr(self.event_status_ok), expected)

    def test_get_current_status(self):
        """Test the get_current_status() function of ProjectEvent"""
        status = self.event.get_current_status()

        expected = {
            'id': self.event_status_ok.pk,
            'event': self.event.pk,
            'status_type': 'OK',
            'description': 'OK',
            'extra_data': {'test_key': 'test_val'}}

        self.assertEqual(model_to_dict(status), expected)

    def test_get_timestamp(self):
        """Test the get_timestamp() function of ProjectEvent"""
        timestamp = self.event.get_timestamp()
        self.assertEqual(timestamp, self.event_status_ok.timestamp)

    def test_get_status_changes(self):
        """Test the get_status_changes() function of ProjectEvent"""
        status_changes = self.event.get_status_changes()
        self.assertEqual(status_changes.count(), 2)
        self.assertEqual(status_changes[0], self.event_status_submit)

    def test_get_status_changes_reverse(self):
        """Test the get_status_changes() function of ProjectEvent with
        reverse=True"""
        status_changes = self.event.get_status_changes(reverse=True)
        self.assertEqual(status_changes.count(), 2)
        self.assertEqual(status_changes[0], self.event_status_ok)

    def test_set_status(self):
        """Test the set_status() function of ProjectEvent"""
        new_status = self.event.set_status(
            'FAILED',
            status_desc='FAILED',
            extra_data={'test_key': 'test_val'})

        expected = {
            'id': new_status.pk,
            'event': self.event.pk,
            'status_type': 'FAILED',
            'description': 'FAILED',
            'extra_data': {'test_key': 'test_val'}}

        self.assertEqual(model_to_dict(new_status), expected)
