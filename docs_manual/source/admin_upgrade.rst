.. _admin_upgrade:

Upgrade Guide
^^^^^^^^^^^^^

This document contains administrator instructions for upgrading specific
versions of SODAR. It assumes the use of the
`SODAR Docker Compose <https://github.com/bihealth/sodar-docker-compose>`_
environment.


General Upgrades
================

For most SODAR versions, the following procedure for upgrading can be followed:

1. Pull and check out the latest ``sodar-docker-compose`` release corresponding
   to the current SODAR server version.
2. Review and update your environment variables to match and/or support those
   recommended in the `env.example <https://github.com/bihealth/sodar-docker-compose/blob/main/env.example>`_
   file found in the current ``sodar-docker-compose`` release. Especially make
   sure ``SODAR_SERVER_VERSION`` is set to the latest version found in the
   `sodar-server packages <https://github.com/bihealth/sodar-server/pkgs/container/sodar-server>`_
   and that other image versions are as recommended in the example.
3. Pull and build the images.
4. Restart the Docker Compose network.

For SODAR releases where breaking changes require additional actions, release
specific procedures are listed below.

All instructions assume you are running the previous major release of SODAR
before performing the upgrade.


.. _admin_upgrade_v1.0:

v1.0
====

SODAR v1.0 contains breaking changes regarding upgrades to iRODS 4.3 and
PostgreSQL >=12. When upgrading from a previous version, it is recommended to do
a clean install.

This release **requires** at least the following versions of SODAR
environment components:

- `sodar-docker-compose <https://github.com/bihealth/sodar-docker-compose>`_ ``1.0.0-1``
- `irods-docker <https://github.com/bihealth/irods-docker>`_ ``4.3.3-2``
- `davrods-docker <https://github.com/bihealth/davrods-docker>`_ ``4.3.3_1.5.1-1``
- PostgreSQL ``>=12``

.. note::

    This release no longer supports iRODS <=4.2 and PostgreSQL <=11. Your iRODS
    and PostgreSQL servers **must** be updated for this release to work.

.. warning::

    This upgrade may result in loss of data if performed incorrectly. Make sure
    your databases and other relevant files are backed up and follow the
    instructions carefully. If working in a production environment, it is
    recommended to take a snapshot of your host VM before proceeding.

1. If it is running, bring down the Docker Compose network *except* for the
   postgres container.

- If not running, bring up the postgres container by itself.

2. Export and backup your ``sodar`` and ``ICAT`` databases.

- SSH into the postgres container as the ``postgres`` user.
- Example: ``pg_dump -cv DATABASE-NAME > /tmp/DATABASE-NAME_yyyy-mm-dd.sql``
- Make sure you export both databases.
- Make sure you store the backups outside your Docker containers.
- **OPTIONAL:** If you have made changes to iRODS config not present in the
  ``sodar-docker-compose`` repository, e.g. changing the iRODS rule files,
  also back up your iRODS config files at this point.
- **OPTIONAL:** If you run an evaluation environment with the iRODS vault
  stored in a local volume and accessed directly via ICAT, also consider
  backing up your vault directory.

3. Pull the latest ``v1.0.0-*`` release of ``sodar-docker-compose``.

4. Delete the iRODS configuration directory and PostgreSQL database volume.

- **WARNING:** This will result in loss of data, so make sure you have
  successfully backed up everything before proceeding!
- Example: ``sudo rm -rf config/irods/etc/ volumes/postgres``

5. Update your ``.env`` file (or environment variables in your deployment
   scripts) to be compatible with the ``env.example`` file of the current
   ``sodar-docker-compose`` release.

- **NOTE:** Make sure ``IRODS_PASS`` and ``IRODS_PASSWORD_SALT`` are set with
  the same values as in your previous installation. Otherwise iRODS will fail to
  run after re-importing old databases, as the service user is unable to connect
  to the ICAT server.

6. Run ``./init.sh`` (or the corresponding command in your deployment scripts)
   to recreate directories.

7. Bring up the Docker Compose network.

- If something fails in your SODAR or iRODS install, repeat steps 4-7.

8. Once SODAR and iRODS are successfully set up, bring down the Docker Compose
   network *except* for the postgres container.

9. Replace the ``sodar`` and ``ICAT`` databases in postgres with your database
   exports.

- Example: ``psql DATABASE-NAME < /tmp/DATABASE-NAME_yyyy-mm-dd.sql``

10. Restart the full Docker Compose network.

- ``sodar-web`` will migrate your SODAR database on restart.
- ``irods`` will use the previously backed up database on restart.


.. _admin_upgrade_v0.15:

v0.15
=====

To enable support for custom ISA-Tab templates, make sure to add
``isatemplates_backend`` to ``SODAR_ENABLED_BACKEND_PLUGINS`` in your
environment variables.


.. _admin_upgrade_v0.14:

v0.14
=====

Upon deploying this release on an existing instance, admins must run the
``syncmodifyapi`` management command. This will update project user access in
iRODS according to the role inheritance update introduced in SODAR Core v0.13.
