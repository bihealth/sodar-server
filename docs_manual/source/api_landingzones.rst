.. _api_landingzones:

Landing Zones API
^^^^^^^^^^^^^^^^^

The REST API for landing zone operations is described in this document.


Versioning
==========

Media Type
    ``application/vnd.bihealth.sodar.landingzones+json``
Current Version
    ``1.0``
Accepted Versions
    ``1.0``
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
<<<<<<< HEAD


Versioning
==========

For accept header versioning, the following header is expected in the current
SODAR version:

.. code-block:: console

    Accept: application/vnd.bihealth.sodar+json; version=0.15.1
=======
>>>>>>> update rest api versioning (#1936)
