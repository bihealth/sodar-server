.. _introduction:

SODAR Introduction
^^^^^^^^^^^^^^^^^^

.. youtube:: LQ8foUpjnqs
    :align: center

____________________

SODAR stands for the System for Omics Data Access and Retrieval. It is a
centralized system for providing access to raw data, results, and metadata in
omics research projects. SODAR is targeted for researchers and project owners
who want to manage their experiment data according to the
`FAIR principles <https://www.go-fair.org/fair-principles/>`_:
*findable*, *accessible*, *interoperable* and *reusable*.

SODAR is developed by the
`Core Unit Bioinformatics <https://www.cubi.bihealth.org/>`_ at the
`Berlin Institute of Health <https://www.bihealth.org/>`_.

SODAR aims at providing the following capabilities for managing omics research
data:

- Project based access control and data encapsulation
- Modeling and management of study design metadata
- Large scale data storage
- Linking files to metadata
- Management and validation of file uploads
- Management of study design templates
- Tools for aiding project data management
- Integrating data with third party tools

SODAR can be accessed either by a web based
:ref:`graphical user interface <ui_index>` or
:ref:`REST APIs <api_documentation>` for programmatic use.


Data Workflow
=============

The SODAR data workflow involves the following elements:

:ref:`Projects and Categories <ui_index>`
    In SODAR, data and user access are structured into *projects*, which exist
    under *categories*. Projects contain project study modeling, file data and
    other project related functionality. A category can be thought of as a
    project with no data and the possibility to contain other categories or
    projects under it.
:ref:`Sample Sheets <app_samplesheets>`
    Sample sheets contain the sample, process and material metadata for project
    studies. They are modeled in the `ISA Model <https://isa-tools.org/>`_
    standard as *investigations*, *studies* and *assays*. One SODAR project can
    contain one investigation with one or more studies.
:ref:`Large Scale Data Storage <data_transfer_irods>`
    The actual sample data files for studies and assays are stored in a
    distributed file system built on `iRODS <https://irods.org>`_. This data
    can contain anything from binary alignment map files to e.g. reports and log
    files. The files can be accessed through relevant sample sheet metadata in
    SODAR.
:ref:`Landing Zones <app_landingzones>`
    Uploading new sample data is done through landing zones, which are temporary
    user-specific file areas with write access. Once uploads are prepared, SODAR
    validates the files and moves them into the read-only sample data
    repository.


Notable Features
================

- Accessibility
    * User access via one or multiple LDAP/AD services and/or local accounts
    * Access tokens can be can be generated for REST API use
    * UUIDs and permanent URLs for all relevant objects in the system
- iRODS Integration
    * Automated iRODS environment file generation
    * WebDAV for mounting iRODS as a network drive and web-based browsing of
      files, supporting random file access
- Sample Sheets
    * Sample sheet import from existing ISA-Tab TSV files
    * Sample sheet generation from templates
    * Sample sheet editing and version control
    * Sample sheet export in ISA-Tab and Excel formats
    * Automated iRODS shortcut generation for BAM/CRAM/VCF files
    * Automated Integrative Genomics Viewer (IGV) session file generation and
      merging
    * Track hub management for UCSC Genome Browser integration
- Landing Zones
    * Automated validation and of file uploads
    * Transactions with rollback for file transfers to avoid invalid or
      incomplete data to be entered to projects
    * Automated generation of expected iRODS collections for standardized data
      structures
- Other Features
    * Searching for sources, samples and files in iRODS
    * Timeline application for enhanced event logging an providing audit trails
