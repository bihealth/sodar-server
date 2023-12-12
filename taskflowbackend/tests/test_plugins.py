"""Plugin tests for the taskflowbackend app"""

from irods.user import iRODSUser, iRODSUserGroup
from irods.exception import UserDoesNotExist, UserGroupDoesNotExist

from django.test import RequestFactory

# Projectroles dependency
from projectroles.app_settings import AppSettingAPI
from projectroles.models import RoleAssignment, SODAR_CONSTANTS
from projectroles.plugins import BackendPluginPoint

# Irodsbackend dependency
from irodsbackend.api import USER_GROUP_TEMPLATE

# Timeline dependency
from timeline.models import ProjectEvent

from taskflowbackend.tests.base import TaskflowViewTestBase


app_settings = AppSettingAPI()


# SODAR constants
PROJECT_TYPE_CATEGORY = SODAR_CONSTANTS['PROJECT_TYPE_CATEGORY']
PROJECT_TYPE_PROJECT = SODAR_CONSTANTS['PROJECT_TYPE_PROJECT']
PROJECT_ACTION_CREATE = SODAR_CONSTANTS['PROJECT_ACTION_CREATE']
PROJECT_ACTION_UPDATE = SODAR_CONSTANTS['PROJECT_ACTION_UPDATE']


class ModifyAPITaskflowTestBase(TaskflowViewTestBase):
    """Base class for project modify API tests"""

    def _make_project_tf(self):
        project, _ = self.make_project_taskflow(
            'NewProject', PROJECT_TYPE_PROJECT, self.category, self.user
        )
        return project

    def setUp(self):
        super().setUp()
        self.plugin = BackendPluginPoint.get_plugin('taskflow')
        # Create dummy request
        self.req_factory = RequestFactory()
        self.request = self.req_factory.get('/')
        self.request.user = self.user


class TestPerformProjectModify(ModifyAPITaskflowTestBase):
    """Tests for perform_project_modify()"""

    def test_create(self):
        """Test project creation in iRODS"""
        # Create project (NOTE: without taskflow)
        project = self.make_project(
            'NewProject', PROJECT_TYPE_PROJECT, self.category
        )
        self.make_assignment(project, self.user, self.role_owner)
        group_name = self.irods_backend.get_user_group_name(project)
        self.assert_irods_coll(project, expected=False)
        with self.assertRaises(UserGroupDoesNotExist):
            self.irods.user_groups.get(group_name)
        with self.assertRaises(UserDoesNotExist):
            self.irods.users.get(self.user.username)
        with self.assertRaises(UserDoesNotExist):
            self.irods.users.get(self.user_owner_cat.username)

        self.plugin.perform_project_modify(
            project=project,
            action=PROJECT_ACTION_CREATE,
            project_settings=app_settings.get_all(project),
            request=self.request,
        )

        self.assert_irods_coll(project, expected=True)
        group = self.irods.user_groups.get(group_name)
        self.assertIsInstance(group, iRODSUserGroup)
        self.assert_irods_access(
            group_name,
            self.irods_backend.get_path(project),
            self.irods_access_read,
        )
        self.assertIsInstance(
            self.irods.users.get(self.user.username), iRODSUser
        )
        self.assert_group_member(project, self.user, True)
        project_coll = self.irods.collections.get(
            self.irods_backend.get_path(project)
        )
        self.assertEqual(
            project_coll.metadata.get_one('parent_uuid').value,
            str(self.category.sodar_uuid),
        )
        # Assert inherited category owner status
        self.assertIsInstance(
            self.irods.users.get(self.user_owner_cat.username), iRODSUser
        )
        self.assert_group_member(project, self.user_owner_cat, True)
        tl_events = ProjectEvent.objects.filter(
            project=project,
            plugin='taskflow',
            user=self.user,
            event_name='project_create',
        )
        self.assertEqual(tl_events.count(), 1)
        self.assertEqual(tl_events.first().get_status().status_type, 'OK')

    def test_create_inherited_members(self):
        """Test project creation in iRODS with inherited members"""
        # Add category members
        user_contrib_cat = self.make_user('user_contrib_cat')
        self.make_assignment(
            self.category, user_contrib_cat, self.role_contributor
        )
        user_finder_cat = self.make_user('user_finder_cat')
        self.make_assignment(self.category, user_finder_cat, self.role_finder)

        project = self.make_project(
            'NewProject', PROJECT_TYPE_PROJECT, self.category
        )
        self.make_assignment(project, self.user, self.role_owner)
        group_name = self.irods_backend.get_user_group_name(project)
        self.assert_irods_coll(project, expected=False)
        with self.assertRaises(UserGroupDoesNotExist):
            self.irods.user_groups.get(group_name)
        with self.assertRaises(UserDoesNotExist):
            self.irods.users.get(self.user.username)
        with self.assertRaises(UserDoesNotExist):
            self.irods.users.get(user_contrib_cat.username)
        with self.assertRaises(UserDoesNotExist):
            self.irods.users.get(user_finder_cat.username)

        self.plugin.perform_project_modify(
            project=project,
            action=PROJECT_ACTION_CREATE,
            project_settings=app_settings.get_all(project),
            request=self.request,
        )

        self.assert_group_member(project, self.user, True)
        self.assert_group_member(project, self.user_owner_cat, True)
        self.assert_group_member(project, user_contrib_cat, True)
        # Finder role should not be added
        with self.assertRaises(UserDoesNotExist):
            self.irods.users.get(user_finder_cat.username)
        self.assert_group_member(project, user_finder_cat, False)

    def test_create_inherited_subcategory(self):
        """Test creation with inherited members and nested categories"""
        user_contrib_cat = self.make_user('user_contrib_cat')
        self.make_assignment(
            self.category, user_contrib_cat, self.role_contributor
        )
        user_finder_cat = self.make_user('user_finder_cat')
        self.make_assignment(self.category, user_finder_cat, self.role_finder)
        # Create subcategory
        sub_cat = self.make_project(
            'SubCategory', PROJECT_TYPE_CATEGORY, self.category
        )
        self.make_assignment(sub_cat, self.user_owner_cat, self.role_owner)

        project = self.make_project('NewProject', PROJECT_TYPE_PROJECT, sub_cat)
        self.make_assignment(project, self.user, self.role_owner)
        group_name = self.irods_backend.get_user_group_name(project)
        self.assert_irods_coll(project, expected=False)
        with self.assertRaises(UserGroupDoesNotExist):
            self.irods.user_groups.get(group_name)
        with self.assertRaises(UserDoesNotExist):
            self.irods.users.get(self.user.username)
        with self.assertRaises(UserDoesNotExist):
            self.irods.users.get(user_contrib_cat.username)
        with self.assertRaises(UserDoesNotExist):
            self.irods.users.get(user_finder_cat.username)

        self.plugin.perform_project_modify(
            project=project,
            action=PROJECT_ACTION_CREATE,
            project_settings=app_settings.get_all(project),
            request=self.request,
        )

        self.assert_group_member(project, self.user, True)
        self.assert_group_member(project, self.user_owner_cat, True)
        self.assert_group_member(project, user_contrib_cat, True)
        with self.assertRaises(UserDoesNotExist):
            self.irods.users.get(user_finder_cat.username)
        self.assert_group_member(project, user_finder_cat, False)

    def test_create_inherited_override_child(self):
        """Test creation with role overridden in child category"""
        user_finder_cat = self.make_user('user_finder_cat')
        self.make_assignment(self.category, user_finder_cat, self.role_finder)
        # Create subcategory with overridden role
        sub_cat = self.make_project(
            'SubCategory', PROJECT_TYPE_CATEGORY, self.category
        )
        self.make_assignment(sub_cat, self.user_owner_cat, self.role_owner)
        self.make_assignment(sub_cat, user_finder_cat, self.role_guest)

        project = self.make_project('NewProject', PROJECT_TYPE_PROJECT, sub_cat)
        self.make_assignment(project, self.user, self.role_owner)

        self.plugin.perform_project_modify(
            project=project,
            action=PROJECT_ACTION_CREATE,
            project_settings=app_settings.get_all(project),
            request=self.request,
        )
        # Since there is an overridden role, this should be created
        self.assert_group_member(project, user_finder_cat, True)

    def test_create_inherited_override_parent(self):
        """Test creation with role overridden in parent category"""
        user_guest_cat = self.make_user('user_guest_cat')
        self.make_assignment(self.category, user_guest_cat, self.role_guest)
        # Create subcategory with finder role role
        sub_cat = self.make_project(
            'SubCategory', PROJECT_TYPE_CATEGORY, self.category
        )
        self.make_assignment(sub_cat, self.user_owner_cat, self.role_owner)
        self.make_assignment(sub_cat, user_guest_cat, self.role_finder)

        project = self.make_project('NewProject', PROJECT_TYPE_PROJECT, sub_cat)
        self.make_assignment(project, self.user, self.role_owner)

        self.plugin.perform_project_modify(
            project=project,
            action=PROJECT_ACTION_CREATE,
            project_settings=app_settings.get_all(project),
            request=self.request,
        )
        # Since the finder role is overridden by parent, this should be created
        self.assert_group_member(project, user_guest_cat, True)

    def test_create_category(self):
        """Test category creation in iRODS (should not be created)"""
        category = self.make_project(
            'SubCategory', PROJECT_TYPE_CATEGORY, self.category
        )
        self.make_assignment(category, self.user, self.role_owner)
        group_name = USER_GROUP_TEMPLATE.format(uuid=category.sodar_uuid)

        self.assert_irods_coll(category, expected=False)
        with self.assertRaises(UserGroupDoesNotExist):
            self.irods.user_groups.get(group_name)

        self.plugin.perform_project_modify(
            project=category,
            action=PROJECT_ACTION_CREATE,
            project_settings=app_settings.get_all(category),
            request=self.request,
        )

        self.assert_irods_coll(category, expected=False)
        with self.assertRaises(UserGroupDoesNotExist):
            self.irods.user_groups.get(group_name)
        self.assertEqual(
            ProjectEvent.objects.filter(
                project=category,
                plugin='taskflow',
                user=self.user,
                event_name='project_create',
            ).count(),
            0,
        )

    def test_update(self):
        """Test project update in iRODS with unchanged parent"""
        project = self._make_project_tf()
        self.plugin.perform_project_modify(
            project=project,
            action=PROJECT_ACTION_UPDATE,
            project_settings=app_settings.get_all(project),
            old_data={'parent': self.category},
            request=self.request,
        )

        project_path = self.irods_backend.get_path(project)
        project_coll = self.irods.collections.get(project_path)
        self.assertEqual(
            project_coll.metadata.get_one('parent_uuid').value,
            str(self.category.sodar_uuid),
        )
        self.assert_group_member(project, self.user, True)
        self.assert_group_member(project, self.user_owner_cat, True)

    def test_update_parent(self):
        """Test project update in iRODS with changed parent"""
        project = self._make_project_tf()
        user_contributor = self.make_user('user_contributor')
        user_owner_cat_new = self.make_user('user_owner_cat_new')
        user_guest_cat_new = self.make_user('user_guest_cat_new')
        user_finder_cat_new = self.make_user('user_finder_cat_new')
        self.make_assignment_taskflow(
            project, user_contributor, self.role_contributor
        )
        project_path = self.irods_backend.get_path(project)

        self.assert_group_member(project, self.user, True)
        self.assert_group_member(project, self.user_owner_cat, True)
        self.assert_group_member(project, user_contributor, True)
        self.assert_group_member(project, user_owner_cat_new, False)
        self.assert_group_member(project, user_guest_cat_new, False)
        self.assert_group_member(project, user_finder_cat_new, False)
        project_coll = self.irods.collections.get(project_path)
        self.assertEqual(
            project_coll.metadata.get_one('parent_uuid').value,
            str(self.category.sodar_uuid),
        )

        new_category = self.make_project(
            'NewCategory', PROJECT_TYPE_CATEGORY, None
        )
        self.make_assignment(new_category, user_owner_cat_new, self.role_owner)
        self.make_assignment(new_category, user_guest_cat_new, self.role_guest)
        project.parent = new_category
        project.save()
        self.plugin.perform_project_modify(
            project=project,
            action=PROJECT_ACTION_UPDATE,
            project_settings=app_settings.get_all(project),
            old_data={'parent': self.category},
            request=self.request,
        )

        project_coll = self.irods.collections.get(project_path)
        self.assertEqual(
            project_coll.metadata.get_one('parent_uuid').value,
            str(new_category.sodar_uuid),
        )
        self.assert_group_member(project, self.user, True)
        # Owner of old category should no longer have access
        self.assert_group_member(project, self.user_owner_cat, False)
        self.assert_group_member(project, user_contributor, True)
        # Users of new category should have access
        self.assert_group_member(project, user_owner_cat_new, True)
        self.assert_group_member(project, user_guest_cat_new, True)
        # Finder should not have access
        self.assert_group_member(project, user_finder_cat_new, False)

    def test_update_category(self):
        """Test category update in iRODS with unchanged parent"""
        group_name = USER_GROUP_TEMPLATE.format(uuid=self.category.sodar_uuid)
        self.assert_irods_coll(self.category, expected=False)
        with self.assertRaises(UserGroupDoesNotExist):
            self.irods.user_groups.get(group_name)
        with self.assertRaises(UserDoesNotExist):
            self.irods.users.get(self.user_owner_cat.username)

        self.plugin.perform_project_modify(
            project=self.category,
            action=PROJECT_ACTION_UPDATE,
            project_settings=app_settings.get_all(self.category),
            old_data={'parent': None},
            old_settings=app_settings.get_all(self.category),
            request=self.request,
        )

        self.assert_irods_coll(self.category, expected=False)
        with self.assertRaises(UserGroupDoesNotExist):
            self.irods.user_groups.get(group_name)
        with self.assertRaises(UserDoesNotExist):
            self.irods.users.get(self.user_owner_cat.username)

    def test_update_category_parent(self):
        """Test category update in iRODS with changed parent"""
        # Create top category and store self.category under it
        old_category = self.make_project(
            'OldCategory', PROJECT_TYPE_CATEGORY, None
        )
        user_owner_cat_old = self.make_user('user_owner_cat_old')
        self.make_assignment(old_category, user_owner_cat_old, self.role_owner)
        self.category.parent = old_category
        self.category.save()
        # Create project with taskflow
        project = self._make_project_tf()
        # Create new root category with users
        user_owner_cat_new = self.make_user('user_owner_cat_new')
        user_guest_cat_new = self.make_user('user_guest_cat_new')
        user_finder_cat_new = self.make_user('user_finder_cat_new')
        new_category = self.make_project(
            'NewCategory', PROJECT_TYPE_CATEGORY, None
        )
        self.make_assignment(new_category, user_owner_cat_new, self.role_owner)
        self.make_assignment(new_category, user_guest_cat_new, self.role_guest)
        self.make_assignment(
            new_category, user_finder_cat_new, self.role_finder
        )

        self.assert_group_member(project, user_owner_cat_old, True)
        self.assert_group_member(project, self.user, True)
        self.assert_group_member(project, self.user_owner_cat, True)
        self.assert_group_member(project, user_owner_cat_new, False)
        self.assert_group_member(project, user_guest_cat_new, False)
        self.assert_group_member(project, user_finder_cat_new, False)
        self.assert_irods_coll(project, expected=True)

        # Move category containing project under new category
        self.category.parent = new_category
        self.category.save()
        self.plugin.perform_project_modify(
            project=self.category,
            action=PROJECT_ACTION_UPDATE,
            project_settings=app_settings.get_all(self.category),
            old_data={'parent': old_category},
            old_settings=app_settings.get_all(self.category),
            request=self.request,
        )

        self.assert_group_member(project, user_owner_cat_old, False)
        self.assert_group_member(project, self.user, True)
        self.assert_group_member(project, self.user_owner_cat, True)
        self.assert_group_member(project, user_owner_cat_new, True)
        self.assert_group_member(project, user_guest_cat_new, True)
        self.assert_group_member(project, user_finder_cat_new, False)


class TestRevertProjectModify(ModifyAPITaskflowTestBase):
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
        """Test reverting project creation"""
        self.assert_irods_coll(self.project, expected=True)
        self.assert_group_member(self.project, self.user, True)

        self.plugin.revert_project_modify(
            project=self.project,
            action=PROJECT_ACTION_CREATE,
            project_settings=app_settings.get_all(self.project),
            request=self.request,
        )

        self.assert_irods_coll(self.project, expected=False)
        with self.assertRaises(UserGroupDoesNotExist):
            self.irods.user_groups.get(self.group_name)
        tl_events = ProjectEvent.objects.filter(
            project=self.project,
            plugin='taskflow',
            user=self.user,
            event_name='project_create_revert',
        )
        self.assertEqual(tl_events.count(), 1)
        self.assertEqual(tl_events.first().get_status().status_type, 'OK')


class TestPerformRoleModify(ModifyAPITaskflowTestBase):
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
        self.user_new = self.make_user('user_new')

    def test_create(self):
        """Test creating role assignment"""
        role_as = self.make_assignment(
            self.project, self.user_new, self.role_contributor
        )
        self.assert_group_member(self.project, self.user_new, False)

        self.plugin.perform_role_modify(
            role_as=role_as,
            action=PROJECT_ACTION_CREATE,
            request=self.request,
        )

        self.assert_group_member(self.project, self.user_new, True)
        tl_events = ProjectEvent.objects.filter(
            project=self.project,
            plugin='taskflow',
            user=self.user,
            event_name='role_update',
        )
        self.assertEqual(tl_events.count(), 1)
        self.assertEqual(tl_events.first().get_status().status_type, 'OK')

    def test_create_parent(self):
        """Test creating parent assignment"""
        role_as = self.make_assignment(
            self.category, self.user_new, self.role_contributor
        )
        self.assert_group_member(self.project, self.user_new, False)

        self.plugin.perform_role_modify(
            role_as=role_as,
            action=PROJECT_ACTION_CREATE,
            request=self.request,
        )

        self.assert_group_member(self.project, self.user_new, True)
        tl_events = ProjectEvent.objects.filter(
            project=self.category,
            plugin='taskflow',
            user=self.user,
            event_name='role_update',
        )
        self.assertEqual(tl_events.count(), 1)
        self.assertEqual(tl_events.first().get_status().status_type, 'OK')

    def test_create_parent_finder(self):
        """Test creating parent finder assignment"""
        role_as = self.make_assignment(
            self.category, self.user_new, self.role_finder
        )
        self.assert_group_member(self.project, self.user_new, False)

        self.plugin.perform_role_modify(
            role_as=role_as,
            action=PROJECT_ACTION_CREATE,
            request=self.request,
        )

        # Should still be False
        self.assert_group_member(self.project, self.user_new, False)
        tl_events = ProjectEvent.objects.filter(
            project=self.category,
            plugin='taskflow',
            user=self.user,
            event_name='role_update',
        )
        self.assertEqual(tl_events.count(), 1)

    def test_create_parent_override(self):
        """Test creating overriding parent assignment"""
        # Make sub category and place project under it
        sub_cat = self.make_project(
            'SubCategory', PROJECT_TYPE_CATEGORY, self.category
        )
        self.make_assignment(sub_cat, self.user_owner_cat, self.role_owner)
        self.project.parent = sub_cat
        self.project.save()

        self.make_assignment_taskflow(sub_cat, self.user_new, self.role_finder)
        self.assert_group_member(self.project, self.user_new, False)

        role_as = self.make_assignment(
            self.category, self.user_new, self.role_guest
        )
        self.plugin.perform_role_modify(
            role_as=role_as,
            action=PROJECT_ACTION_CREATE,
            request=self.request,
        )
        self.assert_group_member(self.project, self.user_new, True)

    def test_create_parent_overridden(self):
        """Test creating overridden parent assignment"""
        self.make_assignment_taskflow(
            self.project, self.user_new, self.role_guest
        )
        self.assert_group_member(self.project, self.user_new, True)
        role_as = self.make_assignment(
            self.category, self.user_new, self.role_finder
        )
        self.plugin.perform_role_modify(
            role_as=role_as,
            action=PROJECT_ACTION_CREATE,
            request=self.request,
        )
        self.assert_group_member(self.project, self.user_new, True)

    def test_update(self):
        """Test updating member assignment in iRODS (should do nothing)"""
        role_as = self.make_assignment_taskflow(
            self.project, self.user_new, self.role_contributor
        )
        self.assert_group_member(self.project, self.user_new, True)

        self.plugin.perform_role_modify(
            role_as=role_as,
            action=PROJECT_ACTION_UPDATE,
            old_role=self.role_guest,
            request=self.request,
        )

        self.assert_group_member(self.project, self.user_new, True)
        self.assertEqual(
            ProjectEvent.objects.filter(
                project=self.project,
                plugin='taskflow',
                user=self.user,
                event_name='role_update',
            ).count(),
            1,
        )

    def test_update_to_finder(self):
        """Test updating assignment to finder"""
        role_as = self.make_assignment_taskflow(
            self.category, self.user_new, self.role_contributor
        )
        self.assert_group_member(self.project, self.user_new, True)
        role_as.role = self.role_finder
        role_as.save()
        self.plugin.perform_role_modify(
            role_as=role_as,
            action=PROJECT_ACTION_UPDATE,
            old_role=self.role_contributor,
            request=self.request,
        )
        self.assert_group_member(self.project, self.user_new, False)

    def test_update_from_finder(self):
        """Test updating assignment from finder"""
        role_as = self.make_assignment_taskflow(
            self.category, self.user_new, self.role_finder
        )
        self.assert_group_member(self.project, self.user_new, False)
        role_as.role = self.role_guest
        role_as.save()
        self.plugin.perform_role_modify(
            role_as=role_as,
            action=PROJECT_ACTION_UPDATE,
            old_role=self.role_finder,
            request=self.request,
        )
        self.assert_group_member(self.project, self.user_new, True)

    def test_update_parent_override(self):
        """Test updating overriding parent assignment"""
        sub_cat = self.make_project(
            'SubCategory', PROJECT_TYPE_CATEGORY, self.category
        )
        self.make_assignment(sub_cat, self.user_owner_cat, self.role_owner)
        self.project.parent = sub_cat
        self.project.save()

        self.make_assignment_taskflow(sub_cat, self.user_new, self.role_finder)
        role_as = self.make_assignment_taskflow(
            self.category, self.user_new, self.role_finder
        )
        self.assert_group_member(self.project, self.user_new, False)

        role_as.role = self.role_guest
        self.plugin.perform_role_modify(
            role_as=role_as,
            action=PROJECT_ACTION_UPDATE,
            old_role=self.role_finder,
            request=self.request,
        )
        self.assert_group_member(self.project, self.user_new, True)

    def test_update_parent_overridden(self):
        """Test updating overridden parent assignment"""
        sub_cat = self.make_project(
            'SubCategory', PROJECT_TYPE_CATEGORY, self.category
        )
        self.make_assignment(sub_cat, self.user_owner_cat, self.role_owner)
        self.project.parent = sub_cat
        self.project.save()

        self.make_assignment_taskflow(sub_cat, self.user_new, self.role_guest)
        role_as = self.make_assignment_taskflow(
            self.category, self.user_new, self.role_guest
        )
        self.assert_group_member(self.project, self.user_new, True)

        role_as.role = self.role_finder
        self.plugin.perform_role_modify(
            role_as=role_as,
            action=PROJECT_ACTION_UPDATE,
            old_role=self.role_guest,
            request=self.request,
        )
        self.assert_group_member(self.project, self.user_new, True)

    def test_revert_create(self):
        """Test reverting role creation"""
        role_as = self.make_assignment_taskflow(
            self.project, self.user_new, self.role_contributor
        )
        self.assert_group_member(self.project, self.user_new, True)

        self.plugin.revert_role_modify(
            role_as=role_as,
            action=PROJECT_ACTION_CREATE,
            request=self.request,
        )

        self.assert_group_member(self.project, self.user_new, False)
        tl_events = ProjectEvent.objects.filter(
            project=self.project,
            plugin='taskflow',
            user=self.user,
            event_name='role_update_revert',
        )
        self.assertEqual(tl_events.count(), 1)
        self.assertEqual(tl_events.first().get_status().status_type, 'OK')

    def test_revert_create_parent(self):
        """Test reverting parent role creation"""
        role_as = self.make_assignment_taskflow(
            self.category, self.user_new, self.role_contributor
        )
        self.assert_group_member(self.project, self.user_new, True)

        self.plugin.revert_role_modify(
            role_as=role_as,
            action=PROJECT_ACTION_CREATE,
            request=self.request,
        )

        self.assert_group_member(self.project, self.user_new, False)
        tl_events = ProjectEvent.objects.filter(
            project=self.category,
            plugin='taskflow',
            user=self.user,
            event_name='role_update_revert',
        )
        self.assertEqual(tl_events.count(), 1)
        self.assertEqual(tl_events.first().get_status().status_type, 'OK')

    def test_revert_create_parent_override(self):
        """Test reverting parent role creation with overriding child role"""
        self.make_assignment_taskflow(
            self.project, self.user_new, self.role_contributor
        )
        role_as = self.make_assignment_taskflow(
            self.category, self.user_new, self.role_guest
        )
        self.assert_group_member(self.project, self.user_new, True)
        self.plugin.revert_role_modify(
            role_as=role_as,
            action=PROJECT_ACTION_CREATE,
            request=self.request,
        )
        # User role should remain
        self.assert_group_member(self.project, self.user_new, True)

    def test_revert_create_parent_overridden(self):
        """Test reverting parent role creation with overridden child role"""
        self.make_assignment_taskflow(
            self.project, self.user_new, self.role_guest
        )
        role_as = self.make_assignment_taskflow(
            self.category, self.user_new, self.role_contributor
        )
        self.assert_group_member(self.project, self.user_new, True)
        self.plugin.revert_role_modify(
            role_as=role_as,
            action=PROJECT_ACTION_CREATE,
            request=self.request,
        )
        self.assert_group_member(self.project, self.user_new, True)

    def test_revert_create_parent_finder_override(self):
        """Test reverting parent finder role creation with overriding child role"""
        self.make_assignment_taskflow(
            self.project, self.user_new, self.role_contributor
        )
        role_as = self.make_assignment_taskflow(
            self.category, self.user_new, self.role_finder
        )
        self.assert_group_member(self.project, self.user_new, True)
        self.plugin.revert_role_modify(
            role_as=role_as,
            action=PROJECT_ACTION_CREATE,
            request=self.request,
        )
        self.assert_group_member(self.project, self.user_new, True)

    def test_revert_create_parent_finder_overridden(self):
        """Test reverting parent role creation with overridden finder role"""
        # Create subcategory and assign category under it
        sub_cat = self.make_project(
            'SubCategory', PROJECT_TYPE_CATEGORY, self.category
        )
        self.make_assignment(sub_cat, self.user_owner_cat, self.role_owner)
        self.project.parent = sub_cat
        self.project.save()

        self.make_assignment_taskflow(sub_cat, self.user_new, self.role_finder)
        role_as = self.make_assignment_taskflow(
            self.category, self.user_new, self.role_contributor
        )
        self.assert_group_member(self.project, self.user_new, True)

        self.plugin.revert_role_modify(
            role_as=role_as,
            action=PROJECT_ACTION_CREATE,
            request=self.request,
        )
        self.assert_group_member(self.project, self.user_new, False)

    def test_revert_update(self):
        """Test reverting role update for member roles (should do nothing)"""
        role_as = self.make_assignment_taskflow(
            self.project, self.user_new, self.role_contributor
        )
        self.assert_group_member(self.project, self.user_new, True)
        self.plugin.revert_role_modify(
            role_as=role_as,
            action=PROJECT_ACTION_UPDATE,
            old_role=self.role_guest,
            request=self.request,
        )
        self.assert_group_member(self.project, self.user_new, True)
        self.assertEqual(
            ProjectEvent.objects.filter(
                project=self.project,
                plugin='taskflow',
                user=self.user,
                event_name='role_update_revert',
            ).count(),
            1,
        )

    def test_revert_update_parent_to_finder(self):
        """Test reverting parent role update to finder"""
        role_as = self.make_assignment_taskflow(
            self.category, self.user_new, self.role_finder
        )
        self.assert_group_member(self.project, self.user_new, False)
        role_as.role = self.role_guest
        role_as.save()
        self.plugin.revert_role_modify(
            role_as=role_as,
            action=PROJECT_ACTION_UPDATE,
            old_role=self.role_guest,
            request=self.request,
        )
        self.assert_group_member(self.project, self.user_new, True)

    def test_revert_update_parent_from_finder(self):
        """Test reverting parent role update from finder"""
        role_as = self.make_assignment_taskflow(
            self.category, self.user_new, self.role_guest
        )
        self.assert_group_member(self.project, self.user_new, True)
        role_as.role = self.role_guest
        role_as.save()
        self.plugin.revert_role_modify(
            role_as=role_as,
            action=PROJECT_ACTION_UPDATE,
            old_role=self.role_finder,
            request=self.request,
        )
        self.assert_group_member(self.project, self.user_new, False)

    def test_revert_update_parent_from_finder_override(self):
        """Test reverting parent role update from finder with overriding child role"""
        self.make_assignment_taskflow(
            self.project, self.user_new, self.role_contributor
        )
        role_as = self.make_assignment_taskflow(
            self.category, self.user_new, self.role_guest
        )
        self.assert_group_member(self.project, self.user_new, True)
        role_as.role = self.role_guest
        role_as.save()
        self.plugin.revert_role_modify(
            role_as=role_as,
            action=PROJECT_ACTION_UPDATE,
            old_role=self.role_finder,
            request=self.request,
        )
        self.assert_group_member(self.project, self.user_new, True)


class TestPerformRoleDelete(ModifyAPITaskflowTestBase):
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
        self.group_name = self.irods_backend.get_user_group_name(self.project)

    def test_delete(self):
        """Test deleting role assignment in iRODS"""
        self.role_as = self.make_assignment_taskflow(
            self.project, self.user_new, self.role_contributor
        )
        self.assert_group_member(self.project, self.user_new, True)
        self.plugin.perform_role_delete(self.role_as, self.request)
        self.assert_group_member(self.project, self.user_new, False)
        tl_events = ProjectEvent.objects.filter(
            project=self.project,
            plugin='taskflow',
            user=self.user,
            event_name='role_delete',
        )
        self.assertEqual(tl_events.count(), 1)
        self.assertEqual(tl_events.first().get_status().status_type, 'OK')

    def test_delete_parent(self):
        """Test deleting parent role"""
        self.role_as = self.make_assignment_taskflow(
            self.category, self.user_new, self.role_contributor
        )
        self.assert_group_member(self.project, self.user_new, True)
        self.plugin.perform_role_delete(self.role_as, self.request)
        self.assert_group_member(self.project, self.user_new, False)
        tl_events = ProjectEvent.objects.filter(
            project=self.category,
            plugin='taskflow',
            user=self.user,
            event_name='role_delete',
        )
        self.assertEqual(tl_events.count(), 1)
        self.assertEqual(tl_events.first().get_status().status_type, 'OK')

    def test_delete_parent_with_local(self):
        """Test deleting parent role with local role also set"""
        self.role_as = self.make_assignment_taskflow(
            self.category, self.user_new, self.role_contributor
        )
        self.make_assignment_taskflow(
            self.project, self.user_new, self.role_guest
        )
        self.assert_group_member(self.project, self.user_new, True)
        self.plugin.perform_role_delete(self.role_as, self.request)
        self.assert_group_member(self.project, self.user_new, True)

    def test_delete_parent_finder_with_local(self):
        """Test deleting parent finder role with local role also set"""
        self.role_as = self.make_assignment_taskflow(
            self.category, self.user_new, self.role_finder
        )
        self.assert_group_member(self.project, self.user_new, False)
        self.make_assignment_taskflow(
            self.project, self.user_new, self.role_guest
        )
        self.assert_group_member(self.project, self.user_new, True)
        self.plugin.perform_role_delete(self.role_as, self.request)
        self.assert_group_member(self.project, self.user_new, True)

    def test_delete_parent_with_finder_child(self):
        """Test deleting parent role with finder role in child"""
        # Set up new top level category and place self.category under it
        top_cat = self.make_project(
            'NewTopCategory', PROJECT_TYPE_CATEGORY, None
        )
        self.make_assignment(top_cat, self.user_owner_cat, self.role_owner)
        self.category.parent = top_cat
        self.category.save()

        self.make_assignment_taskflow(
            self.category, self.user_new, self.role_finder
        )
        self.assert_group_member(self.project, self.user_new, False)
        self.role_as = self.make_assignment_taskflow(
            top_cat, self.user_new, self.role_guest
        )
        self.assert_group_member(self.project, self.user_new, True)

        self.plugin.perform_role_delete(self.role_as, self.request)
        self.assert_group_member(self.project, self.user_new, False)

    def test_revert(self):
        """Test reverting role assignment deletion"""
        self.role_as = self.make_assignment_taskflow(
            self.project, self.user_new, self.role_contributor
        )
        self.assert_group_member(self.project, self.user_new, True)
        self.plugin.perform_role_delete(self.role_as, self.request)
        self.assert_group_member(self.project, self.user_new, False)

        self.plugin.revert_role_delete(self.role_as, self.request)
        self.assert_group_member(self.project, self.user_new, True)
        tl_events = ProjectEvent.objects.filter(
            project=self.project,
            plugin='taskflow',
            user=self.user,
            event_name='role_delete_revert',
        )
        self.assertEqual(tl_events.count(), 1)
        self.assertEqual(tl_events.first().get_status().status_type, 'OK')

    def test_revert_parent(self):
        """Test reverting parent role deletion"""
        self.role_as = self.make_assignment_taskflow(
            self.category, self.user_new, self.role_contributor
        )
        self.assert_group_member(self.project, self.user_new, True)
        self.plugin.perform_role_delete(self.role_as, self.request)
        self.assert_group_member(self.project, self.user_new, False)

        self.plugin.revert_role_delete(self.role_as, self.request)
        self.assert_group_member(self.project, self.user_new, True)
        tl_events = ProjectEvent.objects.filter(
            project=self.category,
            plugin='taskflow',
            user=self.user,
            event_name='role_delete_revert',
        )
        self.assertEqual(tl_events.count(), 1)
        self.assertEqual(tl_events.first().get_status().status_type, 'OK')

    def test_revert_parent_with_local(self):
        """Test reverting parent role deletion with local member role"""
        self.role_as = self.make_assignment_taskflow(
            self.category, self.user_new, self.role_contributor
        )
        self.make_assignment_taskflow(
            self.project, self.user_new, self.role_guest
        )
        self.assert_group_member(self.project, self.user_new, True)
        self.plugin.perform_role_delete(self.role_as, self.request)
        self.assert_group_member(self.project, self.user_new, True)

        self.plugin.revert_role_delete(self.role_as, self.request)
        self.assert_group_member(self.project, self.user_new, True)

    def test_revert_parent_finder_with_local(self):
        """Test reverting parent finder role deletion with local member role"""
        self.role_as = self.make_assignment_taskflow(
            self.category, self.user_new, self.role_finder
        )
        self.assert_group_member(self.project, self.user_new, False)
        self.make_assignment_taskflow(
            self.project, self.user_new, self.role_guest
        )
        self.assert_group_member(self.project, self.user_new, True)
        self.plugin.perform_role_delete(self.role_as, self.request)
        self.assert_group_member(self.project, self.user_new, True)

        self.plugin.revert_role_delete(self.role_as, self.request)
        self.assert_group_member(self.project, self.user_new, True)

    def test_revert_parent_with_finder_child(self):
        """Test reverting parent role deletion with finder role in child"""
        top_cat = self.make_project(
            'NewTopCategory', PROJECT_TYPE_CATEGORY, None
        )
        self.make_assignment(top_cat, self.user_owner_cat, self.role_owner)
        self.category.parent = top_cat
        self.category.save()

        self.make_assignment_taskflow(
            self.category, self.user_new, self.role_finder
        )
        self.assert_group_member(self.project, self.user_new, False)
        self.role_as = self.make_assignment_taskflow(
            top_cat, self.user_new, self.role_guest
        )
        self.assert_group_member(self.project, self.user_new, True)
        self.plugin.perform_role_delete(self.role_as, self.request)
        self.assert_group_member(self.project, self.user_new, False)

        self.plugin.revert_role_delete(self.role_as, self.request)
        self.assert_group_member(self.project, self.user_new, True)


class TestPerformOwnerTransfer(ModifyAPITaskflowTestBase):
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

    def test_transfer_category(self):
        """Test category owner transfer in iRODS"""
        self.make_assignment_taskflow(
            self.category, self.user_new, self.role_contributor
        )
        self.assert_group_member(self.project, self.user, True)
        self.assert_group_member(self.project, self.user_new, True)
        self.assert_group_member(self.project, self.user_owner_cat, True)

        self.plugin.perform_owner_transfer(
            project=self.category,
            new_owner=self.user_new,
            old_owner=self.user_owner_cat,
            old_owner_role=self.role_contributor,
            request=self.request,
        )

        self.assert_group_member(self.project, self.user, True)
        self.assert_group_member(self.project, self.user_new, True)
        self.assert_group_member(self.project, self.user_owner_cat, True)
        tl_events = ProjectEvent.objects.filter(
            project=self.category,
            plugin='taskflow',
            user=self.user,
            event_name='role_owner_transfer',
        )
        self.assertEqual(tl_events.count(), 1)
        self.assertEqual(tl_events.first().get_status().status_type, 'OK')

    def test_transfer_category_old_owner_finder(self):
        """Test category owner transfer with finder role for old owner"""
        self.make_assignment_taskflow(
            self.category, self.user_new, self.role_contributor
        )
        self.assert_group_member(self.project, self.user, True)
        self.assert_group_member(self.project, self.user_new, True)
        self.assert_group_member(self.project, self.user_owner_cat, True)

        self.plugin.perform_owner_transfer(
            project=self.category,
            new_owner=self.user_new,
            old_owner=self.user_owner_cat,
            old_owner_role=self.role_finder,
            request=self.request,
        )

        self.assert_group_member(self.project, self.user, True)
        self.assert_group_member(self.project, self.user_new, True)
        self.assert_group_member(self.project, self.user_owner_cat, False)

    def test_transfer_category_to_finder(self):
        """Test category owner transfer to user with finder role"""
        self.make_assignment_taskflow(
            self.category, self.user_new, self.role_finder
        )
        self.assert_group_member(self.project, self.user, True)
        self.assert_group_member(self.project, self.user_new, False)
        self.assert_group_member(self.project, self.user_owner_cat, True)

        self.plugin.perform_owner_transfer(
            project=self.category,
            new_owner=self.user_new,
            old_owner=self.user_owner_cat,
            old_owner_role=self.role_contributor,
            request=self.request,
        )

        self.assert_group_member(self.project, self.user, True)
        self.assert_group_member(self.project, self.user_new, True)
        self.assert_group_member(self.project, self.user_owner_cat, True)

    def test_transfer_project(self):
        """Test project owner transfer in iRODS"""
        self.make_assignment_taskflow(
            self.project, self.user_new, self.role_contributor
        )
        self.assert_group_member(self.project, self.user, True)
        self.assert_group_member(self.project, self.user_new, True)
        self.assert_group_member(self.project, self.user_owner_cat, True)

        self.plugin.perform_owner_transfer(
            project=self.project,
            new_owner=self.user_new,
            old_owner=self.user,
            old_owner_role=self.role_contributor,
            request=self.request,
        )

        self.assert_group_member(self.project, self.user, True)
        self.assert_group_member(self.project, self.user_new, True)
        self.assert_group_member(self.project, self.user_owner_cat, True)

    def test_transfer_project_old_owner_finder(self):
        """Test project owner transfer with finder role for old user"""
        self.make_assignment_taskflow(
            self.project, self.user_new, self.role_contributor
        )
        self.assert_group_member(self.project, self.user, True)
        self.assert_group_member(self.project, self.user_new, True)
        self.assert_group_member(self.project, self.user_owner_cat, True)

        self.plugin.perform_owner_transfer(
            project=self.project,
            new_owner=self.user_new,
            old_owner=self.user,
            old_owner_role=self.role_finder,
            request=self.request,
        )

        self.assert_group_member(self.project, self.user, False)
        self.assert_group_member(self.project, self.user_new, True)
        self.assert_group_member(self.project, self.user_owner_cat, True)


class TestPerformProjectSync(ModifyAPITaskflowTestBase):
    """Tests for perform_project_sync()"""

    def test_sync_new_project(self):
        """Test sync with new project"""
        # NOTE: Should be identical to test_create() in TestPerformProjectModify
        project = self.make_project(
            'NewProject', PROJECT_TYPE_PROJECT, self.category
        )
        self.make_assignment(project, self.user, self.role_owner)
        group_name = self.irods_backend.get_user_group_name(project)
        self.assert_irods_coll(project, expected=False)
        with self.assertRaises(UserGroupDoesNotExist):
            self.irods.user_groups.get(group_name)
        with self.assertRaises(UserDoesNotExist):
            self.irods.users.get(self.user.username)
        with self.assertRaises(UserDoesNotExist):
            self.irods.users.get(self.user_owner_cat.username)

        self.plugin.perform_project_sync(project)

        self.assert_irods_coll(project, expected=True)
        group = self.irods.user_groups.get(group_name)
        self.assertIsInstance(group, iRODSUserGroup)
        self.assert_irods_access(
            group_name,
            self.irods_backend.get_path(project),
            self.irods_access_read,
        )
        self.assertIsInstance(
            self.irods.users.get(self.user.username), iRODSUser
        )
        self.assert_group_member(project, self.user, True)
        project_coll = self.irods.collections.get(
            self.irods_backend.get_path(project)
        )
        self.assertEqual(
            project_coll.metadata.get_one('parent_uuid').value,
            str(self.category.sodar_uuid),
        )
        # Assert inherited category owner status
        self.assertIsInstance(
            self.irods.users.get(self.user_owner_cat.username), iRODSUser
        )
        self.assert_group_member(project, self.user_owner_cat, True)
        tl_events = ProjectEvent.objects.filter(
            project=project,
            plugin='taskflow',
            user=None,
            event_name='project_sync',
        )
        self.assertEqual(tl_events.count(), 1)
        self.assertEqual(tl_events.first().get_status().status_type, 'OK')

    def test_sync_existing(self):
        """Test sync with existing identical iRODS project (should not do anything)"""
        project = self._make_project_tf()
        group_name = self.irods_backend.get_user_group_name(project)

        self.assert_irods_coll(project, expected=True)
        group = self.irods.user_groups.get(group_name)
        self.assertIsInstance(group, iRODSUserGroup)
        self.assert_irods_access(
            group_name,
            self.irods_backend.get_path(project),
            self.irods_access_read,
        )
        self.assert_group_member(project, self.user, True)
        self.assert_group_member(project, self.user_owner_cat, True)

        self.plugin.perform_project_sync(project)

        self.assert_irods_coll(project, expected=True)
        self.assert_irods_access(
            group_name,
            self.irods_backend.get_path(project),
            self.irods_access_read,
        )
        self.assert_group_member(project, self.user, True)
        self.assert_group_member(project, self.user_owner_cat, True)
        tl_events = ProjectEvent.objects.filter(
            project=project,
            plugin='taskflow',
            user=None,
            event_name='project_sync',
        )
        self.assertEqual(tl_events.count(), 1)

    def test_sync_new_member(self):
        """Test sync with existing iRODS project and new member"""
        project = self._make_project_tf()
        # Set up new user and assignment without taskflow
        user_new = self.make_user('user_new')
        self.make_assignment(project, user_new, self.role_contributor)
        with self.assertRaises(UserDoesNotExist):
            self.irods.users.get(user_new.username)

        self.plugin.perform_project_sync(project)

        self.assert_irods_coll(project, expected=True)
        self.assert_group_member(project, self.user, True)
        self.assert_group_member(project, self.user_owner_cat, True)
        self.assert_group_member(project, user_new, True)

    def test_sync_new_inherited(self):
        """Test sync with new inherited member"""
        project = self._make_project_tf()
        # Set up new user and assignment without taskflow
        user_new = self.make_user('user_new')
        self.make_assignment(self.category, user_new, self.role_contributor)
        with self.assertRaises(UserDoesNotExist):
            self.irods.users.get(user_new.username)

        self.plugin.perform_project_sync(project)

        self.assert_irods_coll(project, expected=True)
        self.assert_group_member(project, self.user, True)
        self.assert_group_member(project, self.user_owner_cat, True)
        self.assert_group_member(project, user_new, True)

    def test_sync_new_inherited_finder(self):
        """Test sync with new inherited finder"""
        project = self._make_project_tf()
        user_new = self.make_user('user_new')
        self.make_assignment(self.category, user_new, self.role_finder)
        with self.assertRaises(UserDoesNotExist):
            self.irods.users.get(user_new.username)

        self.plugin.perform_project_sync(project)

        self.assert_irods_coll(project, expected=True)
        self.assert_group_member(project, self.user, True)
        self.assert_group_member(project, self.user_owner_cat, True)
        # Finder should not have been created
        with self.assertRaises(UserDoesNotExist):
            self.irods.users.get(user_new.username)

    def test_sync_removed_role(self):
        """Test sync with removed role"""
        project = self._make_project_tf()
        # Create new user and role with taskflow
        user_new = self.make_user('user_new')
        self.make_assignment_taskflow(project, user_new, self.role_guest)
        self.assert_group_member(project, user_new, True)
        # Delete role without taskflow
        RoleAssignment.objects.get(project=project, user=user_new).delete()
        # Should still be true in iRODS
        self.assert_group_member(project, user_new, True)

        self.plugin.perform_project_sync(project)

        self.assert_group_member(project, self.user, True)
        self.assert_group_member(project, self.user_owner_cat, True)
        self.assert_group_member(project, user_new, False)

    def test_sync_removed_inherited(self):
        """Test sync with removed inherited role"""
        project = self._make_project_tf()
        user_new = self.make_user('user_new')
        self.make_assignment_taskflow(self.category, user_new, self.role_guest)
        self.assert_group_member(project, user_new, True)
        RoleAssignment.objects.get(
            project=self.category, user=user_new
        ).delete()
        self.assert_group_member(project, user_new, True)

        self.plugin.perform_project_sync(project)

        self.assert_group_member(project, self.user, True)
        self.assert_group_member(project, self.user_owner_cat, True)
        self.assert_group_member(project, user_new, False)

    def test_sync_inherited_finder(self):
        """Test sync with role changed to finder"""
        project = self._make_project_tf()
        user_new = self.make_user('user_new')
        role_as = self.make_assignment_taskflow(
            self.category, user_new, self.role_guest
        )
        self.assert_group_member(project, user_new, True)
        # Change role to finder locally
        role_as.role = self.role_finder
        role_as.save()
        self.assert_group_member(project, user_new, True)

        self.plugin.perform_project_sync(project)

        self.assert_group_member(project, self.user, True)
        self.assert_group_member(project, self.user_owner_cat, True)
        self.assert_group_member(project, user_new, False)

    def test_sync_removed_user(self):
        """Test sync with removed SODAR user"""
        project = self._make_project_tf()
        user_new = self.make_user('user_new')
        self.make_assignment_taskflow(project, user_new, self.role_guest)
        self.assert_group_member(project, user_new, True)
        # Delete user
        user_new.delete()
        # Should still be true in iRODS
        self.assert_group_member(project, user_new, True)

        self.plugin.perform_project_sync(project)

        self.assert_group_member(project, self.user, True)
        self.assert_group_member(project, self.user_owner_cat, True)
        self.assert_group_member(project, user_new, False)

    def test_sync_removed_user_inherited(self):
        """Test sync with removed SODAR user with inherited role"""
        project = self._make_project_tf()
        user_new = self.make_user('user_new')
        self.make_assignment_taskflow(self.category, user_new, self.role_guest)
        self.assert_group_member(project, user_new, True)
        user_new.delete()
        self.assert_group_member(project, user_new, True)

        self.plugin.perform_project_sync(project)

        self.assert_group_member(project, self.user, True)
        self.assert_group_member(project, self.user_owner_cat, True)
        self.assert_group_member(project, user_new, False)
