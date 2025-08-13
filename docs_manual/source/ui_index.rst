.. _ui_index:

User Interface Overview
^^^^^^^^^^^^^^^^^^^^^^^

This section describes the SODAR user interface (UI).

Great care has been taken to make the usage of SODAR as intuitive and
self-explaining as possible and to make features *discoverable*. That is, if we
(the SODAR authors) were successful then you should be able to find most SODAR
features by following visual cues. You should also be able to understand the
majority of the system without reading long manual text.

However, scientific data management comes with intrinsic complexity and SODAR
does not attempt to hide this from you. This manual tries to list the major
features, thus help with discoverability, and also explain these features in a
sufficient manner.

.. note::

    Supported web browsers for the SODAR UI are the latest versions of
    `Mozilla Firefox <https://www.mozilla.org/en-US/firefox/new/>`_ and
    `Google Chrome <https://www.google.com/chrome/>`_. Other modern browsers may
    work with the site, but are not supported by the authors. Javascript must be
    enabled for full UI functionality.

.. warning::

    The SODAR UI will **not** function correctly on Microsoft Internet Explorer
    or other legacy browsers!

The following screenshot displays the *home view*, which appears after logging
in from the :ref:`login view <ui_login>`.

.. figure:: _static/sodar_ui/home.png
    :align: center
    :scale: 60%

    SODAR home view

In this view you can see the following UI components:

SODAR Site Title
    Click this to return to the home view.
Search
    Search in SODAR projects and data. Start the search by pressing :kbd:`Enter`
    or clicking :guilabel:`Search`. You need to enter at least three characters.
    Left to the search box is a button to access advanced search, in which you
    can enter multiple search terms at once.
Manual
    Access this manual.
Help
    Terse inline help that describes the components currently visible in the UI.
    This may not be enabled for all views.
User Icon
    Click this to open the :ref:`user dropdown <ui_user_dropdown>`.
Home
    Click this to return to this home view.
Available Projects
    A paginated list of categories and projects to which you have access. The
    list columns contain shortcuts for creating or accessing landing zones,
    browsing the project's sample data via WebDAV, and viewing or importing
    sample sheets into a project.
Starred Button
    Filter projects to those that you have favourited by clicking on the star
    icon in the project views. The starred status toggle will be remembered the
    next time you navigate to this view.
Page Dropdown
    Choose how many categories and projects are displayed on each page of the
    list. This value will be saved for subsequent visits to the site. Pagination
    controls will appear on the bottom of the list.
Filter
    Filter projects and categories to those containing a search string.
