import rules

# Projectroles dependency
from projectroles import rules as pr_rules  # To access common predicates


# Predicates -------------------------------------------------------------------


# TODO: If we need to assign new predicates, we do it here


# Rules ------------------------------------------------------------------------


# TODO: Rules should not be needed, use permissions for user rights


# Permissions ------------------------------------------------------------------


# Allow viewing user's own landing zones for the project
rules.add_perm(
    'landingzones.view_zones_own',
    pr_rules.is_project_owner
    | pr_rules.is_project_delegate
    | pr_rules.is_project_contributor,
)

# Allow viewing all landing zones for the project
rules.add_perm(
    'landingzones.view_zones_all',
    pr_rules.is_project_owner | pr_rules.is_project_delegate,
)

# Allow creating landing zones
rules.add_perm(
    'landingzones.add_zones',
    pr_rules.is_project_owner
    | pr_rules.is_project_delegate
    | pr_rules.is_project_contributor,
)

# Allow modifying or deleting the user's own landing zones
rules.add_perm(
    'landingzones.update_zones_own',
    pr_rules.is_project_owner
    | pr_rules.is_project_delegate
    | pr_rules.is_project_contributor,
)

# Allow modifying or deleting all landing zones
rules.add_perm(
    'landingzones.update_zones_all',
    pr_rules.is_project_owner | pr_rules.is_project_delegate,
)
