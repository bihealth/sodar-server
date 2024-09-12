.. _api_landingzones:

Landing Zones API
^^^^^^^^^^^^^^^^^

The REST API for landing zone operations is described in this document.


API Views
=========

.. currentmodule:: landingzones.views_api

.. autoclass:: ZoneListAPIView

.. autoclass:: ZoneRetrieveAPIView

.. autoclass:: ZoneCreateAPIView

.. autoclass:: ZoneUpdateAPIView

.. autoclass:: ZoneSubmitDeleteAPIView

.. autoclass:: ZoneSubmitMoveAPIView


Versioning
==========

For accept header versioning, the following header is expected in the current
SODAR version:

.. code-block:: console

    Accept: application/vnd.bihealth.sodar+json; version=0.15.1
