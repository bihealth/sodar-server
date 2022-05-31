.. _admin_install:

Installation and Deployment
^^^^^^^^^^^^^^^^^^^^^^^^^^^

The `SODAR Docker Compose <https://github.com/bihealth/sodar-docker-compose>`_
environment is the recommended method of installing SODAR, both for trying it
out locally and for deploying in production. This environment will install and
run all required SODAR components as a configurable Docker Compose network.


SODAR Environment
=================

The following SODAR components are included in the SODAR Docker Compose
environment. All these components are required for running the complete feature
set of SODAR. However, it is also possible to run some of these outside of the
Docker Compose network if e.g. you already have a separate iRODS server running.

- Essential SODAR Components
    - ``sodar-web``: The SODAR web server for main program logic and UIs.
    - ``sodar-celeryd-default``: Celery daemon for background jobs.
    - ``sodar-celerybeat``: Celery service for periodic tasks.
    - ``sodar-taskflow``: SODAR transaction engine for iRODS operations.
- Database Servers
    - ``postgres``: PostgreSQL server for SODAR and iRODS databases.
    - ``redis``: In-memory database for Celery jobs and caching.
- iRODS Servers
    - ``irods``: An iRODS iCAT server for file storage.
    - ``davrods``: iRODS WebDAV server for web access and IGV/UCSC integration.
- Networking
    - ``traefik``: Reverse proxy for TLS/SSL routing.
    - ``sssd``: System Security Service Daemon for LDAP/AD authentication.


Quickstart Guide
================

For a guide on how to try out and evaluate SODAR on your Linux workstation, see
the `README file <https://github.com/bihealth/sodar-docker-compose#readme>`_ of
the SODAR Docker Compose repository.


Installation Guide
==================

This section provides more detailed information on setting up SODAR as a Docker
Compose network.

.. _admin_install_prerequisites:

Prerequisites
-------------

Ensure your system matches the following operating system and software
requirements.

- Hardware
    - ~10 GB of disk space for the Docker images
- Operating System
    - A modern Linux distribution that is
      `supported by Docker <https://docs.docker.com/engine/install/#server>`_.
    - Outgoing HTTPS connections to the internet are allowed to download data
      and Docker images.
    - Server ports 80 and 443 are open and free on the host.
- Software
    - `Docker <https://docs.docker.com/get-docker/>`_
    - `Docker Compose <https://docs.docker.com/compose/install/>`_
    - `OpenSSL <https://www.openssl.org/>`_

1. Clone the Repository
-----------------------

Clone the ``sodar-docker-compose`` repository as follows:

.. code-block:: bash

    $ git clone https://github.com/bihealth/sodar-docker-compose.git
    $ cd sodar-docker-compose

Alternatively, fork the repository as a first step so you can track changes that
you make using Git.

2. Initialize Volumes
---------------------

Use the provided ``init.sh`` script to create required directories.

.. code-block:: bash

    $ ./init.sh
    $ ls volumes

The ``volumes`` directory is used for data storage, while the subdirectories
under ``config`` point to directories containing configuration files for images
in the network. Some of the configuration directories already exist in the
repository.

3. Provide Certificate and DH Parameters
----------------------------------------

To enable all SODAR features, TLS/SSL connections over HTTPS connections are
required. SODAR Docker Compose uses `Traefik <https://traefik.io/>`_ as a
reverse proxy for the web-based SODAR services. iRODS must also be able to
access certificate files directly.

For instructions on how to generate certificates with OpenSSL in Ubuntu, see
`here <https://ubuntu.com/server/docs/security-certificates>`_. If using a
different Linux distribution, consult the relevant documentation.

Place your certificates under ``config/traefik/tls/`` as ``server.crt`` and
``server.key``. If you need to use different filenames or path, make sure to
edit the ``.env`` and ensure Traefik, iRODS and Davrods can all access the
files. Make sure to provide the full certificate chain if needed. Self-signed
certificates can be used for evaluation and testing.

.. code-block:: bash

    $ cp yourcert.crt config/traefik/tls/server.crt
    $ cp yourcert.key config/traefik/tls/server.key

iRODS also excepts a ``dhparams.pem`` file for Diffie-Hellman key exchange. You
can generate the file using OpenSSL as demonstrated below.

.. code-block:: bash

    $ openssl dhparam -2 -out config/irods/etc/dhparams.pem 2048

4. Configure the Environment
----------------------------

Copy the included ``env.example`` file into a new file called ``.env`` and
adjust the default settings if needed.

.. code-block:: bash

    $ cp env.example .env

See :ref:`admin_settings` for detailed descriptions of SODAR web server
settings. Note that in the Docker Compose environment, settings specific to the
SODAR web server are prefixed with ``SODAR_*``. This does not include e.g. iRODS
settings commonly used by multiple components.

For more information on the iRODS settings, see the
`iRODS documentation <https://docs.irods.org/master/system_overview/configuration/>`_.

Note that for certain settings to take effect, you need to run the Docker
Compose network with specific override files. For more on these, see the next
section and :ref:`admin_install_advanced_config`.

5. Bring up SODAR
-----------------

After configuring you can bring up the Docker network. The full SODAR system,
with all critical components running as Docker containers, can be run with the
following command:

.. code-block:: bash

    $ ./run.sh

If you have the need to modify the default configuration, you can alternatively
launch the network with the ``docker-compose up`` command with appropriate
parameters:

.. code-block:: bash

    $ docker-compose -f docker-compose.yml \
        -f docker-compose.override.yml.irods \
        -f docker-compose.override.yml.davrods \
        -f docker-compose.override.yml.provided-cert \
        up

As the main entrypoint to the system, this will run the SODAR web server which
listens on ports 80 and 443. Make sure that these ports are open. The console
output will display the status of each image. Once everything has initialized
successfully, you can access the SODAR site in your web browser at
``https://<your-host>/``.

.. note::

    For running the system locally on your workstation, you should still set up
    a fully qualified domain name by editing your ``/etc/hosts`` file, the
    default expected server name being ``https://sodar.local``. This is due to
    all features not working properly if pointing to localhost.

The aforementioned command will not return you to your shell. You can stop the
running servers with ``Ctrl-C``. To run the containers in the background, start
it up with the ``-d`` flag. If running in the background, you can check the
status of your images with ``docker ps``.

The command depicted will run everything in the SODAR system within the Docker
Compose network. If you already run some services outside of the network (e.g.
an existing iRODS server) and want to connect to them instead, omit the related
override(s) and update your ``.env`` file to point to the existing resources
instead. Similarly, you may add or replace overrides for different desired
features. For more information, see :ref:`admin_install_advanced_config`.

6. Create Superuser Account
---------------------------

To gain access to the SODAR web UI, you must first create a superuser account.
The user name should be given as ``admin``, otherwise you will need to edit the
``.env`` file. Open a new terminal tab, enter the following and follow the
prompt:

.. code-block:: bash

    $ docker exec -it sodar-docker-compose_sodar-web_1 \
        python /usr/src/app/manage.py createsuperuser \
        --skip-checks --username admin

7. Use SODAR
------------

Once the superuser has been created, you can navigate to the SODAR web UI at
``https://<your-host>/`` and log in with the superuser credentials you provided.

Typically, the first step when logging to a newly installed SODAR site is to
:ref:`create a top level category <ui_project_update>` under which projects can
be added. If you are not using an external LDAP service, you can also create
additional local users in the :guilabel:`Django Admin`, which is available in
the user dropdown at the top right corner of the UI.

Read further in this section on information regarding
:ref:`administrator user access <admin_user>`,
:ref:`admin user interfaces <admin_ui>` and
:ref:`management commands <admin_commands>`.

8. Updating the Environment
---------------------------

If you need to update the configuration after initial install, make sure you
restart the Docker Compose network after editing the ``.env`` file. If you
are running the network in the foreground, stop it with ``Ctrl-C`` and
restart. If the network is running in the background, enter the following:

.. code-block:: bash

    $ docker-compose down && docker-compose up -d

For updating all the images to their latest version, run the following:

.. code-block:: bash

    $ docker-compose pull

To only update a specific image, you can do the following:

.. code-block:: bash

    $ docker-compose pull IMAGE-NAME
    $ docker-compose up -d --no-deps --build IMAGE-NAME

Whenever updating your SODAR environment, it is strongly recommend to ensure
your ``sodar-docker-compose`` repository is up-to-date with the latest version
with the following command:

.. code-block:: bash

    $ git pull origin main


.. _admin_install_advanced_config:

Advanced Configuration
======================

Further configuration for specific use cases are described in this section.

Docker Compose Overrides
------------------------

The following overrides are available for customizing the environment:

``docker-compose.override.yml.irods``
    iRODS iCAT server run as a Docker image within the network.
``docker-compose.override.yml.davrods``
    Davrods service for WebDAV connections to iRODS. Requires the iRODS iCAT
    server.
``docker-compose.override.yml.sssd``
    SSSD service providing LDAP/AD logins. Includes the iRODS iCAT server. If
    you want to include LDAP/AD logins for iRODS, replace the iRODS override
    with this one.
``docker-compose.override.yml.provided-cert``
    Traefik settings for a provided certificate. If you have another way of
    providing certificates, replace this override with your own. Note that in
    addition to Traefik, iRODS and Davrods will also need access to the
    certificate files.

LDAP Configuration with SSSD
----------------------------

To enable LDAP/AD logins to SODAR, you need to take the following steps.

First, create a ``sssd.conf`` file under ``config/sssd``. You can use the
provided ``sss.conf.example`` file as a base for editing. The LDAP settings
depend on the service used.

Next, edit your ``.env`` file. Set the following values:

- ``IRODS_SSSD_AUTH=1``
- ``SODAR_ENABLE_LDAP=1``
- ``SODAR_AUTH_LDAP_*``: Fill according to your LDAP settings.
- ``SODAR_ENABLE_LDAP_SECONDARY=1``: Optional, if using two LDAP services.
- ``SODAR_AUTH_LDAP2_*``: Optional, if using two LDAP services.

Finally, bring up the Docker Compose environment with the appropriate override
file. Make sure you have ``-f docker-compose.override.yml.sssd`` in your startup
command.


Deploying in Production
=======================

This section details issues specific to deploying SODAR in production.

Production Prerequisites
------------------------

In addition to the :ref:`general prerequisites <admin_install_prerequisites>`,
we recommend the following for a production deployment of SODAR:

**TODO:** Update these

- Recommended Hardware
    - Memory: 64 GB of RAM
    - CPU: 16 cores
    - Disk: 600+ GB of free and **fast** disk space
        - ~10 GB for the Docker images
        - **TODO:** Data estimates for actual projects?

General Remarks
---------------

When running the environment for the first time, it may take time for the system
to start up due to e.g. iRODS installation. If you set up deployment with e.g.
Ansible, it is recommended to add wait conditions and checks for the environment
to be ready before proceeding with further tasks.
