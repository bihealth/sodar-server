.. _api_landingzones:

Landing Zones API
^^^^^^^^^^^^^^^^^

The REST API for landing zone operations is described in this document.


API Views
=========

.. currentmodule:: landingzones.views_api

.. autoclass:: LandingZoneListAPIView

.. autoclass:: LandingZoneRetrieveAPIView

.. autoclass:: LandingZoneCreateAPIView

.. autoclass:: LandingZoneSubmitDeleteAPIView

.. autoclass:: LandingZoneSubmitMoveAPIView


Versioning
==========

For accept header versioning, the following header is expected in SODAR v0.7.1:

.. code-block:: console

    Accept: application/vnd.bihealth.sodar+json; version=0.7.1
