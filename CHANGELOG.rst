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
    - Create new base project using the current version of `cookiecutter-django<https://github.com/pydanny/cookiecutter-django>`_
    - Additional unit tests for site apps
    - Add changelog in ``CHANGELOG.rst``
- **Filesfolders**
    - Import app from prototype
- **Projectroles**
    - Import app from prototype
- **Timeline**
    - Import app and backend plugin from prototype

Changed
-------

- **General**
    - Update site from Bootstrap 4 Alpha 5 to Beta
    - Update third-party libraries to their latest versions
    - Switch from PhantomJS to Headless Chrome for UI tests (improved performance and stability, Bootstrap 4 Beta compatibility)
    - Include CSS and JS imports in testing configs and CI
    - General code refactoring and cleanup
    - Update installation instructions in ``INSTALL.rst``
- **Filesfolders**
    - Redesign data model with inheritance to avoid field repetition
- **Projectroles**
    - Remove restrictions for project and category nesting in models
    - Improved project list layout
    - Move ``OMICS_CONSTANTS`` from configuration into ``models.py``
    - Populate Role objects in a migration script instead of a fixture
    - Import patched ``django-plugins`` from GitHub instead of including in project directly
    - Include modified fields in project_update timeline event
- **Timeline**
    - Enable event details popover on the project details page
    - Limit details page list to successful events
    - Allow guest user to see non-classified events

Fixed
-----

- **Projectroles**
    - Check for project title uniqueness
    - Don't allow matching titles for subproject and parent
- **Timeline**
    - Tour help anchoring for list navigation buttons

Removed
-------

- **Filesfolders**
    - Removed redundant and deprecated fields/functions from the data model
- **Projectroles**
    - Remove temporary settings variables for demo and UI testing hacks


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
