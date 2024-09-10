.. _api_samplesheets:

Sample Sheets API
^^^^^^^^^^^^^^^^^

The REST API for sample sheet operations is described in this document.


Versioning
==========

Media Type
    ``application/vnd.bihealth.sodar.samplesheets+json``
Current Version
    ``1.0``
Accepted Versions
    ``1.0``
Header Example
    ``Accept: application/vnd.bihealth.sodar.samplesheets+json; version=x.y``


API Views
=========

.. currentmodule:: samplesheets.views_api

Sample Sheet Management
-----------------------

.. autoclass:: InvestigationRetrieveAPIView

.. autoclass:: SheetImportAPIView

.. autoclass:: SheetISAExportAPIView

iRODS Data Objects and Collections
----------------------------------

.. autoclass:: IrodsCollsCreateAPIView

.. autoclass:: SampleDataFileExistsAPIView

.. autoclass:: ProjectIrodsFileListAPIView

iRODS Access Tickets
--------------------

.. autoclass:: IrodsAccessTicketRetrieveAPIView

.. autoclass:: IrodsAccessTicketListAPIView

.. autoclass:: IrodsAccessTicketCreateAPIView

.. autoclass:: IrodsAccessTicketUpdateAPIView

.. autoclass:: IrodsAccessTicketDestroyAPIView

iRODS Data Requests
-------------------

.. autoclass:: IrodsDataRequestRetrieveAPIView

.. autoclass:: IrodsDataRequestListAPIView

.. autoclass:: IrodsDataRequestCreateAPIView

.. autoclass:: IrodsDataRequestUpdateAPIView

.. autoclass:: IrodsDataRequestDestroyAPIView

.. autoclass:: IrodsDataRequestAcceptAPIView

.. autoclass:: IrodsDataRequestRejectAPIView
<<<<<<< HEAD


Versioning
==========

For accept header versioning, the following header is expected in the current
SODAR version:

.. code-block:: console

    Accept: application/vnd.bihealth.sodar+json; version=0.15.1
=======
>>>>>>> update rest api versioning (#1936)
