.. _admin_install:

Installation and Deployment
^^^^^^^^^^^^^^^^^^^^^^^^^^^

The `SODAR Docker Compose <https://github.com/bihealth/sodar-docker-compose>`_
environment is the recommended method of installing SODAR, both for trying it
out locally and for deploying in production. This environment can install and
run all required SODAR components as a configurable Docker Compose network.


SODAR Environment
=================

The following SODAR components are included in the ``sodar-docker-compose``
environment. All these components are required for running the complete feature
set of SODAR. However, it is also possible to run some of these outside of the
Docker Compose network if e.g. you already have a separate iRODS server running.

- Essential SODAR Components
    - ``sodar-web``: The SODAR Django server for main program logic and UIs.
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


Installation Guide
==================

This section will guide you through setting up and running SODAR using the
SODAR Docker Compose environment.

1. Prerequisites
----------------

Ensure your system matches the following operating system and software
requirements.

- Operating System
    - A modern Linux distribution that is
      `supported by Docker <https://docs.docker.com/engine/install/#server>`_.
    - Outgoing HTTPS connections to the internet are allowed to download data
      and Docker images.
    - Server ports 80 and 443 are open and free on the host.
- Software
    - `Docker <https://docs.docker.com/get-docker/>`_
    - `Docker Compose <https://docs.docker.com/compose/install/>`_

2. Clone the Repository
-----------------------

Clone the ``sodar-docker-compose`` repository as follows:

.. code-block:: bash

    $ git clone https://github.com/bihealth/sodar-docker-compose.git
    $ cd sodar-docker-compose

3. Initialize Volumes
---------------------

Use the provided ``init.sh`` script for creating the required volumes
(directories).

.. code-block:: bash

    $ ./init.sh
    $ ls volumes

**TODO:** Explain these directories

4. Configure the Environment
----------------------------

Copy the included ``env.example`` file into a new file called ``.env`` and
adjust the default settings if needed.

See :ref:`admin_settings` for detailed descriptions of SODAR server settings.
Note that in the Docker Compose environment, settings specific to the server are
prefixed with ``SODAR_*``. This does not include e.g. iRODS settings commonly
used by multiple components.

At this point you should also add your TLS/SSL certificates to enable HTTPS
connections. Place your certificates under ``config/traefik/tls/server.crt`` and
``server.key``. If trying out SODAR on a non-production environment, you can
e.g. generate a self-signed certificate.

**TODO**: iRODS configuration (separate subsection?)

5. Bring up SODAR
-----------------

After configuring you can bring up the Docker environment.

The most basic SODAR setup can be run with the following command:

.. code-block:: bash

    $ docker-compose up

This will run the SODAR site which will listen on ports 80 and 443. Make sure
that these ports are open. The console output will display the status of each
image. Once everything has initialized correctly, you can access the SODAR site
in your web browser at ``https://127.0.0.1/`` or ``https://<your-host>/``.

The aforementioned command will not return you to your shell. You can stop the
running servers with ``Ctrl-C``.

You can also use let Docker Compose run the containers in the background:

.. code-block:: bash

    $ docker-compose up -d

If you run the environment in the background with the ``-d`` flag, you can use
the following command to ensure the status of the images:

.. code-block:: bash

    $ docker ps

The basic command only runs the SODAR site and its mandatory requirements. The
repository also comes up with several overrides for running additional images in
the Docker Compose network:

``docker-compose.override.yml.irods``
    iRODS iCAT server run as a Docker image within the network.
``docker-compose.override.yml.davrods``
    Davrods service for WebDAV connections to iRODS. Requires iRODS iCAT server.
``docker-compose.override.yml.sssd``
    SSSD service providing LDAP/AD logins. Includes iRODS iCAT server.

Hence, to run the full environment with iRODS and Davrods included, you can use
the following command:

.. code-block:: bash

    $ docker-compose docker-compose -f docker-compose.yml \
        -f docker-compose.override.yml.irods \
        -f docker-compose.override.yml.davrods up

If you want to include LDAP/AD logins for iRODS, replace the iRODS override with
``docker-compose.override.yml.sssd``.

6. Use SODAR
------------

Once the SODAR site and its components are running, you need to create a
superuser to work as your administrator account. Enter the following command and
follow the instructions. As user name, use the value of
``SODAR_PROJECTROLES_ADMIN_OWNER`` in your ``.env`` file (default=``root``).

.. code-block:: bash

    $ docker exec -it sodar-docker-compose_sodar-web_1 \
        python /usr/src/app/manage.py createsuperuser

Once the user has been created, you can navigate to the SODAR site on
``https://127.0.0.1/`` or ``https://<your-host>/`` on your web browser and log
in with the credentials you provided.

You can modify your admin account it in the ``Django Admin``, available from the
user menu on the top right corner of the UI. You can also use the Django
Administration interface to create new user accounts, if you allow local users
or want to create multiple administrators.

The first steps for the administrator on a new SODAR site is usually to
:ref:`create a top level category <ui_project_update>` and invite a non-admin
user into that category. After this that user will be able to create
subcategories and projects without administrator assistance.

Read further in this section on information regarding
:ref:`administrator user access <admin_user>`,
:ref:`admin user interfaces <admin_ui>` and
:ref:`management commands <admin_commands>`.

7. Updating the Environment
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


Deploying in Production
=======================

This section details issues specific to deploying SODAR in production.

Prerequisites
-------------

**TODO:** Update these

- Recommended Hardware
    - Memory: 64 GB of RAM
    - CPU: 16 cores
    - Disk: 600+ GB of free and **fast** disk space
        - **TODO:** Data estimates for actual projects?
        - ~5 GB for the Docker images
- Network
    - Outgoing HTTPS connections to the internet are allowed to download data
      and Docker images
    - Server ports 80 and 443 are open and free on the host that run on this on

TLS/SSL Certificates
--------------------

SODAR Docker Compose uses `Traefik <https://traefik.io/>`_ as a reverse proxy
and must be reconfigured if you want to change the default behaviour of using
self-signed certificates.

``settings:testing``
    By default and as a fallback, Traefik will use self-signed certificates that
    are recreated at every startup. These are probably fine for a test
    environment but you might want to change this to one of the below.
``settings:production-provide-certificate``
  You can provide your own certificates by placing them into
  ``config/traefik/tls/server.crt`` and ``server.key``. Make sure to provide the
  full certificate chain if needed (e.g., for DFN issued certificates).
``settings:production-letsencrypt``
  If your site is reachable from the internet, you can also use
  ``settings:production-letsencrypt`` which will use
  `Letsencrypt <https://letsencrypt.org/>`_ to obtain the certificates.
  NB: if you make your site reachable from the internet then you should be aware
  of the implications. SODAR is MIT licensed software which means that it comes
  "without any warranty of any kind". See the ``LICENSE`` file for details.
