import rules

from django.conf import settings

# Projectroles dependency
from projectroles import rules as pr_rules  # To access common predicates
from projectroles.app_settings import AppSettingAPI
from projectroles.models import ROLE_RANKING, SODAR_CONSTANTS


app_settings = AppSettingAPI()


# SODAR constants
PROJECT_ROLE_CONTRIBUTOR = SODAR_CONSTANTS['PROJECT_ROLE_CONTRIBUTOR']

# Local constants
APP_NAME = 'landingzones'


# Helpers ----------------------------------------------------------------------


def is_not_restricted(user, project):
    """Helper for zone access predicates"""
    s = app_settings.get(APP_NAME, 'zone_access_restrict', project=project)
    if not s:
        return True
    c_rank = ROLE_RANKING[PROJECT_ROLE_CONTRIBUTOR]
    role_as = project.get_role(user)
    return (
        role_as
        and role_as.role.rank < c_rank
        or (s == user.username and role_as.role.rank == c_rank)
    )


# Predicates -------------------------------------------------------------------


@rules.predicate
def can_create_zone(user, obj):
    """Allow creating a new landing zone"""
    if settings.LANDINGZONES_DISABLE_FOR_USERS:
        return False
    inv = obj.investigations.filter(active=True).first()
    if not inv or not inv.irods_status:
        return False
    return is_not_restricted(user, obj)


@rules.predicate
def can_modify_zone(user, obj):
    """Allow modifying an existing landing zone"""
    if settings.LANDINGZONES_DISABLE_FOR_USERS:
        return False
    return is_not_restricted(user, obj)


# Permissions ------------------------------------------------------------------


# Allow viewing and listing user's own landing zones for the project
rules.add_perm(
    'landingzones.view_zone_own',
    pr_rules.is_project_owner
    | pr_rules.is_project_delegate
    | pr_rules.is_project_contributor,
)

# Allow viewing and listing all landing zones for the project
rules.add_perm(
    'landingzones.view_zone_all',
    pr_rules.is_project_owner | pr_rules.is_project_delegate,
)

# Allow creating landing zones
rules.add_perm(
    'landingzones.create_zone',
    (
        pr_rules.is_project_owner
        | pr_rules.is_project_delegate
        | pr_rules.is_project_contributor
    )
    & pr_rules.can_modify_project_data
    & can_create_zone,
)

# Allow updating the user's own landing zones
rules.add_perm(
    'landingzones.update_zone_own',
    (
        pr_rules.is_project_owner
        | pr_rules.is_project_delegate
        | pr_rules.is_project_contributor
    )
    & pr_rules.can_modify_project_data
    & can_modify_zone,
)

# Allow moving files from the user's own landing zones
rules.add_perm(
    'landingzones.move_zone_own',
    (
        pr_rules.is_project_owner
        | pr_rules.is_project_delegate
        | pr_rules.is_project_contributor
    )
    & pr_rules.can_modify_project_data
    & can_modify_zone,
)

# Allow deleting the user's own landing zones
# NOTE: Is allowed if project is archived
rules.add_perm(
    'landingzones.delete_zone_own',
    (
        pr_rules.is_project_owner
        | pr_rules.is_project_delegate
        | pr_rules.is_project_contributor
    )
    & pr_rules.is_site_writable
    & can_modify_zone,
)

# Allow updating any landing zone
rules.add_perm(
    'landingzones.update_zone_all',
    (pr_rules.is_project_owner | pr_rules.is_project_delegate)
    & can_modify_zone
    & pr_rules.can_modify_project_data,
)

# Allow moving files from any landing zone
rules.add_perm(
    'landingzones.move_zone_all',
    (pr_rules.is_project_owner | pr_rules.is_project_delegate)
    & can_modify_zone
    & pr_rules.can_modify_project_data,
)

# Allow deleting any landing zone
# NOTE: Is allowed if project is archived
rules.add_perm(
    'landingzones.delete_zone_all',
    (pr_rules.is_project_owner | pr_rules.is_project_delegate)
    & pr_rules.is_site_writable
    & can_modify_zone,
)
