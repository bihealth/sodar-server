.. _admin_user:

Admin Users
^^^^^^^^^^^

The following extra features are available for SODAR administrators:

- Full access to all projects (Note: iRODS access must be separately granted)
- Ability to create categories on the root level
- Additional site-wide administrative applications
- Access to Django admin UI
- SODAR management commands (Note: shell access to SODAR server required)
- SODAR site settings (Note: server deployment access required)

SODAR admin users are expected to have the Django ``superuser`` status. To
create a new superuser, you need to do it either in the SODAR server shell by
Django management commands or in the Django admin web UI.

In the shell, use the following command in the SODAR project root and follow the
prompts for further details:

.. code-block:: console

    ./manage.py createsuperuser

To create an administrator in the UI, enter the Django admin and
`follow these instructions <https://docs.djangoproject.com/en/3.2/topics/auth/default/#id6>`_.
Make sure to set the ``superuser`` status true.

.. note::

    The ``staff`` status is not used in SODAR at this time.

.. warning::

    Administrator accounts wield a high degree of power in the system, including
    the potential for introducing breaking changes into the SODAR database. Care
    should be put in who gets this access. It is recommended to keep the
    passwords for these accounts extra safe and change them regularly.
