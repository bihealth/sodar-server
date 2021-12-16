.. _glossary:

Glossary
^^^^^^^^

Application
    In SODAR, a group of views and actions related to a specific functionality
    are called an *application*, or *app* for short. In the SODAR UI,
    applications can be recognized by their links in the project sidebar or the
    user dropdown, as well as URL patterns. Applications can either be project
    specific or site-wide applications. The most prominent applications in SODAR
    are :ref:`Sample Sheets <app_samplesheets>`,
    :ref:`Landing Zones <app_landingzones>`, and the
    :ref:`Timeline <ui_project_timeline>`.
Assay
    In the context of SODAR, *assay* refers to assays as defined in the
    ISA-Tab specification. For more information, see :ref:`metadata_recording`.
Assay Plugin
    SODAR internally uses assay plugins to determine how assay shortcuts and
    links to iRODS data are determined and presented to the user. For more
    information see :ref:`metadata_advanced`.
HPO
    The `Human Phenotype Ontology <https://hpo.jax.org/>`_.
IGV
    The `Integrative Genomics Viewer <https://software.broadinstitute.org/software/igv/>`_.
Investigation
    Investigation is the topmost structure in the ISA-Tab format. An
    investigation can contain one or more studies. SODAR supports one
    investigation per project. For more information, see :ref:`metadata_recording`.
iRODS
    The `Integrated Rule-Oriented Data System <https://irods.org>`_.
ISA-Tab
    The TSV-based file format for the
    `ISA Framework specification <https://isa-tools.org/format/specification.html>`_.
JSON
    JavaScript Object Notation, the format used for providing data in e.g.
    sample sheet editing.
Landing Zone
    User-specific file area with write access. Used for uploading files which
    will then be transferred into the read-only sample data repository.
Markdown
    Lightweight text-to-HTML markup language for creating formatted text. Used
    in e.g. project ReadMe documents.
REST API
    An application programming interface following the representational state
    transfer (REST) principles.
Sample Data Repository
    Read-only file area containing the sample and study data files accessible
    through sample sheets. Files are uploaded here through landing zones.
Sample Sheets
    Project study design and sample metadata, presented in a tabular form and
    grouped into studies and assays. Based on the
    `ISA Framework <https://isa-tools.org>`_ and enhanced with SODAR-specific
    links, shortucts and additional features.
SODAR
    System for Omics Data Access and Retrieval.
Study
    In the context of SODAR, *study* refers to studies as defined in the
    ISA-Tab specification. For more information, see :ref:`metadata_recording`.
TSV
    Tab-separated Values. A data format used e.g. by the ISA-Tab specification.
UUID
    Universally unique identifier. Used in SODAR to refer to all relevant
    objects in the system.
WebDAV
    Web Distributed Authoring and Versioning. Used in SODAR to provide web-based
    access to files, mount iRODS collections as network drives, provide random
    access to large files and link files to external tools such as IGV.
