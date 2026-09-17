.. _admin_custom:

Site Customization
^^^^^^^^^^^^^^^^^^

This document provides instructions for customizing your SODAR instance.


Custom Include Templates
========================

SODAR makes use of custom template includes supported by SODAR Core. These are
not included in the repository but have to be provided during deployment. They
should be placed under the include template path defined in
``PROJECTROLES_TEMPLATE_INCLUDE_PATH`` (by default ``sodar/templates/include/``)
or the corresponding volume in the
`SODAR Docker Compose <https://github.com/bihealth/sodar-docker-compose>`_
network. Examples of these templates are provided in
``sodar/templates/include_example/*.html.example``.

Supported templates:

``_footer.html``
    Custom page footer.
``_login_extend.html``
    Extra content displayed in the login view.
``_titlebar_nav.html``
    Links permanently displayed in the site title bar.


.. _admin_custom_login_override:

Login Template Override
=======================

If you need to override the entire login template, you can do it by placing
a template file named ``login.html`` under the include template path defined in
``PROJECTROLES_TEMPLATE_INCLUDE_PATH``.
