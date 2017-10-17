import rules

# Projectroles dependency
from projectroles import rules as pr_rules  # To access common predicates


# Predicates -------------------------------------------------------------


# TODO: If we need to assign new predicates, we do it here


# Rules ------------------------------------------------------------------


# TODO: Rules should not be needed, use permissions for user rights


# Permissions ------------------------------------------------------------

# TODO: TBD: Should we split file and folder rules into different ones?

# Allow viewing data in project
rules.add_perm(
    'filesfolders.view_data',
    rules.is_superuser | pr_rules.is_project_owner |
    pr_rules.is_project_delegate | pr_rules.is_project_staff |
    pr_rules.is_project_contributor | pr_rules.is_project_guest)

# Allow adding data to project
rules.add_perm(
    'filesfolders.add_data',
    rules.is_superuser | pr_rules.is_project_owner |
    pr_rules.is_project_delegate | pr_rules.is_project_staff |
    pr_rules.is_project_contributor)

# Allow updating own data in project
rules.add_perm(
    'filesfolders.update_data_own',
    rules.is_superuser | pr_rules.is_project_owner |
    pr_rules.is_project_delegate | pr_rules.is_project_staff |
    pr_rules.is_project_contributor)

# Allow updating all data in project
rules.add_perm(
    'filesfolders.update_data_all',
    rules.is_superuser | pr_rules.is_project_owner |
    pr_rules.is_project_delegate | pr_rules.is_project_staff)

# Allow sharing public temporary URLs
rules.add_perm(
    'filesfolders.share_public_link',
    rules.is_superuser | pr_rules.is_project_owner |
    pr_rules.is_project_delegate | pr_rules.is_project_staff |
    pr_rules.is_project_contributor)
