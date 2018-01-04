import rules


# Predicates -------------------------------------------------------------


# None needed right now


# Rules ------------------------------------------------------------------


# Rules should not be needed, use permissions for user rights


# Permissions ------------------------------------------------------------


# Allow viewing alert details
rules.add_perm(
    'adminalerts.view_alert',
    rules.is_authenticated)

# Allow viewing alert list
rules.add_perm(
    'adminalerts.view_list',
    rules.is_superuser)

# Allow creation of alerts
rules.add_perm(
    'adminalerts.create_alert',
    rules.is_superuser)

# Allow updating alerts
rules.add_perm(
    'adminalerts.update_alert',
    rules.is_superuser)
