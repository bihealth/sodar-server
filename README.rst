SODAR
=====

.. image:: https://github.com/bihealth/sodar-server/workflows/build/badge.svg
    :target: https://github.com/bihealth/sodar-server/actions?query=workflow%3Abuild

.. image:: https://img.shields.io/badge/License-MIT-green.svg
    :target: https://opensource.org/licenses/MIT

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/ambv/black

SODAR (System for Omics Data Access and Retrieval) is a specialized system for
managing data in omics research projects.

The system provides a web-based GUI running on the python based Django web
server with apps for managing project permissions, modeling research data and
managing both small and large scale files.

In the **Samplesheets** app, research data modeled in the
`ISA-Tools <https://isa-tools.org/>`_ standard can be viewed and searched.

Using the **Landingzones** app a user can manage their large scale data input
in the `iRODS <https://irods.org/>`_ distributed file storage system.

Additional apps provided by SODAR:

- **Irodsadmin**: iRODS data administration helpers
- **Irodsbackend**: Backend app for iRODS queries and operations
- **Irodsinfo**: Display iRODS server information and create user configurations
- **Ontologyaccess**: Parse, store and serve ontologies for local lookup

The project is built on the `SODAR Core <https://github.com/bihealth/sodar-core>`_
framework, which provides the base functionalities for project management and
dynamic app content inclusion.

SODAR uses the external
`SODAR Taskflow <https://github.com/bihealth/sodar-taskflow>`_
service for managing large scale data transactions in the iRODS system.

See `docs_dev <docs_dev>`_ for development documentation.

**Note:** This project is under heavy development and all features may not be
fully tested or documented. Improved documentation is forthcoming.

**Note:** The project and documentation may refer to practices, services or data
specific to research work at Berlin Institute of Health, Core Unit
Bioinformatics. You may need to adapt them if you wish to deploy your own SODAR
instance.
