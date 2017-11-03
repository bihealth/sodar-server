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
    - Add changelog in ``CHANGELOG.rst``
- **Filesfolders**
    - Import app from prototype
    - Add page title to main files list
- **Projectroles**
    - Import app from prototype
    - Add sub-navbar with project breadcrumb (issue #20)
    - Move app and project editing links to project sidebar (issue #20)
    - Add ``get_app_plugin()`` helper function
    - Add ``validate_project_setting()`` helper function
    - Add ``get_project_setting()`` helper function
    - Add ``set_project_setting()`` helper function
    - Initial project search by title (issue #16)
    - Add ``ProjectManager`` in models for project search (issue #16)
    - More helper functions in Project model: ``get_parents()``, ``get_full_title()``
- **Timeline**
    - Import app and backend plugin from prototype

Changed
-------

- **General**
    - Update site from Bootstrap 4 Alpha 5 to Beta
    - Update third-party libraries to their latest versions
    - Layout redesign (issue #20)
    - Switch from PhantomJS to Headless Chrome for UI tests (improved performance and stability, Bootstrap 4 Beta compatibility)
    - Include CSS and JS imports in testing configs and CI
    - General code refactoring and cleanup
    - Update installation instructions in ``INSTALL.rst``
- **Filesfolders**
    - Redesign data model with inheritance to avoid field repetition
    - Internal app name is now ``filesfolders``
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
    - Refactor URL kwargs
- **Timeline**
    - Enable event details popover on the project details page
    - Limit details page list to successful events
    - Allow guest user to see non-classified events

Fixed
-----

- **Filesfolders**
    - Redirects in exception cases in ``FilePublicLinkView``
- **Projectroles**
    - Check for project title uniqueness
    - Don't allow matching titles for subproject and parent
    - App plugin element IDs in templates
    - Project context for role invite revocation page
    - Project type correctly displayed for user (issue #27)
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
