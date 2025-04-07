.. _admin_other:

Other Admin Functionality
^^^^^^^^^^^^^^^^^^^^^^^^^

Additional functionality available to the administrators is detailed in this
section.


User Account Deactivation
=========================

From v1.1 onwards, SODAR supports user account deactivation in site
functionality. Deactivated users can no longer log on to the site or access the
REST API. They will no longer be visible for selection for category or project
members. Furthermore, inactive users will not receive any further email
notifications or app alerts.

Currently there is no separate UI or REST API endpoint for deactivating users.
Administrators have the following options for deactivating a user:

- Navigate into the Django admin and uncheck the :guilabel:`active` field for
  the desired user.
- Open the Django shell to similarly set the ``is_active`` field of the ``User``
  object.
- Use the ``removeroles`` :ref:`management command <admin_commands>` to remove
  the user's roles and optionally deactivate their account.

.. note::

    Project access is not automatically altered by user deactivation. User
    access must either be manually revoked, or automatically removed for all
    projects using the ``removeroles`` management command.

.. note::

    Similar to project access, user iRODS access is not currently automatically
    disabled by user deactivation.
