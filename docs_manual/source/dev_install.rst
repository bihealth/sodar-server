.. _dev_install:

Installation for Development
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This section guides you through installing and running SODAR for local
development.

Unlike :ref:`installation for evaluation or deployment <admin_install>`, you
will need to install and run the SODAR web server and related first party
components locally on your development workstation. Third party services such as
iRODS and database servers can still be run in a Docker Compose network.


Prerequisites
=============

System requirements for SODAR development are as follows:

- Ubuntu 20.04 Focal
    - Recommended: other distributions and versions may work but are not
      supported. The instructions in this section assume the use of Ubuntu
      20.04.
- Python 3.8, 3.9 or 3.10
    - 3.8 recommended.


Install SODAR
=============

Set Up the Repository
---------------------

First, clone the ``sodar-server`` repository and install the OS dependencies
along with Python. Make sure to checkout the ``dev`` branch, as that is the
bleeding edge branch used as a base for development.

.. code-block:: console

    $ git clone https://github.com/bihealth/sodar-server.git
    $ cd sodar
    $ git checkout dev
    $ sudo utility/install_os_dependencies.sh
    $ sudo utility/install_python.sh

Next, setup and activate a virtual environment. Once in the environment, install
the Python dependencies for the project:

.. code-block:: console

    $ python3 -m venv .venv
    $ source .venv/bin/activate
    $ utility/install_python_dependencies.sh

It is also possible to use other virtual environments such as pipenv or conda,
but those are not supported.

Set Up External Components
--------------------------

In addition to this ``sodar-server`` repository, the following components are
required for SODAR development:

- SODAR Taskflow
    - To be removed in SODAR v0.12.0.
- PostgreSQL v9.6+
    - v11 recommended.
- Redis
- Main iRODS server
    - Persistent storage for development.
- Test iRODS server
    - Only used in testing, storage wiped out after each test run.

**TODO:** Describe running setup with sodar-docker-compose: requires new Docker
Compose file and must be tested first.

- Set up port forwarding in dev compose file
    * TBD: Forward non-default ports to avoid conflicts?
- Update all env vars in docker compose env and SODAR env.example
- Test!

**TODO:** Mention it is also possible to run these locally if needed.

**TODO:** Describe setting up ``.env`` file for SODAR and updating these values
accordingly (provide an example?)

To ensure the file gets read by Django, ensure ``DJANGO_READ_DOT_ENV_FILE=1`` is
set in your environment variables.

Database Setup (Optional)
-------------------------

If you set up PostgreSQL using the SODAR Docker Compose network, you can skip
this step.

If manually running a PostgreSQL server instead, you will need to create a user
and a database for the SODAR server. In the example, we use ``sodar`` for the
database, user name and password. Make sure to give the user the permission to
create further PostgreSQL databases, which will be used for testing.

Alternatively, you can use the ``utility/setup_database.sh`` script and follow
the command line prompt.

.. code-block:: console

    $ sudo su - postgres
    $ psql
    $ CREATE DATABASE sodar;
    $ CREATE USER sodar WITH PASSWORD 'sodar';
    $ GRANT ALL PRIVILEGES ON DATABASE sodar to sodar;
    $ ALTER USER sodar CREATEDB;
    $ \q

You have to add the credentials in the environment variable ``DATABASE_URL``.

Example in .env file:

.. code-block:: bash

    DATABASE_URL=postgres://sodar:sodar@127.0.0.1/sodar

LDAP Setup (Optional)
---------------------

If you will be using LDAP/AD auth on your site, make sure to also run:

.. code-block:: bash

    $ sudo utility/install_ldap_dependencies.sh
    $ pip install -r requirements/ldap.txt

**TODO:** Update

Sample Sheets Vue.js App Installation
-------------------------------------

You need to install the Vue.js app prerequisites with NPM. First install the
prerequisites using the following command:

.. code-block:: bash

    $ sudo utility/install_vue_dev.sh

Once NPM has been set up, install the app requirements:

.. code-block:: bash

    $ cd samplesheets/vueapp
    $ npm install

Final Setup
-----------

Initialize the database (this will also synchronize django-plugins):

.. code-block:: bash

    $ ./manage.py migrate

Create a Django superuser for the SODAR site:

.. code-block:: bash

    $ ./manage.py createsuperuser


Prerequisites / Docker Environment
----------------------------------

The easiest way to get the dependencies up is to clone and run the SODAR docker
environment in
`sodar-docker-env <https://github.com/bihealth/sodar-docker-env>`_.

If you want to set up an iRODS server locally, you must have ``MD5`` set as the
default hash scheme in ``server_config.json``. In the Docker environment setup
CUBI Ansible playbooks this is already pre-configured.

SODAR Taskflow
--------------

For development it is recommend to run sodar_taskflow locally.

First, clone the `Sodar Taskflow <https://github.com/bihealth/sodar-taskflow>`_
repository.

Follow the installation instructions in the ``README.rst`` file. Make sure to
configure environment variables to point to the Redis and iRODS servers you are
using.

Configure SODAR Components
--------------------------

In the SODAR environment variables (preferably in the ``.env`` file), set up
iRODS and Taskflow variables to point to your server. The default values in
``config/settings/base.py`` point to the sodar-docker-env and sodar-taskflow
defaults. If using the Docker environment and local Taskflow service, no changes
should thus be required.

Similar configuration also needs to be done to SODAR Taskflow, see instructions
in its respective project repository.


Run the Components
==================

For best results, start the required components in the order presented here.

1. SODAR Docker Environment
---------------------------

Make sure Redis and iRODS iCAT server(s) are running. If you have set up and
launched the sodar_docker_env environment, they all should be available as
Docker containers.

Run the ``sodar-docker-env`` Docker environment as follows:

.. code-block:: console

    $ utility/env_restart.sh

**NOTE:** It can take a bit of time for the iRODS server to initialize.

2. SODAR Taskflow
-----------------

In the ``sodar-taskflow`` repository, start the SODAR Taskflow service:

.. code-block:: console

    $ utility/run_dev.sh

3. Sample Sheets Vue App
------------------------

The Sample Sheets Vue app must be run in a separate process using NPM. The
easiest way is to use the shortcut script in the SODAR project, which will
serve the development version with hot reload in ``http://127.0.0.1:8080``.

.. code-block::

    $ make samplesheets_vue

4. SODAR Celery Processes
-------------------------

For asynchronous tasks, run the SODAR celery process in debug mode using the
following command:

.. code-block:: console

    $ make celery

Note that the Celery process needs to access correct Django settings. Make sure
the variable ``DJANGO_READ_DOT_ENV=1`` is set in your environment when running
this process! This will also start the Celery beat scheduler.

5. SODAR Django Site
--------------------

Finally, we can start up the actual SODAR Django Site. In the SODAR root
directory, start the site in debug mode with ``local`` settings.

.. code-block:: console

    $ make serve

**NOTE:** If existing data on your development iRODS server has been wiped out
due to e.g. rebooting the Docker environment project metadata and collections
(but not data objects) can be synced with the following command:

.. code-block:: console

    $ ./manage.py synctaskflow

There is also a shortcut for syncing iRODS data and starting the server:

.. code-block:: console

    $ make serve arg=sync

Now you should be able to browse to http://127.0.0.1:8000 and see your site.
iRODS and Taskflow functionalities should also be available.
