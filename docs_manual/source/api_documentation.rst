.. _api_documentation:

API Documentation
^^^^^^^^^^^^^^^^^

This document describes the REST API functionality in SODAR. This is intended
for users who want to access and modify data programmatically from e.g. scripts.


Using the API
=============

Usage of the REST API is detailed in this section. Basic knowledge of HTTP APIs
is assumed.

Authentication
--------------

The API supports authentication through Knox authentication tokens as well as
logging in using your SODAR username and password. Tokens are the recommended
method for security purposes.

For token access, first retrieve your token using the :ref:`ui_api_tokens` app
on the SODAR web UI. Note that you can you only see the token once when creating
it.

Add the token in the ``Authorization`` header of your HTTP request as
follows:

.. code-block:: console

    Authorization: token 90c2483172515bc8f6d52fd608e5031db3fcdc06d5a83b24bec1688f39b72bcd

.. _api_documentation_versioning:

Versioning
----------

.. note::

    API versioning has had a major overhaul in SODAR v1.0. Some changes are
    breaking with no backwards compatibility. Please review this part of the
    document carefully and adjust your clients accordingly.

The SODAR REST API uses accept header versioning. While specifying the desired
API version in your HTTP requests is optional, it is **strongly recommended**.
This ensures you will get the appropriate return data and avoid running into
unexpected incompatibility issues.

To enable versioning, add the ``Accept`` header to your request with the
appropriate media type of your API and the expected version. From SODAR v1.0
onwards, both the media type and the version are specific for a SODAR Server or
SODAR Core application, as each provides their independent API which may
introduce new versions independent of other APIs.

Example for the SODAR Server samplesheets API:

.. code-block:: console

    Accept: application/vnd.bihealth.sodar.samplesheets+json; version=1.0

For detailed media types and versioning information of each API, see the
respective application API documentation.

Model Access and Permissions
----------------------------

Objects in SODAR API views are accessed through their ``sodar_uuid`` field.

In the REST API documentation, *"UUID"* refers to the ``sodar_uuid`` field of
each model unless otherwise noted.

For permissions the API uses the same rules which are in effect in the SODAR
GUI. That means you need to have appropriate project access for each operation.

Return Data
-----------

The return data for each request will be a JSON document unless otherwise
specified.

If return data is not specified in the documentation of an API view, it will
return the appropriate HTTP status code along with an optional ``detail`` JSON
field upon a successfully processed request.

Pagination
----------

From SODAR V1.0 onwards, list views support pagination unless otherwise
specified. Pagination can be enabled by providing the ``?page=x`` query string
in the API request. This will change the return data into a paginated format.
Example:

.. code-block:: python

    {
        'count' 170,
        'next': 'api/url?page=3',
        'previous': 'api/url?page=1',
        'results': [
            # ...
        ]
    }
