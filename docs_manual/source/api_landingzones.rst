.. _api_landingzones:

Landing Zones API
^^^^^^^^^^^^^^^^^

The REST API for landing zone operations is described in this document.


Versioning
==========

Media Type
    ``application/vnd.bihealth.sodar.landingzones+json``
Current Version
    ``1.1``
Accepted Versions
    ``1.0``, ``1.1``
Header Example
    ``Accept: application/vnd.bihealth.sodar.landingzones+json; version=x.y``


API Views
=========

.. currentmodule:: landingzones.views_api

.. autoclass:: ZoneListAPIView

.. autoclass:: ZoneRetrieveAPIView

.. autoclass:: ZoneCreateAPIView

.. autoclass:: ZoneUpdateAPIView

.. autoclass:: ZoneSubmitDeleteAPIView

.. autoclass:: ZoneSubmitMoveAPIView

.. autoclass:: ZoneSettingsRetrieveAPIView

.. autoclass:: ZoneIrodsFileListAPIView


Version Changes
===============

.. _api_landingzones_version_1_1:

v1.1
----

- ``ZoneRetrieveAPIView``
    * Add ``coll_creation`` field
- ``ZoneIrodsFileListAPIView``
    * Add view
- ``ZoneSettingsRetrieveAPIView``
    * Add view
