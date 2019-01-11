.. _installation:

Installation
^^^^^^^^^^^^

.. warning::

   Under construction!

This document describes how to install the system for local development.

**NOTE:** When viewing this document in GitLab critical content will by default
be missing. Please click "display source" if you want to read this in GitLab.

If you want to install or develop SODAR without iRODS and SODAR Taskflow, you
can skip the steps related to their installation and set the environment
variable ``ENABLED_BACKEND_PLUGINS='timeline_backend'``.

These instructions assume you have Python 3.6+ and PostgreSQL 9.4+ installed.

**NOTE:** Python 3.5.x and lower are no longer supported!


Install SODAR
=============

Requirements
------------

- Ubuntu 16.04 Xenial
- Python 3.6+
- Postgres 9.6+

System Installation
-------------------

First you need to install OS dependencies, PostgreSQL 9.6 and Python3.6.

.. code-block:: console

    $ sudo utility/install_os_dependencies.sh
    $ sudo utility/install_python.sh
    $ sudo utility/install_postgres.sh

Database Setup
--------------

Create a PostgreSQL user and a database for your application. In the example,
we use ``sodar`` for the database, user name and password. Make sure to
give the user the permission to create further PostgreSQL databases (used for
testing).

.. code-block:: console

    $ sudo su - postgres
    $ psql
    $ CREATE DATABASE sodar;
    $ CREATE USER sodar WITH PASSWORD 'sodar';
    $ GRANT ALL PRIVILEGES ON DATABASE sodar to sodar;
    $ ALTER USER sodar CREATEDB;
    $ \q

You have to add the credentials in the environment variable ``DATABASE_URL``.
For development it is recommended to place this variable in an ``.env`` file and
set ``DJANGO_READ_DOT_ENV_FILE=1`` in your actual environment. See
``config/settings/base.py`` for more information.

.. code-block:: console

    $ export DATABASE_URL='postgres://sodar:sodar@127.0.0.1/sodar'

Project Setup
-------------

Clone the repository, setup and activate the virtual environment. Once in
the environment, install Python requirements for the project:

.. code-block:: console

    $ git clone git@cubi-gitlab.bihealth.org:CUBI_Engineering/CUBI_Data_Mgmt/sodar.git
    $ cd sodar
    $ pip install virtualenv
    $ virtualenv -p python3.6 .venv
    $ source .venv/bin/activate
    $ utility/install_python_dependencies.sh

LDAP Setup (Optional)
---------------------

If you will be using LDAP/AD auth on your site, make sure to also run:

.. code-block:: console

    $ sudo utility/install_ldap_dependencies.sh
    $ pip install -r requirements/ldap.txt

Final Setup
-----------

Initialize the database (this will also synchronize django-plugins):

.. code-block:: console

    $ ./manage.py migrate

Create a Django superuser for the SODAR site:

.. code-block:: console

    $ ./manage.py createsuperuser


Set Up the Development Environment
==================================

To use iRODS and SODAR Taskflow in development, you need to have
`sodar_taskflow <https://cubi-gitlab.bihealth.org/CUBI_Engineering/CUBI_Data_Mgmt/sodar_taskflow>`_
installed and running. As prerequisites, the project requires a Redis server
plus two iRODS iCAT servers (one for a throwavay test server) running and
configured for SODAR projects.

Prerequisites / Docker Environment
----------------------------------

The easiest way to get the dependencies up is to clone and run the SODAR docker
environment in
`sodar_docker_env <https://cubi-gitlab.bihealth.org/CUBI_Engineering/CUBI_Data_Mgmt/sodar_docker_env>`_.
As a downside, the environment does not currently provide permanent storage for
the default iRODS server.

If you want to set up an iRODS server manually, it must be configured with the
`omics.re <https://cubi-gitlab.bihealth.org/CUBI_Operations/Ansible_Playbooks/blob/master/roles/cubi.irods-setup/files/etc/irods/omics.re>`_
rule set file and MD5 set as the default hash scheme in ``server_config.json``.
In the Docker environment setup CUBI Ansible playbooks these settings are
already pre-configured.

SODAR Taskflow
--------------

For development it is recommend to run sodar_taskflow locally.

First, clone the `sodar_taskflow repository <https://cubi-gitlab.bihealth.org/CUBI_Engineering/CUBI_Data_Mgmt/sodar_taskflow>`_.

Follow the installation instructions in the ``README.rst`` file. Make sure to
configure environment variables to point to the Redis and iRODS servers you are
using.

Configure SODAR
---------------

In the SODAR environment variables (preferably in the ``.env``
file), set up iRODS and Taskflow variables to point to your server. The default
values in ``config/settings/base.py`` point to the sodar_docker_env and
sodar_taskflow defaults. If using the Docker environment and local Taskflow
service, no changes should thus be required.


Run the Components
==================

Make sure Redis and iRODS iCAT server(s) are running. If you have set up and
launched the sodar_docker_env environment, they all should be available as
Docker containers.

Run the Docker environment as follows:

.. code-block:: console

    $ utility/env_relaunch.sh

In the ``sodar_taskflow`` repository, start the SODAR Taskflow service:

.. code-block:: console

    $ utility/run_dev.sh

In the SODAR root directory, start the site in debug mode with ``local``
settings. After this you can access the site at ``http://localhost:8080``.

.. code-block:: console

    $ ./run.sh

If existing data on your development iRODS server has been wiped out due to e.g.
rebooting the Docker environment project metadata and collections (but not data
objects) can be synced with the following command:

.. code-block:: console

    $ ./manage.py synctaskflow

There is also a shortcut for syncing iRODS data and starting the server:

.. code-block:: console

    $ ./run.sh sync

Now you should be able to browse to http://localhost:8000 and see your site.
iRODS and Taskflow actions should also be available.
