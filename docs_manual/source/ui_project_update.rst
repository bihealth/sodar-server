.. _ui_project_update:

Project Update
^^^^^^^^^^^^^^

The project update screen allows you to update project settings.

The role in your project defines whether this button is available to you and
which settings you can update.

.. figure:: _static/sodar_ui/project_update.png

Title
    Update the project's (short) title.
Parent
    Move the project to another category. Options only include categories to
    which you have sufficient access.
Description
    Set an optional longer description of the project.
ReadMe
    Set an optional ReadMe document with MarkDown notation for the project.
Public Guest Access
    Enable public guest access to the project for anyone using SODAR. This
    should be used with caution and is generally intended for demonstration
    projects. If your SODAR server allows anonymous users, this will grant guest
    access to anyone browsing the site.
Allow Sample Sheet Editing
    Enable or disable editability of sample sheets in the project.
Enable Sheet Synchronization
    For cases where a project is displayed e.g. on a demonstration server, this
    and accompanying settings can be used to retrieve the sample sheets from
    another SODAR instance.
IP Restrict
    Restrict project access to specific IP addresses if this is set. Specify
    accepted IPs in the "IP Allow List" setting.

After changing a setting, press :guilabel:`Update` to apply the changes.
