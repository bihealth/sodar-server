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
