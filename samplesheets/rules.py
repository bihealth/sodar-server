import rules

# Projectroles dependency
from projectroles import rules as pr_rules  # To access common predicates


# Predicates -------------------------------------------------------------


# TODO: If we need to assign new predicates, we do it here


# Rules ------------------------------------------------------------------


# TODO: Rules should not be needed, use permissions for user rights


# Permissions ------------------------------------------------------------


# Allow viewing the sample sheet of the project
rules.add_perm(
    'samplesheets.view_sheet',
    rules.is_superuser | pr_rules.is_project_owner |
    pr_rules.is_project_delegate | pr_rules.is_project_contributor |
    pr_rules.is_project_guest)

# Allow creating, importing or modifying the project's JSON sample sheet
rules.add_perm(
    'samplesheets.edit_sheet',
    rules.is_superuser | pr_rules.is_project_owner |
    pr_rules.is_project_delegate)

# Allow exporting a JSON sample sheet from project
rules.add_perm(
    'samplesheets.export_sheet',
    rules.is_superuser | pr_rules.is_project_owner |
    pr_rules.is_project_delegate | pr_rules.is_project_contributor)

# Allow creating directory structure in iRODS
rules.add_perm(
    'samplesheets.create_dirs',
    rules.is_superuser | pr_rules.is_project_owner |
    pr_rules.is_project_delegate)

# Allow deleting the project sample sheet
rules.add_perm(
    'samplesheets.delete_sheet',
    rules.is_superuser | pr_rules.is_project_owner |
    pr_rules.is_project_delegate)
