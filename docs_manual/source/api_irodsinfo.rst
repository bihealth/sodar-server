.. _api_irodsinfo:

Irods Info API
^^^^^^^^^^^^^^

The REST API for the iRODS Info app is described in this document.


API Views
=========

.. currentmodule:: irodsinfo.views_api

.. autoclass:: IrodsEnvRetrieveAPIView


Versioning
==========

For accept header versioning, the following header is expected in the current
SODAR version:

.. code-block:: console

    Accept: application/vnd.bihealth.sodar+json; version=0.14.1
