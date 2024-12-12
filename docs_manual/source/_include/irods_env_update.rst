.. note::

    SODAR v1.0+ uses iRODS v4.3, which requires an updated client software and
    environment. If you experience connection issues, ensure you are running on
    the latest version iCommands or any other iRODS client(s) you use. You also
    need to download a new ``irods_environment.json`` file in the
    :ref:`ui_irods_info` application. Alternatively, edit your existing JSON
    file and change the value of ``irods_authentication_scheme`` from ``PAM`` to
    ``pam_password``.
