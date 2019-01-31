import rules

# Projectroles dependency
from projectroles import rules as pr_rules  # To access common predicates


# Predicates -------------------------------------------------------------


# TODO: If we need to assign new predicates, we do it here


# Rules ------------------------------------------------------------------


# TODO: Rules should not be needed, use permissions for user rights


# Permissions ------------------------------------------------------------


# Allow viewing iRODS file statistics
rules.add_perm(
    'irodsbackend.view_stats',
    pr_rules.is_project_owner
    | pr_rules.is_project_delegate
    | pr_rules.is_project_contributor
    | pr_rules.is_project_guest,
)

# Allow viewing iRODS file lists
rules.add_perm(
    'irodsbackend.view_files',
    pr_rules.is_project_owner
    | pr_rules.is_project_delegate
    | pr_rules.is_project_contributor
    | pr_rules.is_project_guest,
)
