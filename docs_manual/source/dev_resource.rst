.. _dev_resource:

Development Resources
^^^^^^^^^^^^^^^^^^^^^

This section provides general guidelines and resources on SODAR development.


SODAR Core and SODAR
====================

The SODAR Django server is built on the
`SODAR Core <https://github.com/bihealth/sodar-core>`_ framework. To get started
with developing for SODAR, it is strongly recommend to get acquaintanced with
the framework and its `documentation <https://sodar-core.readthedocs.io/>`_.

Specifically, the
`development section <https://sodar-core.readthedocs.io/en/latest/development.html>`_
of the SODAR Core documentation lists guidelines and resources for development.
Unless explicitly stated otherwise, SODAR Core guidelines also apply to SODAR
development. Reading this section is strongly recommended.

For a breakdown on which applications are imported from SODAR Core and which are
native to SODAR, see :ref:`dev_apps`.


Hard-Coded App Imports
======================

Generally, hard-coded imports between apps, with the exception of
``projectroles``, are discouraged due to the dynamic nature of enabling and
disabling SODAR Core apps. In the case of SODAR, direct imports from the
``samplesheets`` app in the ``landingzones`` app are considered acceptable, as
the latter app would not exist without the former. The same is true for the
study and assay sub-apps within ``samplesheets``.


.. _dev_resource_vue_test:

Vue App Unit Testing Hints
==========================

Hints for testing the Sample Sheets Vue.js app can be found below.

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
      if the element itself does not exist at all!
    * Better to check for the exact value of the attribute/property instead.
