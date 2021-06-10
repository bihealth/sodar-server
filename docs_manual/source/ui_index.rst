.. _ui_index:

User Interface
^^^^^^^^^^^^^^

This section describes the SODAR user interface (UI).

Great care has been taken to make the usage of SODAR as intuitive and
self-explaining as possible and to make features *discoverable*. That is, if we
(the SODAR authors) were successful then you should be able to find (most) SODAR
features by following visual cues. You should also be able to understand the
majority of the system without reading long manual text.

However, scientific data management comes with intrinsic complexity and SODAR
does not attempt to hide this from you. This manual tries to list the major
features (and thus help with discoverability) and also explain them in a terse
yet sufficient manner.

The following figure shows the home screen that appears after logging in in the
:ref:`login screen <ui_login>`.

.. figure:: _static/sodar_ui/home.png

You can see the following UI components:

SODAR Label
    Click here to return to the home screen.
Search Box
    Search SODAR data. Start the search by pressing :kbd:`Enter` or clicking
    :guilabel:`Search` to start search (enter at least three characters). Left
    to the search box is a button to access advanced search, in which you can
    enter multiple search terms at once.
Manual
    Go to this manual.
Help
    Terse inline help that describes the components currently visible in the UI.
    This may not be enabled for all views.
User Icon
    Click here to open the :ref:`user dropdown <ui_user_dropdown>`.
    See :ref:`ui_user_dropdown` for more details.
Home
    Click here to return to this home screen.
Available Projects
    Browse all SODAR projects that you have access to.
    There are couple of useful shortcuts, e.g.,

    - adding a landing zone with the plus icon,
    - directly start browsing files through DAVrods, or
    - jump directly to the sample sheets.
Starred Button
    Filter projects to those that you marked with a star.
Filter Box
    Filter projects to those containing a certain search string.

If you have sufficient permissions then you will also see a
:guilabel:`Create Category` or :guilabel:`Create Project or Category`
button on the left-hand side bar under :guilabel:`Home`.

Create Category
    Categories can contain other categories or projects. Thus, they allow to
    build a hierarchical structure of categories and projects. Note that in the
    top / home category, only administrators are allowed to create categories.
Create Project or Category
    Subsequent categories can contain projects. The projects contain the actual
    data and meta data.
