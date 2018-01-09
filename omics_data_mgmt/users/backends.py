from django_auth_ldap.backend import LDAPBackend, _LDAPUser


# Charite LDAP backend
class ChariteLDAPBackend(LDAPBackend):
    settings_prefix = 'AUTH_CHARITE_LDAP_'

    def authenticate(self, username, password, **kwargs):
        # Ensure username has proper suffix
        if (username.find('@') == -1 or
                username.split('@')[1].upper() != 'CHARITE'):
            return None

        ldap_user = _LDAPUser(self, username=username.split('@')[0].strip())
        user = ldap_user.authenticate(password)

        return user

    def ldap_to_django_username(self, username):
        return username + '@CHARITE'

    def django_to_ldap_username(self, username):
        return username.split('@')[0]


# MDC AD backend
class MDCLDAPBackend(LDAPBackend):
    settings_prefix = 'AUTH_MDC_LDAP_'

    def authenticate(self, username, password, **kwargs):
        # Ensure username has proper suffix
        if (username.find('@') == -1 or
                username.split('@')[1].upper() != 'MDC-BERLIN'):
            return None

        ldap_user = _LDAPUser(self, username=username.split('@')[0].strip())
        user = ldap_user.authenticate(password)

        return user

    def ldap_to_django_username(self, username):
        return username + '@MDC-BERLIN'

    def django_to_ldap_username(self, username):
        return username.split('@')[0]
