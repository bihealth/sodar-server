.. _ui_project_update:

Project Creation and Update
^^^^^^^^^^^^^^^^^^^^^^^^^^^

The project creation and update view allows you to create a project or category,
or update existing project metadata and settings.

For creating new categories or projects, you must have the role of either owner,
delegate or contributor in the parent category. For updating an existing
project, the role of owner or delegate is required.

.. figure:: _static/sodar_ui/project_update.png
    :align: center
    :scale: 50%

    Project creation and update view


Project Metadata
================

The following project metadata and settings are available for updating:

Title
    Update the project title.
Parent
    Move the project to another category. Options only contain categories for
    which you have sufficient access.
Description
    Set an optional longer description of the project.
ReadMe
    Set an optional ReadMe document with for the project. MarkDown notation can
    be used.
Public Guest Access
    Enable public guest access to the project for anyone using SODAR. This
    should be used with caution and is generally intended for demonstration
    projects. If your SODAR server allows anonymous users, this will grant guest
    access to anyone browsing the site.
Notify Members of Landing Zone Uploads
    Send project members email updates for file uploads using landing zones. For
    more information, see the
    :ref:`Landing Zones app documentation <app_landingzones>`.
Allow Sample Sheet Editing
    Enable or disable editability of sample sheets in the project.
Enable Sheet Synchronization
    Enable sample sheet synchronization. For more information, see
    :ref:`app_samplesheets_sync`.
URL for Sheet Synchronization
    REST API URL of remote project for sample sheet synchronization.
Token for Sheet Synchronization
    Token string for sample sheet synchronization.
IP Restrict
    Restrict project access to specific IP addresses if this is set.
IP Allow List
    List of accepted IP addresses for the IP Restrict setting.

When creating a new project, the following fields are included:

Type
    Project type. This can either be *Project* or *Category*. The type can not
    be altered after the project has been created.
Owner
    The user who will be set as project owner. After creation, the role can be
    reassigned in the Members view.

.. note::

    After modifying any fields, make sure to click the :guilabel:`Update` button
    to apply the changes.


Project Archiving
=================

From the :guilabel:`Archive` button in the top right corner of the view, it is
possible to archive or unarchive a project. This will set the project data into
a read-only mode for all users, including owners and delegates. The

- Sample sheets can no longer be edited.
- Restoring of sample sheet versions is disabled.
- No iRODS requests for deleting sample data from iRODS can be added.
- No new data from landing zones can be uploaded into the sample data
  repository.

Some editing functionality will remain active when a project is archived:

- Project metadata such as readme and description can still be modified.
- iRODS access tickets for sample sheets can be modified.
- Sample sheet cache can be updated.
- Existing landing zones can be accessed and deleted.
- User membership can be altered, but only read-only access is granted while the
  project is archived.

Unarchiving the project will restore write access to data according to current
member roles.
:guilabel:`Unarchive`.

.. note::

    Archiving categories is not currently supported.
