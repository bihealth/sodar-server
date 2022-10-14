.. _api_samplesheets:

Sample Sheets API
^^^^^^^^^^^^^^^^^

The REST API for sample sheet operations is described in this document.


API Views
=========

.. currentmodule:: samplesheets.views_api

.. autoclass:: InvestigationRetrieveAPIView

.. autoclass:: IrodsCollsCreateAPIView

.. autoclass:: SheetImportAPIView

.. autoclass:: SheetISAExportAPIView

.. autoclass:: SampleDataFileExistsAPIView


Versioning
==========

For accept header versioning, the following header is expected in the current
SODAR version:

.. code-block:: console

    Accept: application/vnd.bihealth.sodar+json; version=0.12.0
