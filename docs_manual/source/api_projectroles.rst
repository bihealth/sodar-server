.. _api_projectroles:

Project Management APIs
^^^^^^^^^^^^^^^^^^^^^^^

The REST APIs for project access and management operations is described in this
document. These APIs are provided by the SODAR Core package. Thus, detailed
documentation can be found in the
`SODAR Core documentation <https://sodar-core.readthedocs.io/en/latest>`_.


Projectroles API
================

This API handles the management of projects, project members and app settings.

Versioning
----------

Media Type
    ``application/vnd.bihealth.sodar-core.projectroles+json``
Current Version
    ``2.0``
Accepted Versions
    ``1.0``, ``1.1``, ``2.0``
Header Example
    ``Accept: application/vnd.bihealth.sodar-core.projectroles+json; version=2.0``

API Views
---------

The projectoles API is provided by the SODAR Core package. Documentation for the
API views can be found in the
`Projectroles REST API documentation <https://sodar-core.readthedocs.io/en/latest/app_projectroles_api_rest.html>`_.


Timeline API
============

This API can be used to query events in the
:ref:`timeline <ui_project_timeline>` audit trail logs.

Versioning
----------

Media Type
    ``application/vnd.bihealth.sodar-core.timeline+json``
Current Version
    ``2.0``
Accepted Versions
    ``2.0``
Header Example
    ``Accept: application/vnd.bihealth.sodar-core.timeline+json; version=2.0``

API Views
---------

The timeline API is provided by the SODAR Core package. Documentation for the
API views can be found in the
`Timeline REST API documentation <https://sodar-core.readthedocs.io/en/latest/app_timeline_api_rest.html>`_.
