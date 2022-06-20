SODAR
=====

.. image:: https://github.com/bihealth/sodar-server/actions/workflows/build.yml/badge.svg
    :target: https://github.com/bihealth/sodar-server/actions/workflows/build.yml

.. image:: https://app.codacy.com/project/badge/Grade/061ef313e0b64bebb46549d6deac0317
    :target: https://www.codacy.com/gh/bihealth/sodar-server/dashboard

.. image:: https://app.codacy.com/project/badge/Coverage/061ef313e0b64bebb46549d6deac0317
    :target: https://www.codacy.com/gh/bihealth/sodar-server/dashboard

.. image:: https://img.shields.io/badge/License-MIT-green.svg
    :target: https://opensource.org/licenses/MIT

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/ambv/black

SODAR (System for Omics Data Access and Retrieval) is a specialized system for
managing data in omics research projects. SODAR provides biomedical scientists
with a single point of access to data in their projects, along with linking out
to external resources and systems.

The main features of SODAR:

- Project based access control and data encapsulation
- Modeling study design metadata
- Large scale data storage
- Linking files to metadata
- Validation of file uploads
- Various tools for aiding in data management

Getting Started
---------------

For instructions on using and administering the system, see the
`SODAR manual <https://sodar-server.readthedocs.io/>`_.

For trying out the system or deploying it in production, see the
`SODAR Docker Compose <https://github.com/bihealth/sodar-docker-compose>`_
repository.

Technical Information
---------------------

SODAR provides a web-based GUI and REST APIs running on the
`Django <https://www.djangoproject.com/>`_ web server.

Studies are modeled with the `ISA Model <https://isa-tools.org>`_ specification.
For file storage SODAR uses the `iRODS <https://irods.org/>`_ open source data
management software.

Django apps provided by SODAR:

- **Samplesheets**: Modeling of study metadata in the ISA-Tab format
- **Landingzones**: Management of file validation and uploads into iRODS
- **Irodsadmin**: iRODS data administration helpers
- **Irodsbackend**: Backend app for iRODS queries and operations
- **Irodsinfo**: Display iRODS server information and create user configurations
- **Ontologyaccess**: Parse, store and serve ontologies for local lookup

The project is built on the `SODAR Core <https://github.com/bihealth/sodar-core>`_
framework, which provides the base functionalities for project management, user
interfaces and dynamic app content inclusion.

SODAR uses the external
`SODAR Taskflow <https://github.com/bihealth/sodar-taskflow>`_
service for managing large scale data transactions in the iRODS system.

**Note:** The project and documentation may refer to practices, services or data
specific to research work at Berlin Institute of Health, Core Unit
Bioinformatics. You may need to adapt them if you wish to deploy your own SODAR
instance.
