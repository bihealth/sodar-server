.. _admin_site_app_settings:

Site App Settings Application
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This application enables changing site-wide app settings which affect the entire
site. These settings are not project or user specific.

.. figure:: _static/admin/site_app_settings.png
    :align: center
    :scale: 55%

    Site App Settings view

Currently available settings:

Landing zone access cleanup
    Enable experimental cleanup feature for landing zone access on zone move, in
    case of e.g admin ACL modifications. Disable if encountering performance
    issues or other zone moving problems. This is a temporary setting subject
    for removal in v1.2.
Site read-only mode
    This sets the entire site into a read-only mode. No data including project
    metadata, sample sheets or landing zones can be modified, except by
    superusers. Previously started landing zone jobs will be allowed to finish.
    The users will receive a UI notification about the enabling and disabling of
    the read-only mode.
