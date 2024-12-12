.. _data_transfer_irods:

iRODS Access
^^^^^^^^^^^^

Experiment data for omics project data is stored under a distributed iRODS
server, which you can log on to with your Charité or MDC credentials. For
accessing project data, membership in respective projects must be granted to you
by a project owner or delegate.

For each project, sample data repository is located in the read-only
``sample_data`` collection. For uploading new files, you must create a landing
zone as a temporary workspace. These are placed under the ``landing_zones``
collection. For more instructions, see the Landing Zones application under the
project you are working on.


Command Line Access (Linux)
===========================

For command line access to iRODS, you should use iRODS iCommands in your Linux
shell.

On the BIH Cluster, the required packages are already installed. If you need to
access the data from elsewhere on the network, you need to install the
``irods-icommands`` package. See the
`official installation instructions <https://irods.org/download/>`_ for more
information.

To configure your iCommands connection, open the
:ref:`ui_irods_info` application. In the app, click the
:guilabel:`Download Configuration` button to download the required configuration
file(s). These include the ``irods_environment.json`` file pre-configured for
your user account and an optional client-side server certificate file, if
applicable.

To set up the environment, open your terminal, enter the directory where you
saved the downloaded configuration file and ensure the iRODS configuration
directory has been created:

.. code-block:: bash

    $ mkdir -p ~/.irods

Next, either copy the returned ``irods_environment.json`` file to the directory:

.. code-block:: bash

    $ cp irods_environment.json ~/.irods/

Alternatively, if you received an ``irods_config.zip`` archive from SODAR, unzip
it into the configuration directory:

.. code-block:: bash

    $ unzip irods_config.zip -d ~/.irods

Now you can initialize your connection to iRODS:

.. code-block:: bash

    $ iinit

You will be prompted for your password, which is the same one you use to access
the SODAR web server. After this, you should be successfully logged on to iRODS
and can access data on the storage in your terminal.

.. include:: _include/oidc_irods_token.rst

.. include:: _include/irods_env_update.rst

See `iRODS documentation <https://docs.irods.org/master/icommands/user/>`_
for iCommands reference.


WebDAV
======

Project iRODS data can be accessed for through WebDAV by mounting it as a
network drive or browsing it in read-only mode on a web browser. Links in SODAR
UI provide shortcuts to specific collections and files on the WebDAV.
