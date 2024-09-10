.. _dev_install:

Installation for Development
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This section guides you through installing and running SODAR for local
development.

Unlike :ref:`installation for evaluation or deployment <admin_install>`, you
will need to run the SODAR Django server and related components locally on your
development workstation. Third party services such as iRODS and database servers
can still be run in a Docker Compose network.


Prerequisites
=============

System requirements for SODAR development are as follows:

- Ubuntu 20.04
    - Other Ubuntu versions and Linux distributions may work but are not
      supported. The instructions in this section assume the use of Ubuntu
      20.04.
- Python 3.9, 3.10 or 3.11
    - 3.11 is recommended.
- `Docker <https://docs.docker.com/get-docker/>`_
- `Docker Compose <https://docs.docker.com/compose/install/>`_
- `OpenSSL <https://www.openssl.org/>`_


SODAR Docker Compose Setup
==========================

In addition to the ``sodar-server`` repository, the following components are
required for SODAR development:

- PostgreSQL v12+ (v16 recommended)
- Redis
- Main iRODS server
- Test iRODS server

The recommended method to set up the environment required for development is
cloning the
`sodar-docker-compose <https://github.com/bihealth/sodar-docker-compose>`_
repository and running it in development mode.

The environment is the same used for evaluation and deployment as described
in the :ref:`administration section <admin_install>`. In this case, we will use
it to only provide the aforementioned services in a Docker Compose network. The
Django server, Vue.js app and Celery workers will be run locally for development
and debugging.

.. note::

    You can also run these components outside of the Docker Compose network if
    needed. In this case, you will need to modify the related server addresses
    and ports in SODAR configurations, as well as initialize the required
    services and databases manually.

1. Clone the Repository
-----------------------

Clone the ``sodar-docker-compose`` repository. It is recommended to clone it
into a specific directory so you can still easily run the evaluation version of
the environment in a separate Docker Compose network if needed.

.. code-block:: bash

    $ git clone https://github.com/bihealth/sodar-docker-compose.git sodar-docker-compose-dev
    $ cd sodar-docker-compose-dev

2. Initialize Volumes
---------------------

Use the provided ``init.sh`` script to create required configuration and volume
directories.

.. code-block:: bash

    $ ./init.sh

3. Provide Certificate and DH Parameters
----------------------------------------

Similar to evaluating SODAR, you will need to provide self-signed TLS/SSL
certificates and Diffie-Hellman key exchange parameters to enable full SODAR
functionality.

For instructions on how to generate certificates with OpenSSL in Ubuntu, see
`here <https://ubuntu.com/server/docs/security-certificates>`_. If using a
different Linux distribution, consult the relevant documentation.

Once generated, ensure your ``.crt`` and ``.key`` files are placed under the
``config/traefik/tls`` directory.

.. code-block:: bash

    $ cp yourcert.crt config/traefik/tls/server.crt
    $ cp yourcert.key config/traefik/tls/server.key
    $ chmod +r config/traefik/tls/server.key

To generate the ``dhparams.pem`` file for Diffie-Hellman key exchange, you can
use OpenSSL as demonstrated below. Ensure the file is placed under
``config/irods/etc``.

.. code-block:: bash

    $ openssl dhparam -2 -out config/irods/etc/dhparams.pem 2048

4. Configure the Environment
----------------------------

Copy the file ``env.example.dev`` into ``.env`` to use the default
sodar-docker-compose configuration for development.

.. code-block:: bash

    $ cp env.example.dev .env

In the case of the development setup, this environment only includes variables
available to the external SODAR components. The ``sodar-server`` settings will
be set up in a local ``.env`` file we will describe further on in this document.

5. Bring Up the Environment
---------------------------

To run the environment in the development configuration, use the following
helper script:

.. code-block:: bash

    $ ./run_dev.sh

You will see a real-time output of the environment. To shut down the network,
press ``Ctrl-C``.


SODAR Server Setup
==================

With the required external components running in Docker, you can set up and run
the SODAR Django server and other local components.

1. Set Up the Repository
------------------------

First, clone the ``sodar-server`` repository and install the OS dependencies
along with Python. Make sure to check out the ``dev`` branch, as it is used as
the base for all development.

.. code-block:: bash

    $ git clone https://github.com/bihealth/sodar-server.git
    $ cd sodar-server
    $ git checkout dev
    $ sudo utility/install_os_dependencies.sh
    $ sudo utility/install_python.sh

2. Install Python Dependencies
------------------------------

Next, create and activate a virtual environment. Once in the environment,
install the Python dependencies for the project:

.. code-block:: bash

    $ python3 -m venv .venv
    $ source .venv/bin/activate
    $ utility/install_python_dependencies.sh

It is also possible to use other virtual environments such as pipenv or conda,
but those are not supported.

3. Copy the Environment File
----------------------------

Next, copy the supplied ``env.example`` file into ``.env``. This contains the
settings for running the SODAR server with the default development
configuration.

.. code-block:: bash

    $ cp env.example .env

To ensure the file gets read by Django, ensure ``DJANGO_READ_DOT_ENV_FILE=1`` is
set in your environment variables.

4. Install the Vue.js Application
---------------------------------

To enable the Sample Sheets Vue.js app in development, you need to install its
prerequisites. First, install Nodejs and Vue dependencies using the following
command:

.. code-block:: bash

    $ sudo utility/install_vue_dev.sh

Once the dependencies have been set up, install the app requirements:

.. code-block:: bash

    $ cd samplesheets/vueapp
    $ npm install

5. Final Setup
--------------

The SODAR database needs to be initialized and migrated to run the server
locally. This will also synchronize the app plugins for the server.

.. code-block:: bash

    $ cd sodar-server
    $ ./manage.py migrate

Next, run commands to retrieve the Iconify icons and collect static files.

.. code-block:: bash

    $ ./manage.py geticons
    $ ./manage.py collectstatic

Finally, you should create a Django superuser for the SODAR site. Use the user
name ``admin`` if you do not wish to edit your configuration files. Run the
following command and follow the command line prompt.

.. code-block:: bash

    $ ./manage.py createsuperuser --skip-checks --username admin

LDAP Setup (Optional)
---------------------

If you will be developing features using LDAP/AD authentication, make sure to
also run:

.. code-block:: bash

    $ sudo utility/install_ldap_dependencies.sh
    $ pip install -r requirements/ldap.txt

Furthermore, update your LDAP settings in the ``.env`` file.


Run SODAR for Development
=========================

With both the Docker environment and the SODAR server set up, you can now run
all the component to have a local SODAR environment for development. It is
recommended to run the components in the order presented here.

.. note::

    This will require running multiple services which remain active in their
    respective terminals. Thus multiple terminal tabs or windows will be
    required.

1. SODAR Docker Compose
-----------------------

During first time setup, you should also have the environment running at this
point. If not, run it with the following commands:

.. code-block:: bash

    $ cd sodar-docker-compose-dev
    $ ./run_dev.sh

2. SODAR Django Server
----------------------

In a separate terminal tab, run the SODAR Django server. Make sure to activate
your virtual environment.

.. code-block:: bash

    $ cd sodar-server
    $ source .venv/bin/activate
    $ make serve

3. Sample Sheets Vue App
------------------------

Open a new terminal tab and run the Sample Sheets Vue.js app with the following
command. This will serve the development version with hot reloading in
``http://127.0.0.1:8080``.

.. code-block:: bash

    $ make samplesheets_vue

4. SODAR Celery Processes
-------------------------

For asynchronous tasks, run the SODAR celery process in debug mode. First, open
a new terminal tab, make sure to activate your virtual environment and run
Celery with Celerybeat using the following command:

.. code-block:: bash

    $ source .venv/bin/activate
    $ make celery

.. note::

    The Celery process needs to access correct Django settings. Make sure the
    variable ``DJANGO_READ_DOT_ENV_FILE=1`` is set in your environment when
    running this process.

Navigate to SODAR
-----------------

Now you should have all the required components running for developing SODAR.
Use your web browser to open http://127.0.0.1:8000 and you should see your local
SODAR development site.
