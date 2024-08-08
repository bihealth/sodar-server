"""Rules for the isatemplates app"""

import rules


# Predicates -------------------------------------------------------------


# N/A


# Rules ------------------------------------------------------------------


# Rules should not be needed, use permissions for user rights


# Permissions ------------------------------------------------------------


# Allow viewing template list
rules.add_perm('isatemplates.view_list', rules.is_superuser)

# Allow viewin template details
rules.add_perm('isatemplates.view_template', rules.is_superuser)

# Allow creation of templates
rules.add_perm('isatemplates.create_template', rules.is_superuser)

# Allow updating of templates
rules.add_perm('isatemplates.update_template', rules.is_superuser)

# Allow deletion of templates
rules.add_perm('isatemplates.delete_template', rules.is_superuser)
