"""Rules for the taskflowbackend app"""

import rules

# Projectroles dependency
from projectroles import rules as pr_rules  # To access common predicates


# Permissions ------------------------------------------------------------------


# Allow viewing project lock status
rules.add_perm(
    'taskflowbackend.view_lock',
    pr_rules.is_project_owner
    | pr_rules.is_project_delegate
    | pr_rules.is_project_contributor
    | pr_rules.is_project_guest,
)
