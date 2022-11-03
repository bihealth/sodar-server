.. _admin_custom:

Site Customization
^^^^^^^^^^^^^^^^^^

This document provides instructions for customizing your SODAR instance.


Custom Include Templates
========================

SODAR makes use of custom template includes supported by SODAR Core. These are
not included in the repository but have to be provided during deployment. They
should be placed under ``sodar/templates/include/`` or the corresponding volume
in the `Docker Compose <https://github.com/bihealth/sodar-docker-compose>`_
environment. Examples of these templates are provided in
``sodar/templates/include_example/*.html.example``.

Supported templates:

``_footer.html``
    Custom page footer.
``_login_extend.html``
    Extra content displayed in the login view.
``_titlebar_nav.html``
    Links permanently displayed in the site title bar.
