import rules

from .models import RoleAssignment, OMICS_CONSTANTS

# Omics constants
PROJECT_ROLE_OWNER = OMICS_CONSTANTS['PROJECT_ROLE_OWNER']
PROJECT_ROLE_DELEGATE = OMICS_CONSTANTS['PROJECT_ROLE_DELEGATE']
PROJECT_ROLE_STAFF = OMICS_CONSTANTS['PROJECT_ROLE_STAFF']
PROJECT_ROLE_CONTRIBUTOR = OMICS_CONSTANTS['PROJECT_ROLE_CONTRIBUTOR']
PROJECT_ROLE_GUEST = OMICS_CONSTANTS['PROJECT_ROLE_GUEST']


# Predicates -------------------------------------------------------------


@rules.predicate
def is_project_owner(user, obj):
    """Whether or not the user has the role of project owner"""
    assignment = RoleAssignment.objects.get_assignment(user, obj)

    if assignment:
        return assignment.role.name == PROJECT_ROLE_OWNER

    return False


@rules.predicate
def is_project_delegate(user, obj):
    """Whether or not the user has the role of project delegate"""
    assignment = RoleAssignment.objects.get_assignment(user, obj)

    if assignment:
        return assignment.role.name == PROJECT_ROLE_DELEGATE

    return False


@rules.predicate
def is_project_contributor(user, obj):
    """Whether or not the user has the role of project contributor"""
    assignment = RoleAssignment.objects.get_assignment(user, obj)

    if assignment:
        return assignment.role.name == PROJECT_ROLE_CONTRIBUTOR

    return False


@rules.predicate
def is_project_guest(user, obj):
    """Whether or not the user has the role of project guest"""
    assignment = RoleAssignment.objects.get_assignment(user, obj)

    if assignment:
        return assignment.role.name == PROJECT_ROLE_GUEST

    return False


@rules.predicate
def is_project_staff(user, obj):
    """Whether or not the user has the role of project staff"""
    assignment = RoleAssignment.objects.get_assignment(user, obj)

    if assignment:
        return assignment.role.name == PROJECT_ROLE_STAFF

    return False


@rules.predicate
def has_project_role(user, obj):
    """Whether or not the user has any role in the project"""
    return RoleAssignment.objects.get_assignment(user, obj) is not None


@rules.predicate
def has_roles(user):
    """Whether or not the user has any roles set in the system"""
    return RoleAssignment.objects.filter(user=user).count() > 0


# Rules ------------------------------------------------------------------


# Rules should not be needed, use permissions for user rights


# Permissions ------------------------------------------------------------


# Allow viewing project details
rules.add_perm(
    'projectroles.view_project',
    rules.is_superuser | has_project_role)

# Allow project updating
rules.add_perm(
    'projectroles.update_project',
    rules.is_superuser | is_project_owner | is_project_delegate)

# Allow creation of projects
rules.add_perm(
    'projectroles.create_project',
    rules.is_superuser | is_project_owner)

# Allow updating project settings
rules.add_perm(
    'projectroles.update_project_settings',
    rules.is_superuser | is_project_owner | is_project_delegate)

# Allow viewing project roles
rules.add_perm(
    'projectroles.view_project_roles',
    rules.is_superuser | is_project_owner | is_project_delegate |
    is_project_staff | is_project_contributor | is_project_guest)

# Allow updating project owner
rules.add_perm(
    'projectroles.update_project_owner',
    rules.is_superuser | is_project_owner)

# Allow updating project delegate
rules.add_perm(
    'projectroles.update_project_delegate',
    rules.is_superuser | is_project_owner)

# Allow updating project staff
rules.add_perm(
    'projectroles.update_project_staff',
    rules.is_superuser | is_project_owner | is_project_delegate)

# Allow updating project members
rules.add_perm(
    'projectroles.update_project_members',
    rules.is_superuser | is_project_owner | is_project_delegate |
    is_project_staff)

# Allow inviting users to project via email
rules.add_perm(
    'projectroles.invite_users',
    rules.is_superuser | is_project_owner | is_project_delegate)
