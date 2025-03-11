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
    pr_rules.is_project_owner
    | pr_rules.is_project_delegate
    | pr_rules.is_project_contributor
    | pr_rules.is_project_guest,
)

# Allow creating, importing or modifying the project's sample sheet
rules.add_perm(
    'samplesheets.edit_sheet',
    pr_rules.can_modify_project_data
    & (
        pr_rules.is_project_owner
        | pr_rules.is_project_delegate
        | pr_rules.is_project_contributor
    ),
)

# Allow managing sample sheet configuration and editing
rules.add_perm(
    'samplesheets.manage_sheet',
    pr_rules.can_modify_project_data
    & (pr_rules.is_project_owner | pr_rules.is_project_delegate),
)

# Allow exporting a sample sheet from project
rules.add_perm(
    'samplesheets.export_sheet',
    pr_rules.is_project_owner
    | pr_rules.is_project_delegate
    | pr_rules.is_project_contributor
    | pr_rules.is_project_guest,
)

# Allow viewing sample sheet versions
rules.add_perm(
    'samplesheets.view_versions',
    pr_rules.is_project_owner
    | pr_rules.is_project_delegate
    | pr_rules.is_project_contributor
    | pr_rules.is_project_guest,
)

# Allow creating collection structure in iRODS
rules.add_perm(
    'samplesheets.create_colls',
    pr_rules.can_modify_project_data
    & (
        pr_rules.is_project_owner
        | pr_rules.is_project_delegate
        | pr_rules.is_project_contributor
    ),
)

# Allow updating sheet cache (also allowed for archived projects)
rules.add_perm(
    'samplesheets.update_cache',
    pr_rules.is_site_writable
    & (
        pr_rules.is_project_owner
        | pr_rules.is_project_delegate
        | pr_rules.is_project_contributor
    ),
)

# Allow deleting the project sample sheet
rules.add_perm(
    'samplesheets.delete_sheet',
    pr_rules.can_modify_project_data
    & (
        pr_rules.is_project_owner
        | pr_rules.is_project_delegate
        | pr_rules.is_project_contributor
    ),
)

# Allow viewing iRODS access tickets
rules.add_perm(
    'samplesheets.view_tickets',
    pr_rules.is_project_owner
    | pr_rules.is_project_delegate
    | pr_rules.is_project_contributor,
)

# Allow creating, updating or deleting iRODS access tickets
# NOTE: We allow this for archived projects
rules.add_perm(
    'samplesheets.edit_tickets',
    pr_rules.is_site_writable
    & (
        pr_rules.is_project_owner
        | pr_rules.is_project_delegate
        | pr_rules.is_project_contributor
    ),
)
