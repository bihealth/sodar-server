Omics Data Management Development Guidelines
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. warning::
   Under construction!


Git Branches
============

- ``master``
    - Intended for stable and production quality release code only
    - The ``dev`` branch is merged into it for freezing releases
- ``dev``
    - The bleeding edge development branch with (mostly) stable new features
    - This branch is deployed for test use in ``http://omics-beta.bihealth.org``
- Temporary development branches
    - Base on ``dev``
    - Please use a consistent naming such as ``feature/x`` and ``fix/y``
    - These will be merged into ``dev`` when finished/stable

Commits
=======

- Please refer to issues by their ids in comments as it makes thins easier to track


Testing
=======

- For tests utilizing Taskflow or iRODS, please decorate with ``@skipIf`` (see examples in e.g. tests)


App Relationships and Plugins
=============================

- Apps can freely import and use stuff from the ``projectroles`` app
- Apps should not import code directly from other apps, **except** for the following:
    - ``landingzones`` can use ``samplesheets`` models
    - ``samplesheets.configapps.*`` can import things from ``samplesheets``
- For everything else, please use plugins to avoid hardcoded imports
    - See existing plugins for examples on what you need to implement and how


Plugin Types
============

- Project app plugin (``projectroles.plugins.ProjectAppPluginPoint``)
    - For apps related to project operations
    - Content always related to a project
    - Will be shown on project sidebar
- Backend plugin (``projectroles.plugins.BackendPluginPoint``)
    - Intended for backend apps used by other apps, mostly without their own views
- Site plugin (``projectroles.plugins.SiteAppPluginPoint``)
    - Generic site app *not* tied to a project
- Samplesheet config app plugins (``samplesheets.plugins.SampleSheetConfigPluginPoint``)
    - Plugins for configuration-specific sample sheet display includes
