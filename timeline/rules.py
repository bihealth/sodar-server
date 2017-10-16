"""Access rules for the timeline app"""

import rules

# Projectroles dependency
from projectroles import rules as pr_rules  # To access common predicates


# Predicates -------------------------------------------------------------


# TODO: If we need to assign new predicates, we do it here


# Rules ------------------------------------------------------------------


# TODO: Rules should not be needed, use permissions for user rights


# Permissions ------------------------------------------------------------


# Allow viewing project timeline
rules.add_perm(
    'timeline.view_timeline',
    rules.is_superuser | pr_rules.is_project_owner |
    pr_rules.is_project_delegate | pr_rules.is_project_staff |
    pr_rules.is_project_contributor | pr_rules.is_project_guest)

# Allow viewing classified event
rules.add_perm(
    'timeline.view_classified_event',
    rules.is_superuser | pr_rules.is_project_owner |
    pr_rules.is_project_delegate)
