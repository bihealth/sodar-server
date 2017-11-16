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
    - Create new base project using the current version of `cookiecutter-django <https://github.com/pydanny/cookiecutter-django>`_
    - Additional unit tests for site apps
    - Changelog in ``CHANGELOG.rst``
- **Filesfolders**
    - Import app from prototype
    - Page title to main files list
    - File, folder and link search (#21)
    - Item flagging (#38)
- **Projectroles**
    - Import app from prototype
    - Sub-navbar with project breadcrumb (#20)
    - Move app and project editing links to project sidebar (#20)
    - Helper functions for project settings
    - Initial project and app object search (#16, #21)
    - More helper functions in Project model: ``get_parents()``, ``get_full_title()``
    - Project list filtering (#32)
    - Project tagging/starring functionality (#37)
- **Timeline**
    - Import app and backend plugin from prototype

Changed
-------

- **General**
    - Update site from Bootstrap 4 Alpha 5 to Beta
    - Update third-party libraries to their latest versions
    - Layout redesign (#20)
    - Switch from PhantomJS to Headless Chrome for UI tests (improved performance and stability, Bootstrap 4 Beta compatibility)
    - Include CSS and JS imports in testing configs and CI
    - General code refactoring and cleanup
    - Update installation instructions in ``INSTALL.rst``
    - Rename "actions" into "operations" (#41)
- **Filesfolders**
    - Redesign data model with inheritance to avoid field repetition
    - Internal app name is now ``filesfolders``
    - Project setting ``allow_public_links`` is now False by default (#43)
- **Projectroles**
    - Remove two-level restriction for project and category nesting in models
    - Only allow creation of categories on top level
    - Improved project list layout
    - Move ``OMICS_CONSTANTS`` from configuration into ``models.py``
    - Populate Role objects in a migration script instead of a fixture
    - Import patched ``django-plugins`` from GitHub instead of including in project directly
    - Include modified fields in project_update timeline event
    - Move Project settings helper functions to ``project_settings.py``
    - Disable help link instead of hiding if no tour help is available
    - Show notice card if no ReadMe is available for project (#42)
    - Refactor URL kwargs
    - Allow users with roles under category children to view category (#47)
    - Update text labels for role management to refer to "members" (#40)
- **Timeline**
    - Enable event details popover on the project details page
    - Limit details page list to successful events
    - Allow guest user to see non-classified events

Fixed
-----

- **Filesfolders**
    - Redirects in exception cases in ``FilePublicLinkView``
    - Unexpected characters in file name broke the ``file_serve`` view (ODA #109)
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
- **Filesfolders**
    - Redundant and deprecated fields/functions from the data model
    - Example project settings
- **Projectroles**
    - Temporary settings variables for demo and UI testing hacks


v0.1 (2017-XX-YY)
=================

Added
-----

- TODO

Changed
-------

- TODO

Fixed
-----

- TODO

Removed
-------

- TODO
