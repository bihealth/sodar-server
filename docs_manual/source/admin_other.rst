.. _admin_other:

Other Admin Functionality
^^^^^^^^^^^^^^^^^^^^^^^^^

Additional functionality available to the administrators is detailed in this
section.


User Account Deactivation
=========================

From v1.1 onwards, SODAR supports user account deactivation in site
functionality. Deactivated users can no longer log on to the site or access the
REST API. They will no longer be visible for selection for category or project
members. Furthermore, inactive users will not receive any further email
notifications or app alerts.

Currently there is no separate UI or REST API endpoint for deactivating users.
Administrators have the following options for deactivating a user:

- Navigate into the Django admin and uncheck the :guilabel:`active` field for
  the desired user.
- Open the Django shell to similarly set the ``is_active`` field of the ``User``
  object.
- Use the ``removeroles`` :ref:`management command <admin_commands>` to remove
  the user's roles and optionally deactivate their account.

.. note::

    Project access is not automatically altered by user deactivation. User
    access must either be manually revoked, or automatically removed for all
    projects using the ``removeroles`` management command.

.. note::

    Similar to project access, user iRODS access is not currently automatically
    disabled by user deactivation.


.. _admin_other_hash_scheme:

iRODS Checksum Hashing Support
==============================

From v1.1 onwards, SODAR adds support for SHA256 checksums in addition to the
default MD5 hashing scheme.

The expected hashing scheme can be set by altering the ``IRODS_HASH_SCHEME``
environment variable in SODAR Server and SODAR Docker Compose. If editing iRODS
variables directly, this setting is accessible under ``default_hash_scheme`` on
the iRODS server and ``irods_default_hash_scheme`` in the client configuration.
Make sure to also update your iRODS client environments in SODAR if you are
altering default values.

One hashing scheme is supported at a time. If MD5 is selected, checksums are
expected to be provided as ``.md5`` files accompanying each uploaded file. If
SHA256 is used, the expected file name suffix is ``.sha256``. The format
checksums are provided needs to be standard hexadecimal output. For SHA256,
iRODS internally stores checksums with base64 encoding. SODAR handles encoding
and decoding checksums automatically for landing zone operations.

.. note::

    The hashing scheme is expected to be set **once when initially deployed**
    and not altered on an already deployed SODAR/iRODS environment. If you wish
    to switch to another hashing scheme on an already running server
    environment, you'll need to recompute checksums, update server and client
    settings and preferably replace checksum files accompanying uploads.
