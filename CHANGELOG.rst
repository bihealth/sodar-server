Omics Data Management Changelog
===============================

Changelog for the Omics Data Management Web UI. Loosely follows the
`Keep a Changelog <http://keepachangelog.com/en/0.3.0/>`_
guidelines.


Unreleased
----------

Added
^^^^^

- New base project using the current version of
  `cookiecutter-django<https://github.com/pydanny/cookiecutter-django>`_
- **Projectroles:** Imported app from prototype
- **CHANGELOG.rst:** Added

Changed
^^^^^^^

- **Projectroles:** Removed restrictions for project and category nesting in
  models
- **Projectroles:** Moved ``OMICS_CONSTANTS`` from configuration into
  ``models.py``
- **Projectroles:** Role objects are populated in a migration script instead of
  a fixture
- **Projectroles:** Import patched ``django-plugins`` from GitHub instead of
  including in project directly
- **INSTALL.rst:** Updated installation instructions
- Upgraded site from Bootstrap 4 Alpha to Bootstrap 4 Beta
- Updated several third-party libraries to their latest versions
- General code refactoring and cleanup

Fixed
^^^^^

- **Projectroles:** Fixed check for project title uniqueness

Removed
^^^^^^^

- TODO


v0.1 (2017-XX-YY)
-----------------

Added
^^^^^

- TODO

Changed
^^^^^^^

- TODO

Fixed
^^^^^

- TODO

Removed
^^^^^^^

- TODO
