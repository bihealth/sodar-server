============
Installation
============

.. warning::

   Under construction!

Development Setup
=================

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
For development it is recommended to place this variable in an .env file and set
``DJANGO_READ_DOT_ENV_FILE`` true in your actual environment. See ``base.py``
for more information.

.. code-block:: shell

    $ export DATABASE_URL='postgres://omics_data_mgmt:omics_data_mgmt@127.0.0.1/omics_data_mgmt'

Clone the repository and setup the virtual environment inside:

.. code-block:: shell

    $ virtualenv -p python3 .venv
    $ source .venv/bin/activate

Install the dependencies:

.. code-block:: shell

    $ sudo utility/install_os_dependencies.sh install
    $ sudo utility/install_phantomjs.sh
    $ pip install --upgrade pip
    $ utility/install_python_dependencies.sh install
    $ for f in requirements/*.txt; do pip install -r $f; done

Initialize the database:

.. code-block:: shell

    $ ./manage.py migrate

Run tests

.. code-block:: shell

    $ ./manage.py test

Create Django superuser, needed to create initial project(s) on the site

.. code-block:: shell

    $ ./manage.py createsuperuser


Development Environment and Execution
=====================================

**NOTE:** The below refers to prototype functionality which will be added to
release v0.3 and may not be available before that.

Docker
------

It is recommended to use `omics_docker_env <https://gitlab.bihealth.org/cubi_data_mgmt/omics_docker_env>`_
for setting up the distributed Omics Data Management environment for development
and testing. see the README file for instructions.

The docker environment provides quick and easy installation with high
performance. As drawbacks, iRODS data is erased upon each time the environment
is brought down/up. Also, debugging may get more complex.

The following components are included (see details in the env README):

* iRODS iCAT server
* `madeline_docker <https://gitlab.bihealth.org/cubi_data_mgmt/madeline_docker>`_
* `omics_taskflow <https://gitlab.bihealth.org/cubi_data_mgmt/omics_taskflow>`_
* `omics_irods_rest <https://gitlab.bihealth.org/cubi_data_mgmt/omics_irods_rest>`_
* iRODS Cloud Browser

After installing and deploying the Docker env, run the following script to
populate the iRODS database with project structures:

.. code-block:: shell

    $ ./manage.py synctaskflow

Then run Omics Data Management with Docker configuration with the following script.

.. code-block:: shell

    $ ./run_docker.sh

If you need to quickly reset the Docker environment while developing or
debugging, use the following script. It wipes out the iRODS database, runs
synctaskflow and restarts the site with Docker configuration.

.. code-block:: shell

    $ ./relaunch_docker.sh


Local Environment without Docker
--------------------------------

This is recommended when you want to develop with changes to multiple
components or do complex debugging. It's slower and more complex to set up but
provides easy access and debugging to all components. Also, iRODS data is
permanently stored until the VM is destroyed.

Default host and port settings for each component should be OK, unless you have
something exotic running already..

Provision and run a virtual machine with the iRODS iCAT Server. An Ansible
script for this with all can be found in the `CUBI Playbooks <https://gitlab.bihealth.org/cubiadmin/cubi_playbook>`_
You can use e.g. Virtualbox or Vagrant.

TODO: Push Vagrant files somewhere and link here

This will also install the iRODS Cloud Browser, so you don't have to install it separately.

Install `Redis <https://redis.io/>`_ and run it, default settings are OK. This is
required by omics_taskflow.

.. code-block:: shell

    $ ./redis-server

Install and run `omics_taskflow <https://gitlab.bihealth.org/cubi_data_mgmt/omics_taskflow>`_
(see project README for details)

Install and run `omics_irods_rest <https://gitlab.bihealth.org/cubi_data_mgmt/omics_irods_rest>`_
(see project README for details)

NOTE: Madeline is only needed for displaying the pedigrees in germline sample
sheets. It not being available doesn't cause crashes so unless debugging this
specific

Once all components are up and running, sync iRODS stuff..

.. code-block:: shell

    $ ./manage.py synctaskflow

..and run Omics Data Management with local configuration.

.. code-block:: shell

    $ ./run.sh
