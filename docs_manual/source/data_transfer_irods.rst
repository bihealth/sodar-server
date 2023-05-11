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

.. note::

    On Ubuntu 22.04, installing iCommands is not officially supported at the
    time of writing. For workarounds,
    `see this discussion <https://github.com/irods/irods/issues/4883>`_.

To configure your iCommands connection, open the
:ref:`ui_irods_info` application. In the app, click the
:guilabel:`Download Configuration` button to download a configuration file
archive. This archive contains the ``irods_environment.json`` file
pre-configured for your user account. A server certificate file for secure
connections is also included, if applicable.

Enter the directory where you saved the downloaded archive and enter the
following commands:

.. code-block:: console

    mkdir -p ~/.irods
    unzip irods_config.zip -d ~/.irods
    iinit

You will be prompted for your password, which is the same one you use to access
this web site. After this, you should be successfully logged on to iRODS and can
access data on the storage in your terminal.

.. note::

    When using ``iput`` or ``irsync`` to upload data into the SODAR iRODS
    server, you must use the ``-k`` argument to enable checksum generation.

See `iRODS documentation <https://docs.irods.org/master/icommands/user/>`_
for iCommands reference.


WebDAV
======

Project iRODS data can be accessed for through WebDAV by mounting it as a
network drive or browsing it in read-only mode on a web browser. Links in SODAR
UI provide shortcuts to specific collections and files on the WebDAV.
