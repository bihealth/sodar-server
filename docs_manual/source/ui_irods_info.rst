.. _ui_irods_info:

iRODS Info
^^^^^^^^^^

This view displays the status of the SODAR iRODS server.
`iRODS <https://irods.org>`_ is the system used for mass file data storage in
SODAR. You can use this information to verify that the iRODS file server is up
and running in case of data access problems.

.. figure:: _static/sodar_ui/irods_info.png
    :align: center
    :scale: 75%

    iRODS Info view with server status

In this view you can generate your personal iRODS configuration by clicking the
:guilabel:`Download Configuration` button. See :ref:`data_transfer_irods`
for more information on connecting to iRODS and data transfers.

Upon your initial SODAR login, an iRODS user account will also be created for
you with the same user name and password you use to access SODAR. However, to
access any project data in iRODS you will need to be explicitly granted project
access in SODAR.

.. include:: _include/oidc_irods_token.rst
