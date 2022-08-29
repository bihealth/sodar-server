"""Plugin tests for the taskflowbackend app"""

from unittest import skipIf

from irods.user import iRODSUser, iRODSUserGroup
from irods.exception import UserGroupDoesNotExist

from django.test import RequestFactory

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
from projectroles.models import SODAR_CONSTANTS
from projectroles.plugins import BackendPluginPoint

# Irodsbackend dependency
from irodsbackend.api import USER_GROUP_PREFIX

from taskflowbackend.tests.test_project_views import (
    TestTaskflowBase,
    BACKENDS_ENABLED,
    BACKEND_SKIP_MSG,
    IRODS_ACCESS_READ,
)

# Timeline dependency
from timeline.models import ProjectEvent


app_settings = AppSettingAPI()


# SODAR constants
PROJECT_TYPE_CATEGORY = SODAR_CONSTANTS['PROJECT_TYPE_CATEGORY']
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']
PROJECT_ACTION_CREATE = SODAR_CONSTANTS['PROJECT_ACTION_CREATE']
PROJECT_ACTION_UPDATE = SODAR_CONSTANTS['PROJECT_ACTION_UPDATE']


class TestModifyAPIBase(TestTaskflowBase):
    """Base class for project modify API tests"""

    def setUp(self):
        super().setUp()
        self.plugin = BackendPluginPoint.get_plugin('taskflow')
        # Create dummy request
        self.req_factory = RequestFactory()
        self.request = self.req_factory.get('/')
        self.request.user = self.user


@skipIf(not BACKENDS_ENABLED, BACKEND_SKIP_MSG)
class TestPerformProjectModify(TestModifyAPIBase):
    """Tests for perform_project_modify()"""

    def test_create(self):
        """Test project creation in iRODS"""
        # Create project (note: without taskflow)
        project = self._make_project(
            'NewProject', PROJECT_TYPE_PROJECT, self.category
        )
        self._make_assignment(project, self.user, self.role_owner)
        group_name = self.irods_backend.get_user_group_name(project)

        self.assert_irods_coll(project, expected=False)
        with self.assertRaises(UserGroupDoesNotExist):
            self.irods_session.user_groups.get(group_name)

        self.plugin.perform_project_modify(
            project=project,
            action=PROJECT_ACTION_CREATE,
            project_settings=app_settings.get_all_settings(project),
            request=self.request,
        )

        self.assert_irods_coll(project, expected=True)
        group = self.irods_session.user_groups.get(group_name)
        self.assertIsInstance(group, iRODSUserGroup)
        self.assert_irods_access(
            group_name, self.irods_backend.get_path(project), IRODS_ACCESS_READ
        )
        self.assertIsInstance(
            self.irods_session.users.get(self.user.username), iRODSUser
        )
        self.assert_group_member(project, self.user, True)
        project_coll = self.irods_session.collections.get(
            self.irods_backend.get_path(project)
        )
        self.assertEqual(
            project_coll.metadata.get_one('parent_uuid').value,
            str(self.category.sodar_uuid),
        )
        # Assert inherited category owner status
        self.assertIsInstance(
            self.irods_session.users.get(self.user_cat.username), iRODSUser
        )
        self.assert_group_member(project, self.user_cat, True)
        tl_events = ProjectEvent.objects.filter(
            project=project,
            plugin='taskflow',
            user=self.user,
            event_name='project_create',
        )
        self.assertEqual(tl_events.count(), 1)
        self.assertEqual(tl_events.first().get_status().status_type, 'OK')

    def test_create_category(self):
        """Test category creation in iRODS (should not be created)"""
        category = self._make_project(
            'SubCategory', PROJECT_TYPE_CATEGORY, self.category
        )
        self._make_assignment(category, self.user, self.role_owner)
        group_name = '{}{}'.format(USER_GROUP_PREFIX, category.sodar_uuid)

        self.assert_irods_coll(category, expected=False)
        with self.assertRaises(UserGroupDoesNotExist):
            self.irods_session.user_groups.get(group_name)

        self.plugin.perform_project_modify(
            project=category,
            action=PROJECT_ACTION_CREATE,
            project_settings=app_settings.get_all_settings(category),
            request=self.request,
        )

        self.assert_irods_coll(category, expected=False)
        with self.assertRaises(UserGroupDoesNotExist):
            self.irods_session.user_groups.get(group_name)
        self.assertEqual(
            ProjectEvent.objects.filter(
                project=category,
                plugin='taskflow',
                user=self.user,
                event_name='project_create',
            ).count(),
            0,
        )

    def test_update_parent(self):
        """Test project updating in iRODS with different parent category"""
        project, _ = self.make_project_taskflow(
            'NewProject', PROJECT_TYPE_PROJECT, self.category, self.user
        )
        user_contrib = self.make_user('contrib_user')
        user_cat_new = self.make_user('user_cat_new')
        self.make_assignment_taskflow(
            project, user_contrib, self.role_contributor
        )
        project_path = self.irods_backend.get_path(project)

        self.assert_group_member(project, self.user, True)
        self.assert_group_member(project, self.user_cat, True)
        self.assert_group_member(project, user_contrib, True)
        self.assert_group_member(project, user_cat_new, False)
        project_coll = self.irods_session.collections.get(project_path)
        self.assertEqual(
            project_coll.metadata.get_one('parent_uuid').value,
            str(self.category.sodar_uuid),
        )

        new_category = self._make_project(
            'NewCategory', PROJECT_TYPE_CATEGORY, None
        )
        self._make_assignment(new_category, user_cat_new, self.role_owner)
        project.parent = new_category
        project.save()
        self.plugin.perform_project_modify(
            project=project,
            action=PROJECT_ACTION_UPDATE,
            project_settings=app_settings.get_all_settings(project),
            old_data={'parent': self.category},
            request=self.request,
        )

        self.assert_group_member(project, self.user, True)
        self.assert_group_member(project, self.user_cat, False)
        self.assert_group_member(project, user_contrib, True)
        self.assert_group_member(project, user_cat_new, True)
        project_coll = self.irods_session.collections.get(project_path)
        self.assertEqual(
            project_coll.metadata.get_one('parent_uuid').value,
            str(new_category.sodar_uuid),
        )


@skipIf(not BACKENDS_ENABLED, BACKEND_SKIP_MSG)
class TestRevertProjectModify(TestModifyAPIBase):
    """Tests for revert_project_modify()"""

    def setUp(self):
        super().setUp()
        # Make project with owner in Taskflow and Django
        self.project, self.owner_as = self.make_project_taskflow(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category,
            owner=self.user,
            description='description',
        )
        self.group_name = self.irods_backend.get_user_group_name(self.project)

    def test_revert_create(self):
        """Test reverting project creation in iRODS"""
        self.assert_irods_coll(self.project, expected=True)
        self.assert_group_member(self.project, self.user, True)

        self.plugin.revert_project_modify(
            project=self.project,
            action=PROJECT_ACTION_CREATE,
            project_settings=app_settings.get_all_settings(self.project),
            request=self.request,
        )

        self.assert_irods_coll(self.project, expected=False)
        with self.assertRaises(UserGroupDoesNotExist):
            self.irods_session.user_groups.get(self.group_name)
        tl_events = ProjectEvent.objects.filter(
            project=self.project,
            plugin='taskflow',
            user=self.user,
            event_name='project_create_revert',
        )
        self.assertEqual(tl_events.count(), 1)
        self.assertEqual(tl_events.first().get_status().status_type, 'OK')


@skipIf(not BACKENDS_ENABLED, BACKEND_SKIP_MSG)
class TestPerformRoleModify(TestModifyAPIBase):
    """Tests for perform_role_modify() and revert_role_modify()"""

    def setUp(self):
        super().setUp()
        self.project, self.owner_as = self.make_project_taskflow(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category,
            owner=self.user,
            description='description',
        )
        self.group_name = self.irods_backend.get_user_group_name(self.project)

    def test_create(self):
        """Test creating a role assignment in iRODS"""
        user_new = self.make_user('user_new')
        role_as = self._make_assignment(
            self.project, user_new, self.role_contributor
        )
        self.assert_group_member(self.project, user_new, False)

        self.plugin.perform_role_modify(
            role_as=role_as,
            action=PROJECT_ACTION_CREATE,
            request=self.request,
        )

        self.assert_group_member(self.project, user_new, True)
        tl_events = ProjectEvent.objects.filter(
            project=self.project,
            plugin='taskflow',
            user=self.user,
            event_name='role_update',
        )
        self.assertEqual(tl_events.count(), 1)
        self.assertEqual(tl_events.first().get_status().status_type, 'OK')

    def test_update(self):
        """Test updating a role assignment in iRODS (should do nothing)"""
        user_new = self.make_user('user_new')
        role_as = self.make_assignment_taskflow(
            self.project, user_new, self.role_contributor
        )
        self.assert_group_member(self.project, user_new, True)

        self.plugin.perform_role_modify(
            role_as=role_as,
            action=PROJECT_ACTION_UPDATE,
            old_role=self.role_guest,
            request=self.request,
        )

        self.assert_group_member(self.project, user_new, True)
        self.assertEqual(
            ProjectEvent.objects.filter(
                project=self.project,
                plugin='taskflow',
                user=self.user,
                event_name='role_update',
            ).count(),
            1,
        )

    def test_revert_create(self):
        """Test reverting role creation in iRODS"""
        user_new = self.make_user('user_new')
        role_as = self.make_assignment_taskflow(
            self.project, user_new, self.role_contributor
        )
        self.assert_group_member(self.project, user_new, True)

        self.plugin.revert_role_modify(
            role_as=role_as,
            action=PROJECT_ACTION_CREATE,
            request=self.request,
        )

        self.assert_group_member(self.project, user_new, False)
        tl_events = ProjectEvent.objects.filter(
            project=self.project,
            plugin='taskflow',
            user=self.user,
            event_name='role_update_revert',
        )
        self.assertEqual(tl_events.count(), 1)
        self.assertEqual(tl_events.first().get_status().status_type, 'OK')

    def test_revert_update(self):
        """Test reverting role update in iRODS (should do nothing)"""
        user_new = self.make_user('user_new')
        role_as = self.make_assignment_taskflow(
            self.project, user_new, self.role_contributor
        )
        self.assert_group_member(self.project, user_new, True)

        self.plugin.revert_role_modify(
            role_as=role_as,
            action=PROJECT_ACTION_UPDATE,
            old_role=self.role_guest,
            request=self.request,
        )

        self.assert_group_member(self.project, user_new, True)
        self.assertEqual(
            ProjectEvent.objects.filter(
                project=self.project,
                plugin='taskflow',
                user=self.user,
                event_name='role_update_revert',
            ).count(),
            0,
        )


@skipIf(not BACKENDS_ENABLED, BACKEND_SKIP_MSG)
class TestPerformRoleDelete(TestModifyAPIBase):
    """Tests for perform_role_delete() and revert_role_delete()"""

    def setUp(self):
        super().setUp()
        self.project, self.owner_as = self.make_project_taskflow(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category,
            owner=self.user,
            description='description',
        )
        self.user_new = self.make_user('user_new')
        self.role_as = self.make_assignment_taskflow(
            self.project, self.user_new, self.role_contributor
        )
        self.group_name = self.irods_backend.get_user_group_name(self.project)

    def test_delete(self):
        """Test deleting a role assignment in iRODS"""
        self.assert_group_member(self.project, self.user_new, True)

        self.plugin.perform_role_delete(
            role_as=self.role_as, request=self.request
        )

        self.assert_group_member(self.project, self.user_new, False)
        tl_events = ProjectEvent.objects.filter(
            project=self.project,
            plugin='taskflow',
            user=self.user,
            event_name='role_delete',
        )
        self.assertEqual(tl_events.count(), 1)
        self.assertEqual(tl_events.first().get_status().status_type, 'OK')

    def test_revert(self):
        """Test reverting role assignment deletion in iRODS"""
        self.assert_group_member(self.project, self.user_new, True)
        self.plugin.perform_role_delete(
            role_as=self.role_as, request=self.request
        )
        self.assert_group_member(self.project, self.user_new, False)

        self.plugin.revert_role_delete(
            role_as=self.role_as, request=self.request
        )

        self.assert_group_member(self.project, self.user_new, True)
        tl_events = ProjectEvent.objects.filter(
            project=self.project,
            plugin='taskflow',
            user=self.user,
            event_name='role_delete_revert',
        )
        self.assertEqual(tl_events.count(), 1)
        self.assertEqual(tl_events.first().get_status().status_type, 'OK')


@skipIf(not BACKENDS_ENABLED, BACKEND_SKIP_MSG)
class TestPerformOwnerTransfer(TestModifyAPIBase):
    """Tests for perform_owner_transfer()"""

    def setUp(self):
        super().setUp()
        self.project, self.owner_as = self.make_project_taskflow(
            title='TestProject',
            type=PROJECT_TYPE_PROJECT,
            parent=self.category,
            owner=self.user,
            description='description',
        )
        self.user_new = self.make_user('user_new')
        self.role_as = self.make_assignment_taskflow(
            self.project, self.user_new, self.role_contributor
        )

    def test_transfer_category(self):
        """Test category owner transfer in iRODS"""
        self.assert_group_member(self.project, self.user, True)
        self.assert_group_member(self.project, self.user_new, True)
        self.assert_group_member(self.project, self.user_cat, True)

        self.plugin.perform_owner_transfer(
            project=self.category,
            new_owner=self.user,
            old_owner=self.user_cat,
            old_owner_role=self.role_contributor,
            request=self.request,
        )

        self.assert_group_member(self.project, self.user, True)
        self.assert_group_member(self.project, self.user_new, True)
        # Former category owner should no longer have roles in inherited project
        self.assert_group_member(self.project, self.user_cat, False)
        tl_events = ProjectEvent.objects.filter(
            project=self.category,
            plugin='taskflow',
            user=self.user,
            event_name='role_owner_transfer',
        )
        self.assertEqual(tl_events.count(), 1)
        self.assertEqual(tl_events.first().get_status().status_type, 'OK')

    def test_transfer_category_child(self):
        """Test owner transfer in iRODS with child category and project"""
        sub_category = self._make_project(
            'sub_category', PROJECT_TYPE_CATEGORY, self.category
        )
        self._make_assignment(sub_category, self.user_cat, self.role_owner)
        sub_project, _ = self.make_project_taskflow(
            'sub_project', PROJECT_TYPE_PROJECT, sub_category, self.user_cat
        )
        # No roles for self.user
        self.assert_group_member(sub_project, self.user, False)
        self.assert_group_member(sub_project, self.user_new, False)
        self.assert_group_member(sub_project, self.user_cat, True)

        self.plugin.perform_owner_transfer(
            project=sub_category,
            new_owner=self.user,
            old_owner=self.user_cat,
            old_owner_role=self.role_contributor,
            request=self.request,
        )

        self.assert_group_member(sub_project, self.user, True)
        self.assert_group_member(sub_project, self.user_new, False)
        self.assert_group_member(sub_project, self.user_cat, True)

    def test_transfer_project(self):
        """Test project owner transfer in iRODS (should not do anything)"""
        self.assert_group_member(self.project, self.user, True)
        self.assert_group_member(self.project, self.user_new, True)
        self.assert_group_member(self.project, self.user_cat, True)

        self.plugin.perform_owner_transfer(
            project=self.project,
            new_owner=self.user,
            old_owner=self.user_cat,
            old_owner_role=self.role_contributor,
            request=self.request,
        )

        self.assert_group_member(self.project, self.user, True)
        self.assert_group_member(self.project, self.user_new, True)
        self.assert_group_member(self.project, self.user_cat, True)
        self.assertEqual(
            ProjectEvent.objects.filter(
                project=self.category,
                plugin='taskflow',
                user=self.user,
                event_name='role_owner_transfer',
            ).count(),
            0,
        )


@skipIf(not BACKENDS_ENABLED, BACKEND_SKIP_MSG)
class TestPerformProjectSync(TestModifyAPIBase):
    """Tests for perform_project_sync()"""

    def test_sync(self):
        """Test project sync in iRODS"""
        # NOTE: Should be identical to test_create() in TestPerformProjectModify
        project = self._make_project(
            'NewProject', PROJECT_TYPE_PROJECT, self.category
        )
        self._make_assignment(project, self.user, self.role_owner)
        group_name = self.irods_backend.get_user_group_name(project)

        self.assert_irods_coll(project, expected=False)
        with self.assertRaises(UserGroupDoesNotExist):
            self.irods_session.user_groups.get(group_name)

        self.plugin.perform_project_modify(
            project=project,
            action=PROJECT_ACTION_CREATE,
            project_settings=app_settings.get_all_settings(project),
            request=self.request,
        )

        self.assert_irods_coll(project, expected=True)
        group = self.irods_session.user_groups.get(group_name)
        self.assertIsInstance(group, iRODSUserGroup)
        self.assert_irods_access(
            group_name, self.irods_backend.get_path(project), IRODS_ACCESS_READ
        )
        self.assertIsInstance(
            self.irods_session.users.get(self.user.username), iRODSUser
        )
        self.assert_group_member(project, self.user, True)
        project_coll = self.irods_session.collections.get(
            self.irods_backend.get_path(project)
        )
        self.assertEqual(
            project_coll.metadata.get_one('parent_uuid').value,
            str(self.category.sodar_uuid),
        )
        # Assert inherited category owner status
        self.assertIsInstance(
            self.irods_session.users.get(self.user_cat.username), iRODSUser
        )
        self.assert_group_member(project, self.user_cat, True)
        tl_events = ProjectEvent.objects.filter(
            project=project,
            plugin='taskflow',
            user=self.user,
            event_name='project_create',
        )
        self.assertEqual(tl_events.count(), 1)
        self.assertEqual(tl_events.first().get_status().status_type, 'OK')

    def test_sync_existing(self):
        """Test sync for existing iRODS project (should not affect anything)"""
        project, _ = self.make_project_taskflow(
            'NewProject', PROJECT_TYPE_PROJECT, self.category, self.user
        )
        group_name = self.irods_backend.get_user_group_name(project)

        self.assert_irods_coll(project, expected=True)
        group = self.irods_session.user_groups.get(group_name)
        self.assertIsInstance(group, iRODSUserGroup)
        self.assert_irods_access(
            group_name, self.irods_backend.get_path(project), IRODS_ACCESS_READ
        )
        self.assertIsInstance(
            self.irods_session.users.get(self.user.username), iRODSUser
        )
        self.assert_group_member(project, self.user, True)

        self.plugin.perform_project_modify(
            project=project,
            action=PROJECT_ACTION_CREATE,
            project_settings=app_settings.get_all_settings(project),
            request=self.request,
        )

        self.assert_irods_coll(project, expected=True)
        self.assert_irods_access(
            group_name, self.irods_backend.get_path(project), IRODS_ACCESS_READ
        )
        self.assert_group_member(project, self.user, True)
        self.assertIsInstance(
            self.irods_session.users.get(self.user_cat.username), iRODSUser
        )
        self.assert_group_member(project, self.user_cat, True)
        tl_events = ProjectEvent.objects.filter(
            project=project,
            plugin='taskflow',
            user=self.user,
            event_name='project_create',
        )
        self.assertEqual(tl_events.count(), 1)
        self.assertEqual(tl_events.first().get_status().status_type, 'OK')
