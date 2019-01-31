import rules


# Predicates -------------------------------------------------------------


# None needed right now


# Rules ------------------------------------------------------------------


# Rules should not be needed, use permissions for user rights


# Permissions ------------------------------------------------------------


# Allow viewing iRODS information
rules.add_perm('irodsinfo.view_info', rules.is_authenticated)

# Allow downloading iRODS configuration and certificate
rules.add_perm('irodsinfo.get_config', rules.is_authenticated)
