Installation for Development
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. warning::
   Under construction!

This document describes how to install the system for local development.

NB: the display of this document in Gitlab is incomplete and all listings will be missing.
Please rather click "view source" if you want to read this in Gitlab.

NB: Make sure to use the `dev` branch of all repositories for development.

**NOTE:** If you want to develop without iRODS and Omics Taskflow, you can skip
the steps related to their installation and set the environment variable
``ENABLED_BACKEND_PLUGINS='timeline_backend'``.


Install SODAR
=============

First, create a postgresql users and a database for your application.
For example, ``omics_data_mgmt`` with password ``omics_data_mgmt`` and a database called ``omics_data_mgmt``.
Also, give the user the permission to create further Postgres databases (used for testing).

.. code-block:: shell
    $ sudo adduser --no-create-home omics_data_mgmt
    $ sudo su - postgres
    $ psql
    $ CREATE DATABASE omics_data_mgmt;
    $ CREATE USER omics_data_mgmt WITH PASSWORD 'omics_data_mgmt';
    $ GRANT ALL PRIVILEGES ON DATABASE omics_data_mgmt to omics_data_mgmt;
    $ ALTER USER omics_data_mgmt CREATEDB;
    $ \q

You have to make the credentials in the environment variable ``DATABASE_URL``.
For development it is recommended to place this variable in an ``.env`` file and
set ``DJANGO_READ_DOT_ENV_FILE`` true in your actual environment. See
``config/settings/base.py`` for more information.

.. code-block:: shell
    $ export DATABASE_URL='postgres://omics_data_mgmt:omics_data_mgmt@127.0.0.1/omics_data_mgmt'

Clone the repository and setup the virtual environment inside:

.. code-block:: shell
    $ git clone git@cubi-gitlab.bihealth.org:CUBI_Engineering/CUBI_Data_Mgmt/omics_data_mgmt.git
    $ cd omics_data_mgmt
    $ virtualenv -p python3.6 .venv
    $ source .venv/bin/activate

Install the dependencies:

.. code-block:: shell
    $ sudo utility/install_os_dependencies.sh install
    $ sudo utility/install_chrome.sh
    $ pip install --upgrade pip
    $ utility/install_python_dependencies.sh install

Initialize the database:

.. code-block:: shell
    $ ./manage.py migrate

Create Django superuser, needed to create initial project(s) on the site

.. code-block:: shell
    $ ./manage.py createsuperuser

If you are running the Docker environment then modify ``config/settings/test_local.py`` and add the following line.

.. code-block:: python
    IRODS_PORT = env.int('IRODS_PORT', 4477)


2. Set Up a Development iRODS Server
====================================

To use the iRODS and taskflow functionalities, You need to have an iRODS iCAT
server v4.2+ running and configured for omics projects.

**IMPORTANT:** Do **NOT** develop or run tests on a production server or an iRODS
server used for any other project, as server data **WILL** be wiped between
automated tests! (The ability for defining a separate server for running tests
is TODO)

Options for setting up an iRODS server:

- Install and run a server locally (see `irods.org <https://irods.org/download/>`_ for instructions)
- Run server as a Docker image
- Install on a VM using e.g. Vagrant and the `CUBI Ansible Playbooks <https://cubi-gitlab.bihealth.org/CUBI_Operations/Ansible_Playbooks/>`_

A Docker environment containing a basic iRODS setup: `omics_docker_env <https://cubi-gitlab.bihealth.org/CUBI_Engineering/CUBI_Data_Mgmt/omics_docker_env>`_

The server must be configured with the `omics.re <https://cubi-gitlab.bihealth.org/CUBI_Operations/Ansible_Playbooks/blob/master/roles/cubi.irods-setup/files/etc/irods/omics.re>`_
rule set file and MD5 as the default hash scheme. In the Docker setup and the
Ansible playbooks, this is already pre-configured.

In the SODAR environment variables (preferably in the ``.env``
file), set up iRODS variables to point to your server. See
``config/settings/base.py`` for the variables and their default values.


3. Install and Configure Omics Taskflow
=======================================

For development it is recommend to run omics_taskflow locally.

First, clone the `Omics Taskflow repository <https://cubi-gitlab.bihealth.org/CUBI_Engineering/CUBI_Data_Mgmt/omics_taskflow>`_.

Follow the installation instructions in the ``README.rst`` file. Make sure to
configure environment variables to point to the Redis and iRODS servers you are
using.

The `omics_docker_env <https://cubi-gitlab.bihealth.org/CUBI_Engineering/CUBI_Data_Mgmt/omics_docker_env>`_
environment also contains a Redis server for omics_taskflow use.


4. Run the Components
=====================

Make sure `Redis <https://redis.io/>`_ is running. If you're running it locally
and it is not autostarted, start it manually:

.. code-block:: shell
    $ ./redis-server

In the Omics Taskflow root directory, start the Taskflow service:

.. code-block:: shell
    $ utility/run_dev.sh

In the SODAR root directory, start the site in debug mode with
``local`` settings. After this you can access the site at
``http://localhost:8080``.

.. code-block:: shell
    $ ./run.sh

**NOTE:** If data on your development iRODS server is wiped out due to e.g.
running tests or restarting a Docker instance *after* you have already created
projects, project metadata and directories (but not files) can be synced with
the following command:

.. code-block:: shell
    $ ./manage.py synctaskflow

There is also a shortcut for syncing iRODS data and starting the server:

.. code-block:: shell
    $ ./run.sh sync
