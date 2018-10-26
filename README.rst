SODAR
^^^^^

SODAR (System for Omics Data Access and Retrieval) is a specialized system for
managing data in omics research projects.

The system provides a web-based GUI running on the python based Django web
server with apps for managing project permissions, modeling research data and
managing both small and large scale files.

In the **Sample Sheets** app, research data modeled in the
`ISA-Tools <https://isa-tools.org/>`_ standard can be viewed and searched.

Using the **Landing Zones** app a user can manage their large scale data input
in the `iRODS <https://irods.org/>`_ distributed file storage system.

The project is built on the `SODAR Core <https://cubi-gitlab.bihealth.org/CUBI_Engineering/CUBI_Data_Mgmt/sodar_core>`_
framework, which provides the base functionalities for project management and
dynamic app content inclusion.

SODAR uses the external
`SODAR Taskflow <https://cubi-gitlab.bihealth.org/CUBI_Engineering/CUBI_Data_Mgmt/sodar_taskflow>`_
service for managing large scale data transactions in the iRODS system.

See `docs_dev <docs_dev>`_ for development documentation.

:License: MIT
