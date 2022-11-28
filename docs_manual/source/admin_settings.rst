.. _admin_settings:

SODAR Settings
^^^^^^^^^^^^^^

SODAR contains a number of site-wide backend settings, which greatly affect the
provided features and user experience. The settings are provided to the server
as environment variables and they originate both from the
`SODAR Core <https://github.com/bihealth/sodar-core>`_ platform and SODAR
itself. Settings can be either mandatory or optional. Default values for all
mandatory settings are provided by the
`SODAR Docker Compose <https://github.com/bihealth/sodar-docker-compose>`_
deployment framework.

.. hint::

    To easily see what values for SODAR site settings are currently in use,
    navigate to the
    `Site Info <https://sodar-core.readthedocs.io/en/latest/app_siteinfo.html#usage>`_
    admin application and select the :guilabel:`Settings` tab.

.. note::

    In ``sodar-docker-compose`` environments, internal SODAR settings may be
    prefixed as ``SODAR_*``.


SODAR Core Settings
===================

Settings originating from SODAR Core are documented in the
`SODAR Core documentation <https://sodar-core.readthedocs.io/en/latest/>`_.
Documentation on settings is linked below.

- `Projectroles (the core project and site framework) <https://sodar-core.readthedocs.io/en/latest/app_projectroles_settings.html#general-site-settings>`_
- `Admin Alerts <https://sodar-core.readthedocs.io/en/latest/app_adminalerts.html#optional-settings>`_
- `App Alerts <https://sodar-core.readthedocs.io/en/latest/app_appalerts.html#django-settings>`_
- `Taskflow Backend <https://sodar-core.readthedocs.io/en/latest/app_taskflow.html#django-settings>`_
- `Timeline <https://sodar-core.readthedocs.io/en/latest/app_timeline_install.html#optional-settings>`_

Enabled Backend Plugins
-----------------------

The ``ENABLED_BACKEND_PLUGINS`` settings defines which backend applications are
used in SODAR. These originate both SODAR Core and SODAR itself. The default
configuration for running SODAR in production is a list of applications as
follows:

``appalerts_backend``
    Creation and management of :ref:`user alerts <ui_alerts>`.
``omics_irods``
    iRODS backend for iRODS connections.
``ontologyaccess_backend``
    Provide ontology lookup for the :ref:`Sample Sheets <app_samplesheets>` app.
``sodar_cache``
    Enable the
    `SODAR Cache <https://sodar-core.readthedocs.io/en/latest/app_sodarcache_usage.html>`_.
``taskflow``
    Provide complex iRODS transactions for project data.
``timeline_backend``
    Creation events for the :ref:`project timeline <ui_project_timeline>`.

It is not recommended to modify this configuration except for special
circumstances. If removed from the list, the functionality regarding a specific
backend will be disabled in SODAR.


SODAR Settings
==============

Settings from SODAR applications themselves are described below.

iRODS Settings
--------------

``ENABLE_IRODS``
    Use iRODS except if set false (boolean).
``IRODS_HOST``
    iRODS host (string).
``IRODS_HOST_FQDN``
    Fully qualified domain name of iRODS host, for cases where ``IRODS_HOST`` is
    given as e.g. an internal docker network host (string).
``IRODS_PORT``
    iRODS port (integer).
``IRODS_ZONE``
    iRODS zone (string).
``IRODS_ROOT_PATH``
    iRODS root path, if something else than ``/{IRODS_ZONE}/`` (string).
``IRODS_USER``
    Name of iRODS admin user to be used by backend processes (string).
``IRODS_PASS``
    Password of iRODS admin user (string).
``IRODS_SAMPLE_COLL``
    Name of sample data collection under each project (string,
    default: ``sample_data``).
``IRODS_LANDING_ZONE_COLL``
    Name of landing zone collection under each project (string,
    default: ``landing_zones``).
``IRODS_ENV_DEFAULT``
    Default iRODS environment for backend and client connections (dict).
``IRODS_ENV_BACKEND``
    iRODS environment overrides for backend connections (dict).
``IRODS_ENV_CLIENT``
    iRODS environment overrides for client connections (dict).
``IRODS_CERT_PATH``
    iRODS certificate path on server (string).
``IRODS_SODAR_AUTH``
    Enable local basic auth endpoint for iRODS if an external LDAP/AD server is
    not used (boolean, default: ``False``).

Taskflow Backend Settings
-------------------------

``TASKFLOW_LOCK_RETRY_COUNT``
    Retry count for project lock retrieval for Taskflow operations (int,
    default: 2)
``TASKFLOW_LOCK_RETRY_INTERVAL``
    Retry interval for project lock retrieval for Taskflow operations (int,
    default: 3)

iRODS WebDAV Settings
---------------------

``IRODS_WEBDAV_ENABLED``
    Enable WebDAV unless set false (boolean).
``IRODS_WEBDAV_URL``
    URL for the iRODS WebDAV server (string).
``IRODS_WEBDAV_URL_ANON``
    URL for anonymous WebDAV access, in case running on a different server than
    the general WebDAV (string, default: ``IRODS_WEBDAV_URL``).
``IRODS_WEBDAV_URL_ANON_TMPL``
    Template for anonymous ticket access via the anonymous WebDAV URL (regex).
``IRODS_WEBDAV_USER_ANON``
    User name for anonymous WebDAV access (string, default: ``ticket``).
``IRODS_WEBDAV_IGV_PROXY``
    Enable the use of IGV proxy on the WebDAV server. This should be set
    ``True`` if the WebDAV is deployed on a different host than SODAR itself.
    This will avoid having to log in twice when opening a session file in IGV.
    If SODAR and the WebDAV are deployed on the same host, this should be set
    ``False`` (boolean, default: ``True``).

iRODS Backend Settings
----------------------

``IRODSBACKEND_STATUS_INTERVAL``
    iRODS backend status query interval in seconds (integer).
``IRODS_QUERY_BATCH_SIZE``
    Batch query size for improving sequential iRODS query performance (integer).

Sample Sheets Settings
----------------------

``SHEETS_ALLOW_CRITICAL``
    Allow critical altamISA warnings on import (boolean).
``SHEETS_IRODS_LIMIT``
    iRODS file query limit (integer).
``SHEETS_TABLE_HEIGHT``
    Default study/assay table height.
``SHEETS_MIN_COLUMN_WIDTH``
    Minimum default column width in study/assay tables (integer).
``SHEETS_MAX_COLUMN_WIDTH``
    Maximum default column width in study/assay tables (integer).
``SHEETS_VERSION_PAGINATION``
    Version list pagination limit (integer).
``SHEETS_IRODS_TICKET_PAGINATION``
    iRODS ticket list pagination limit (integer).
``SHEETS_IRODS_TICKET_PAGINATION``
    iRODS deletion request list pagination limit (integer).
``SHEETS_ONTOLOGY_URL_TEMPLATE``
    URL template for ontology lookup (string).
``SHEETS_ONTOLOGY_URL_SKIP``
    Skip URL template modification if substring is found in the ``accession``
    attribute (list).
``SHEETS_EXTERNAL_LINK_PATH``
    Path for JSON file containing labels and other metadata for external link
    columns (dict, default={PROJECT_ROOT}/samplesheets/config/ext_links.json).
    Each item the JSON dictionary should contain an ID descriptor such as
    ``x-generic-remote`` as its key. The item should contain a ``label``
    parameter containing a display-friendly description of the ID. If linking
    out to an external resource is needed, add a ``url`` parameter containing a
    URL pattern in form of ``https://example.com/{id}``.
``SHEETS_SYNC_INTERVAL``
    Interval for remote sheet synchronization in minutes (integer).

Landing Zones Settings
----------------------

``LANDINGZONES_STATUS_INTERVAL``
    Zone status query interval in seconds (integer).
``LANDINGZONES_TRIGGER_ENABLE``
    Enable automated move triggering (boolean).
``LANDINGZONES_TRIGGER_MOVE_INTERVAL``
    Automated move file check interval in seconds (integer).
``LANDINGZONES_TRIGGER_FILE``
    File name for automated move triggering (string,
    default: ``.sodar_validate_and_move``).
``LZ_BIH_PROTEOMICS_SMB_EXPIRY_DAYS``
    BIH proteomics configuration SMB expiry days (integer).
``LZ_BIH_PROTEOMICS_SMB_USER``
    BIH proteomics configuration SMB user (string).
``LZ_BIH_PROTEOMICS_SMB_PASS``
    BIH proteomics configuration SMB password (string).

Ontology Access Settings
------------------------

``ONTOLOGYACCESS_BULK_CREATE``
    Bulk term creation limit for ontology import (integer).
``ONTOLOGYACCESS_QUERY_LIMIT``
    Term query limit (integer).


SODAR Docker Compose Settings
=============================

Settings specific to the
`sodar-docker-compose <https://github.com/bihealth/sodar-docker-compose>`_
repository are described here.

``SODAR_SERVER_VERSION``
    Version of the SODAR server. Should be the latest release tag (e.g.
    ``0.12.0-0``) or the latest development version ``dev-0``. For production it
    is strongly recommended to use the latest tagged release.
``IRODS_VERSION``
    Version of the CUBI
    `irods-docker <https://github.com/bihealth/irods-docker>`_ image to use.
    Corresponds to the iRODS package version, e.g. ``4.2.11-1``.
``SSSD_VERSION``
    SSSD version if using LDAP logins.
``IRODS_SSSD_AUTH``
    Enable SSSD-based logins for iRODS.
``IRODS_SODAR_AUTH``
    Enable PAM logins via the SODAR server for iRODS.
``IRODS_SODAR_API_HOST``
    SODAR server host for iRODS in case the previous setting is set true.
