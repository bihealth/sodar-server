.. _ui_user_profile:

User Profile
^^^^^^^^^^^^

The user profile screen displays information regarding your account.

.. figure:: _static/sodar_ui/user_profile.png
    :align: center
    :scale: 65%

    User profile view

Through the user profile, you can modify global user-specific settings for your
account by clicking the :guilabel:`Update Settings` button. The following user
settings are available:

Sample Sheet Table Height
    Choose the maximum height of study and assay tables in the sample sheets app
    from a set of options. In browsing mode, table height will fit the table
    content if the height of content is lower than the setting. In edit mode,
    the chosen table height will be maintained regardless of content.
Display Project UUID Copying Link
    Enabling this will add an icon next to the project title on each project
    view. Clicking it will copy the project identifier (UUID) into the
    clipboard.
Additional Email
    Additional email addresses for the user can be input here. If email sending
    is enabled on the server, notification emails will be sent to these
    addresses in addition to the default user email. Separate multiple addresses
    with the semicolon character (``;``).

If local users are enabled on the site and you have a local SODAR account, the
profile also includes the :guilabel:`Update User` button. This opens a form in
which you can update your details and password. This form is **not** available
for users authenticating with an existing user account via LDAP or SAML.
