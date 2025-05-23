.. _api_samplesheets:

Sample Sheets API
^^^^^^^^^^^^^^^^^

The REST API for sample sheet operations is described in this document.


Versioning
==========

Media Type
    ``application/vnd.bihealth.sodar.samplesheets+json``
Current Version
    ``1.1``
Accepted Versions
    ``1.0``, ``1.1``
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


Version Changes
===============

.. _api_samplesheets_version_1_1:

v1.1
----

- ``IrodsAccessTicketRetrieveAPIView``
    * Add ``allowed_hosts`` field
- ``IrodsAccessTicketCreateAPIView``
    * Add ``allowed_hosts`` field
- ``IrodsAccessTicketUpdateAPIView``
    * Add ``allowed_hosts`` field
- ``ProjectIrodsFileListAPIView``
    * Add ``checksum`` field to return data
    * Add ``page`` parameter for optional pagination
