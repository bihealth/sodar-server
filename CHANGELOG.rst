Omics Data Management Changelog
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Changelog for the Omics Data Management Web UI. Loosely follows the
`Keep a Changelog <http://keepachangelog.com/en/0.3.0/>`_
guidelines.


Unreleased
==========

Added
-----

- **General**
    - Admin link for superuser (#134)
    - Common ``popupWaitHtml`` and ``popupNoFilesHtml`` Javascript variables
    - Clipboard.js for helping clipboard operations
    - CSS styling for ``.omics-code-input``
    - Height check for project sidebar and dropdown menu switching (#156)
- **Irodsbackend**
    - Add irodsbackend app (#139)
    - Add ``get_path()`` for retrieving iRODS paths for Django objects
    - Template tag ``get_irods_path()`` to get object iRODS path in template
    - Add ``get_session()`` for direct iRODS API access
- **Irodsinfo**
    - Add irodsinfo site app (#183)
- **Landingzones**
    - Add landingzones app (#139)
- **Projectroles**
    - Settings updating to Taskflow for project creation and modification (#139)
    - Add ``get_all_settings()`` in ``project_settings``
    - Add ``get_class()`` in ``projectroles_common_tags``
- **Samplesheets**
    - iRODS directory creation (#139)
    - iRODS link and iCommands display (#139)
    - Render optional hidden HTML attributes for cell meta data (#139)
    - Add ``get_dir()`` and ``get_display_name()`` helpers to Study and Assay
    - Add ``SampleSheetTaskflowMixin`` for Taskflow test helpers
    - Row numbers for sample sheet tables (#155)
    - Tour help (#145)
    - Row limit to prevent import and rendering of huge data (#192)
- **Taskflowbackend**
    - Add taskflowbackend app (#139)
    - Add optional ``omics_url`` kwarg to ``submit()``

Changed
-------

- **General**
    - Upgrade to Django 1.11.13
    - Upgrade to django-crispy-forms 1.7.1 (#153)
    - Upgrade to Boostrap 4.1.1 (#144)
    - Improve tour help layout
- **Filesfolders**
    - Don't show empty folder label if subfolders exist (#135)
- **Irodsbackend**
    - Implement functionality of omics_irods_rest directly in the app
    - Rename ``get_object_list()`` into ``get_objects()``
    - Improved error handling in ``get_objects()``
- **Projectroles**
    - Use Taskflowbackend only for creating and modifying ``PROJECT`` type projects
    - Modify Taskflow API URLs
    - Refactor ``get_active_plugins()``
    - Refactor email sending
    - Properly log and report errors in email sending (#151)
    - Require email sending to succeed for creating invites (#149)
    - Modify ProjectStarringAPIView to use common permission mixins
    - Rename ``TestTaskflowViewBase`` to ``TestTaskflowBase``
    - Integrate ``TaskflowMixin`` into ``TestTaskflowBase``
    - Improve project list layout (#171)
    - Move iRODS info page into the irodsinfo app (#183)
    - Modify signature of ``_get_project()`` in ``ProjectAccessMixin``
- **Samplesheets**
    - Rename top header "legend" to "value" (#129)
    - Allow sample sheet upload for project contributor (#137)
    - Allow sample sheet deletion for project contributor (#168)
    - In taskflow operations, use ``omics_uuid`` instead of ``pk`` (#99)
    - Refactor table HTML rendering
    - Improve URLs for ontology linking (#170)
    - Hide columns with no data (#184)
    - Do not allow creating iRODS dirs if rendering fails (#192)
    - Upgraded altamISA to commit ``ddf54e9ab9b47d2b5a7d54ce65ea8aa673375f87`` (#191)
- **Taskflowbackend**
    - Use ``omics_uuid`` instead of ``pk`` (#139)
    - Only set up ``PROJECT`` type projects in ``synctaskflow``

Fixed
-----

- **General**
    - Add missing email settings in production config (#149)
    - Add ``python3-distutils`` to Xenial requirements to fix failing tests caused by recent updates
    - User links visible when logged out on low resolutions (#197)
- **Filesfolders**
    - Broken link for subfolders with depth >1 (#136)
- **Projectroles**
    - Invalid URL in ``build_invite_url()`` caused a crash (#149)
    - Project creation failure using taskflow caused database corruption (#162)
    - Proper redirect from failed project creation to home or parent category
    - Project partially modified instead of rollback if update with taskflow failed (#163)
- **Samplesheets**
    - Delete investigation if import fails (#138)
    - Assay sorting was not defined
    - Assay data could end up in the wrong table with multiple assays under a study (#169)
    - Correctly use ``request.session.real_referer`` for back/cancel links (#175)
    - Error rendering sheet tables caused app to crash (#182)
    - Building a redirect URL in export view caused a crash
    - Prevent double importing of Investigation (#189)
    - Zip file upload failed on Windows browsers (#198)
- **Timeline**
    - Fix event id parameter in Taskflow view

Removed
-------

- **General**
    - Removed Flynn workarounds, deploying on Flynn no longer supported (#133)
- **Projectroles**
    - "View Details" link in details page, not needed thanks to project sidebar
    - ``get_description()`` templatetag


v0.2.0 (2018-04-13)
===================

Added
-----

- **General**
    - Automated version numbering in footer (#130)
    - ``ProjectPermissionMixin`` for project apps
    - ``ProjectAccessMixin`` for retrieving project from UUID URL kwargs
    - The ``omics_uuid`` field in models where it was missing (#97)
    - Graph output with pygraphviz for local development
- **Projectroles**
    - Add ``get_project_link()`` in templatetags
- **Samplesheets**
    - Add samplesheets app
    - ISA specification compatible data model (#76)
    - Importing ISA investigations as sample sheets (#77)
    - Rendering and navigation of sample sheets (#79)
    - Simple sample sheet search (#87)
    - DataTables rendering of sheets (#81)

Changed
-------

- **General**
    - Upgrade site to Django 1.11.11
    - Upgrade site to Boostrap 4.0.0 Stable (#78)
    - Use ``omics_uuid`` instead of ``pk`` in URLs and templates (#97)
    - Rework URL scheme for consistency and compactness (#105)
    - Modify subtitle and page content containers for all apps
    - Sticky subtitle nav menu for pages with operations menus or navigation
    - Site-wide CSS tweaks
    - Rename ``details_position`` to ``plugin_ordering`` in plugins (#90)
    - Refactor app views with redundant ``SingleObjectMixin`` includes (#106)
    - Squashed/recreated database migrations (#120) (Note: site must be deployed on a fresh database in this version)
- **Projectroles**
    - Search view improvements
    - Refactor roles and invites views
    - Split ``get_link_state`` tag into ``get_app_link_state`` and ``get_pr_link_state`` to support new URLs (#105)
- **Timeline**
    - Use ``omics_uuid`` for object lookup in ``plugins.get_object_link()`` (#97)

Fixed
-----

- **General**
    - Update ChromeDriver to eliminate UI test crashes (#85)
    - User dropdown rendering depth (#82)
    - Error template layout breaking (#108)
- **Filesfolders**
    - Public link form widget always disabled when updating a file (#102)
    - Content type correctly returned for uploaded files and folder READMEs (#131)

Removed
-------

- **General**
    - Role "project staff" (#121)


v0.1 (2018-01-26)
=================

Added
-----

- **General**
    - Create new base project using the current version of `cookiecutter-django <https://github.com/pydanny/cookiecutter-django>`_
    - Additional unit tests for site apps
    - Changelog in ``CHANGELOG.rst``
    - User profile page (#29)
    - Highlight help link for new users (#30)
    - Support for multiple LDAP backends (#69)
- **Adminalerts**
    - Add adminalerts app (#17)
- **Filesfolders**
    - Import app from prototype
    - Page title to main files list
    - File, folder and link search (#21)
    - Item flagging (#38)
    - History links for items (#35)
    - Folder readme file rendering (#36)
- **Projectroles**
    - Import app from prototype
    - Sub-navbar with project breadcrumb (#20)
    - Move app and project editing links to project sidebar (#20)
    - Helper functions for project settings
    - Initial project and app object search (#16, #21)
    - More helper functions in Project model: ``get_parents()``, ``get_full_title()``
    - Project list filtering (#32)
    - Project tagging/starring functionality (#37)
    - History links for project members (#35)
    - Import roles from another owned project (#9)
    - User HTML tag in common templatetags (#71)
- **Timeline**
    - Import app and backend plugin from prototype
    - Object event view history and API (#35)
    - Project model support in event references

Changed
-------

- **General**
    - Update site for Django 1.11.9 (#1) and Python 3.6.3 (#2)
    - Update site to Bootstrap 4 Beta 3 (#70)
    - Update third-party libraries to their latest versions
    - Layout redesign (#20)
    - Switch from PhantomJS to Headless Chrome for UI tests (improved performance and stability, Bootstrap 4 Beta compatibility)
    - Include CSS and JS imports in testing configs and CI
    - General code refactoring and cleanup
    - Update installation instructions in ``INSTALL.rst``
    - Rename "actions" into "operations" (#41)
    - Message alert boxes made dismissable (#25)
    - Make tables and navs responsive to browser width
- **Filesfolders**
    - Redesign data model with inheritance to avoid field repetition
    - Internal app name is now ``filesfolders``
    - Project setting ``allow_public_links`` is now False by default (#43)
    - Include extra data in item creation and updating
    - Only allow one readme.* file in each folder (#36)
- **Projectroles**
    - Remove two-level restriction for project and category nesting in models
    - Only allow creation of categories on top level
    - Improved project list layout
    - Move ``OMICS_CONSTANTS`` from configuration into ``models.py``
    - Populate Role objects in a migration script instead of a fixture
    - Import patched ``django-plugins`` from GitHub instead of including in project directly
    - Include extra data in project creation and updating
    - Move Project settings helper functions to ``project_settings.py``
    - Disable help link instead of hiding if no tour help is available
    - Show notice card if no ReadMe is available for project (#42)
    - Refactor URL kwargs
    - Allow users with roles under category children to view category (#47)
    - Update text labels for role management to refer to "members" (#40)
    - Separate common template tags into ``projectroles_common_tags``
    - Move project settings forms to project creation/update view (#44)
    - Provide reload-safe referer URL in ``request.session.real_referer`` (#67)
- **Timeline**
    - Enable event details popover on the project details page
    - Limit details page list to successful events
    - Allow guest user to see non-classified events
    - Function ``add_event()`` raises proper ``ValueError`` exceptions

Fixed
-----

- **Filesfolders**
    - Redirects in exception cases in ``FilePublicLinkView``
    - Unexpected characters in file name broke the ``file_serve`` view (ODA #109)
    - Check for existing file if moving file during update (#56)
- **Projectroles**
    - Check for project title uniqueness
    - Don't allow matching titles for subproject and parent
    - App plugin element IDs in templates
    - Project context for role invite revocation page
    - Project type correctly displayed for user (#27)
- **Timeline**
    - Tour help anchoring for list navigation buttons
    - User column link was missing the ``mailto:`` protocol syntax

Removed
-------

- **General**
    - The unused ``get_info()`` function and its implementations from ``plugins`` (provide ``details_template`` instead)
    - Unused user app features
- **Filesfolders**
    - Redundant and deprecated fields/functions from the data model
    - Example project settings
- **Projectroles**
    - Temporary settings variables for demo and UI testing hacks
