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
    - Add changelog in ``CHANGELOG.rst``
- **Projectroles**
    - Import app from prototype

Changed
-------

- **General**
    - Update site from Bootstrap 4 Alpha 5 to Beta
    - Update several third-party libraries to their latest versions
    - General code refactoring and cleanup
    - Update installation instructions in ``INSTALL.rst``
- **Projectroles**
    - Remove restrictions for project and category nesting in models
    - Move ``OMICS_CONSTANTS`` from configuration into ``models.py``
    - Populate Role objects in a migration script instead of a fixture
    - Import patched ``django-plugins`` from GitHub instead of including in project directly

Fixed
-----

- **Projectroles**
    - Fix check for project title uniqueness

Removed
-------

- TODO


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
