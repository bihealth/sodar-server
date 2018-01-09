Deploy
======

This assumes you have `Flynn <https://flynn.io>`_ installed and cluster(s) set
up with "flynn cluster add". We use multiple clusters for e.g. testing and
production, so make sure to always include the cluster name in your commands.


Create app:

.. code-block:: shell

    flynn -c {cluster-name} create {app-name} --remote {remote-name}

Add database resources:

.. code-block:: shell

    flynn -c {cluster-name} resource add postgres
    flynn -c {cluster-name} resource add redis

Edit the app’s flynn env as follows.

.. code-block:: shell

    flynn -c {cluster-name} env set \
        LDAP_ENABLED=1 \
        AUTH_CHARITE_LDAP_BIND_DN=CN={DN HERE} \
        AUTH_CHARITE_LDAP_BIND_PASSWORD={PASSWORD HERE} \
        AUTH_CHARITE_LDAP_SERVER_URI={URI HERE} \
        AUTH_CHARITE_LDAP_USER_SEARCH_BASE={BASE HERE} \
        AUTH_MDC_LDAP_BIND_DN=CN={DN HERE} \
        AUTH_MDC_LDAP_BIND_PASSWORD={PASSWORD HERE} \
        AUTH_MDC_LDAP_SERVER_URI={URI HERE} \
        AUTH_MDC_LDAP_USER_SEARCH_BASE={BASE HERE} \
        DJANGO_ALLOWED_HOSTS=* \
        DJANGO_SECRET_KEY="{CHANGE THIS}" \
        DJANGO_SETTINGS_MODULE=config.settings.production \
        DJANGO_SECURE_SSL_REDIRECT=1
        EMAIL_SENDER="{SENDER ADDRESS HERE}" \
        EMAIL_SUBJECT_PREFIX="[CUBI Omics Data Access]" \
        EMAIL_URL=smtp://postamt.charite.de \
        ENABLED_BACKEND_PLUGINS=timeline_backend \
        PROJECTROLES_SEND_EMAIL={1/0, 0 if testing}


Push project to Flynn:

.. code-block:: shell

    git push {flynn-remote} master

Set up the database:

.. code-block:: shell

    flynn -c {cluster-name} run /app/manage.py migrate


Create superuser:

.. code-block:: shell

    flynn -c {cluster-name} run /app/manage.py createsuperuser

You should now be able to login with the created superuser.

Next, you can proceed to deploy the rest of the environment. See instructions
in the repositories of other services.
