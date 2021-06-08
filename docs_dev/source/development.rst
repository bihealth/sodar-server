.. _development:

SODAR Development Guidelines
^^^^^^^^^^^^^^^^^^^^^^^^^^^^


Git Branches
============

- ``main``
    - Intended for stable and production quality release code only
    - The ``dev`` branch is merged into ``main`` for freezing releases
- ``dev``
    - The bleeding edge development branch with (mostly) stable new features
    - Only push small urgent updates such as bug fixes here, otherwise fork and
      submit a merge request!
- Temporary development branches
    - Base on ``dev``
    - Please use a consistent naming such as ``feature/x`` and ``fix/y``
    - These will be merged into ``dev`` when finished/stable


Commits
=======

- Please refer to issues by their ids in comments as it makes things easier to
  track.


Python Testing
==============

- For tests utilizing Taskflow or iRODS, please decorate with ``@skipIf``.


Vue App Unit Testing Hints
==========================

- How to test Bootstrap-vue modals
    * Set ``:static="true"`` on modal
    * Use ``async ()`` on test case
    * **After modal.show():** to make sure modal renders, call ``waitNT()`` and
      ``waitRAF()`` from ``utils.js`` (taken from official bootstrap-vue tests)
- Best way to test for ``disabled="disabled"``:
    * True: ``expect(wrapper.find('#id').attributes().disabled).toBe('disabled')``
    * False: ``expect(wrapper.find('#id').attributes().disabled).toBe(undefined)``
    * ``*.props().disabled`` MAY work if target is a vue component with the
      ``disabled`` property.. but not always!
- How to update ``select option``
    * ``await wrapper.find('#id').findAll('option').at(idx).setSelected()``
    * **Note:** Will **not** work with bootstrap-vue select!
- Testing ``@input`` event in bootstrap-vue elements
    * ``wrapper.setData({ vModel: 'value' })``
    * ``wrapper.find('#id').vm.$emit('input')``
- Beware of using ``.not`` in your tests
    * If used on e.g. an attribute of an element, this may return ``true`` even
      ff the element itself does not exist at all!
    * Better to check for the exact value of the attribute/property instead.


App Relationships and Plugins
=============================

For detailed information, see
`SODAR Core documentation <https://sodar-core.readthedocs.io/en/latest/>`_.
docs.

- Apps can freely import and use stuff from the ``projectroles`` app
- Apps should not import code directly from other apps, **except** for the
  following:
    - ``landingzones`` can use ``samplesheets`` models
    - ``samplesheets.configapps.*`` can import things from ``samplesheets``
- For everything else, please use plugins to avoid hardcoded imports
    - See existing plugins for examples on what you need to implement and how


Plugin Types
============

For detailed information, see
`SODAR Core documentation <https://sodar-core.readthedocs.io/en/latest/>`_.
docs.

- Project app plugin (``projectroles.plugins.ProjectAppPluginPoint``)
    - For apps related to project operations
    - Content always related to a project
    - Will be shown on project sidebar
- Backend plugin (``projectroles.plugins.BackendPluginPoint``)
    - Intended for backend apps used by other apps, mostly without their own
      views
- Site plugin (``projectroles.plugins.SiteAppPluginPoint``)
    - Generic site app *not* tied to a project
- Sample Sheet study/assay app plugins
    - Plugins for configuration-specific sample sheet display includes, either
      on the *study* or *assay* level
- Landing Zone config app plugins
    - Plugins for zone configuration specific functionality
