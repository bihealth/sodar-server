"""Tests for models in the timeline Django app"""

from test_plus.test import TestCase

from django.conf import settings
from django.forms.models import model_to_dict

# Projectroles dependency
from projectroles.models import Role
from projectroles.tests.test_models import ProjectMixin, RoleAssignmentMixin

from ..models import ProjectEvent, ProjectEventObjectRef, ProjectEventStatus


# Global constants from settings
CONSTANTS = settings.OMICS_CONSTANTS
PROJECT_ROLE_OWNER = CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_ROLE_DELEGATE = CONSTANTS['PROJECT_ROLE_DELEGATE']
PROJECT_ROLE_CONTRIBUTOR = CONSTANTS['PROJECT_ROLE_CONTRIBUTOR']
PROJECT_ROLE_GUEST = CONSTANTS['PROJECT_ROLE_GUEST']
PROJECT_ROLE_STAFF = CONSTANTS['PROJECT_ROLE_STAFF']
PROJECT_TYPE_CATEGORY = CONSTANTS['PROJECT_TYPE_CATEGORY']
PROJECT_TYPE_PROJECT = CONSTANTS['PROJECT_TYPE_PROJECT']


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

        self.assertEquals(model_to_dict(self.event), expected)

    # TODO: Test __str__() & __repr__()


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

        self.assertEquals(model_to_dict(self.obj_ref), expected)

    # TODO: Test __str__() & __repr__()


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

        self.event_status = self._make_event_status(
            event=self.event,
            status_type='OK',
            description='OK',
            extra_data={'test_key': 'test_val'})

    def test_initialization(self):
        expected = {
            'id': self.event_status.pk,
            'event': self.event.pk,
            'status_type': 'OK',
            'description': 'OK',
            'extra_data': {'test_key': 'test_val'}}

        self.assertEquals(model_to_dict(self.event_status), expected)

    # TODO: Test __str__() & __repr__()
