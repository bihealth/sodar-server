.. _sodar_release_notes:

Release Notes
^^^^^^^^^^^^^

This document lists major updates and feature in SODAR releases. For a complete
list of changes in current and previous releases, see the
:ref:`full changelog<sodar_changelog>`.


v1.0.0 (WIP)
============

Release for SODAR Core v1.0 upgrade, iRODS v4.3 upgrade and feature updates.

- Add opt-out settings for iRODS data request and zone status update emails
- Add REST API list view pagination
- Add Python v3.11 support
- Add study plugin override via ISA-Tab comments
- Add session control in Django settings and environment variables
- Add token-based iRODS/IGV basic auth support for OIDC users
- Add support for comment, performer and contact field values as list
- Add support for numeric field values as list
- Add support for UTF-8 BOM header in MD5 checksum files
- Add optional SampleDataFileExistsAPIView access restricting for users with
  project roles
- Update minimum supported iRODS version to v4.3.3
- Update REST API versioning
- Update REST API views for OpenAPI support
- Update lock requiring REST API views to return 503 if project is locked
- Update REST APIs to return user UUID instead of SODARUserSerializer objects
- Update landing zone creation REST API view to return 503 if no investigation
  or iRODS collections
- Update irodsinfo configuration download to return JSON without Zip archive if
  client-side cert is not set
- Upgrade to Django v4.2
- Upgrade to Postgres v16
- Upgrade to python-irodsclient v2.2.0
- Upgrade to altamISA v0.3.0
- Upgrade to SODAR Core v1.0.5
- Remove Python v3.8 support
- Remove Postgres <12 support
- Remove iRODS <4.3 support
- `SODAR Core v1.0 updates <https://sodar-core.readthedocs.io/en/latest/major_changes.html>`_:
  OIDC auth support, new REST API versioning, owner/delegate remote sync
  controls, etc

:ref:`Administrator upgrade guide for v1.0 <admin_upgrade_v1.0>`

User Upgrade Guide
------------------

iRODS v4.3 Required
    The minimum supported version of iRODS from this version onwards is v4.3.3.
    Please ensure your iCommands package is upgraded to the latest version.
    Your ``irods_environment.json`` file also needs to be updated. It is
    recommended to download a new environment file in the :ref:`ui_irods_info`
    application. Alternatively, edit the JSON file and change the value of
    ``irods_authentication_scheme`` from ``PAM`` to ``pam_password``.
REST API Versioning Changes
    REST API versioning has changed in SODAR Core v1.0 and SODAR Server v1.0.
    Accept header versioning is now specific to each Django app providing their
    own API. The APIs now use semantic versioning and have individual version
    numbers starting at ``1.0``. There is no backwards compatibility for old
    version numbers. If your clients or scripts make use of the versioning, you
    will need to consult the REST API documentation and update them accordingly.

REST API Updates
----------------

- Sample Sheets API
    * ``IrodsAccessTicketRetrieveAPIView``
        + Return ``user`` field as UUID string instead of serializer
    * ``IrodsCollsCreateAPIView``
        + Return ``503`` if project is locked
    * ``IrodsDataRequestAcceptAPIView``
        + Return ``503`` if project is locked
    * ``IrodsDataRequestRetrieveAPIView``
        + Return ``user`` field as UUID string instead of serializer
    * ``ProjectIrodsFileListAPIView``
        + Return results as list without ``irods_data`` object
        + Return ``modify_time`` field in standard REST API format
- Landing Zones API
    * ``ZoneCreateAPIView``
        + Return ``503`` if Taskflow is not enabled
        + Return ``503`` if investigation for project is not found
        + Return ``503`` if project iRODS collections have not been created
    * ``ZoneRetrieveAPIView``
        + Return ``user`` field as UUID string instead of serializer
    * ``ZoneSubmitMoveAPIView``
        + Return ``503`` if project is locked


v0.15.1 (2024-09-12)
====================

Release for minor updates, maintenance and bug fixes.

- Fix generic assay plugin issues
- Upgrade critical dependencies
- Minor updates and bug fixes


v0.15.0 (2024-08-08)
====================

Feature release.

- Add isatemplates app for management of custom ISA-Tab templates
- Add generic assay plugin
- Add BAM/CRAM/VCF omit pattern display in study shortcut modal
- Add row links display override using assay comment
- Add iRODS checksum calculation retrying
- Add Cyberduck documentation
- Disable lock requirement for project and role update taskflows
- Make sheet template output dir field visibility optional
- Upgrade critical dependencies
- Minor updates and bug fixes

:ref:`Administrator upgrade guide for v0.15 <admin_upgrade_v0.15>`


v0.14.2 (2024-03-15)
====================

Release for minor updates, maintenance and bug fixes.

- Add CRAM file support for cancer/germline study links and IGV sessions
- Add path glob pattern support for IGV session BAM/VCF omit settings
- Add assay plugin shortcut collection creation in landing zones
- Add iRODS data request details in timeline events
- Add landing zone statistics in siteinfo
- Fix iRODS data request issues
- Fix IRODS_ROOT_PATH issues
- Fix LDAP TLS settings
- Fix iRODS stats badge stuck in "updating"
- Fix landing zone status updating not working in project details card
- Fix landing zone creation crash with large amount of created collections
- Fix multiple sheet editor issues
- Minor updates and bug fixes
- Upgrade to SODAR Core v0.13.4

User Upgrade Guide
------------------

CRAM File Support
    This release adds support for CRAM files. They are linked in studies and IGV
    sessions similar to BAM files. If your project contains CRAM files uploaded
    prior to this release, you will have to run :guilabel:`Update Sheet Cache`
    in the Sample Sheets app to enable the files in study links and generated
    IGV sessions. Alternatively, an administrator can run the ``synccache``
    management command to update all projects or a specific project.


v0.14.1 (2023-12-12)
====================

Release for minor updates, maintenance and bug fixes.

- Add iRODS v4.3 support
- Add sheet sync setting validation
- Change default IGV genome to "b37_1kg"
- Fix landing zone locking controls for non-superusers
- Fix access to new HP ontology URLs
- Fix sheet column toggle modal UI issues
- Minor updates and bug fixes
- Upgrade to SODAR Core v0.13.3

User Upgrade Guide
------------------

Default IGV Genome
    The default IGV genome for cancer and germline projects has been changed
    from "b37" to "b37_1kg", as the former is no longer supported by new
    versions of IGV. Existing settings referring the now-unavailble genome will
    be automatically updated. Users should be advised to upgrade their IGV
    software to a recent version.
HPO Term Accession
    The official API for the Human Phenotype Ontology has changed. It is
    recommended to set the default URL pattern in the Ontology Access app to
    ``https://hpo.jax.org/app/browse/term/{id_space}:{local_id}``. Furthermore,
    ``hpo.jax.org`` should be included in ``SHEETS_ONTOLOGY_URL_SKIP`` as
    bioontology.org-wrapped URLs to the new API do not work at the time of
    writing.


v0.14.0 (2023-09-27)
====================

Major feature update.

- Add general read-only iRODS access tickets for assay collections
- Add support for additional sample sheet templates
- Add landing zone updating
- Add automated checksum calculation in landing zone validation and moving
- Add iRODS delete request REST API views
- Add iRODS delete request batch handling in UI
- Add iRODS access ticket REST API views
- Add iRODS environment retrieval REST API view
- Add cytof assay plugin
- Add "create" tag for sample sheet versions
- Add user setting for maximum sample sheet table height
- Add "normalizesheets" management command to clean up existing sample sheets
- Improve sheet template creation form
- Landingzones UI improvements
- Sample sheet table resizing and rendering improvements
- Add study table cache disabling
- Minor updates and bug fixes
- Upgrade to SODAR Core v0.13.2
- SODAR Core v0.13 updates: full role inheritance, finder role, etc.

:ref:`Administrator upgrade guide for v0.14 <admin_upgrade_v0.14>`


v0.13.4 (2023-05-15)
====================

Release for minor sample sheet updates, maintenance and bug fixes.

- Update ISA-Tab template dependency to ``cubi-isa-templates``
- Allow assay tables with no materials after sample
- Fix sample sheet creation form resubmit handling
- Fix django-autocomplete-light Docker build crash


v0.13.3 (2023-05-10)
====================

Release for minor updates, maintenance and bug fixes.

- Add ``ProjectIrodsFileListAPIView`` API endpoint
- Display study and assay plugin icons to contributors and above
- Remove ``SPECIAL_FILE_LINK_HEADERS`` hack
- Update URL patterns
- Upgrade dependencies, fix site for Django v3.2.19+


v0.13.2 (2023-04-18)
====================

Maintenance and bug fix release.

- Improve iRODS path validation
- Minor updates and bug fixes


v0.13.1 (2023-03-31)
====================

Release for minor updates, maintenance and bug fixes.

- Allow restricting landing zone write access
- Add API examples to manual
- Minor updates and bug fixes


v0.13.0 (2023-02-08)
====================

Major feature update.

- Add project archiving support
- Add genome selecting for IGV sessions
- Add omitting IGV session BAM/VCF files by file suffix
- Add iRODS file check for material renaming in editor
- Add optional landing zone write access restriction to created collections
- Add study render table caching for sample sheets
- Add iRODS user account creation at login for users with LDAP/SODAR auth
- Update cancer study shortcut generating
- Fix iRODS connection handling issues
- Upgrade to SODAR Core v0.12.0


v0.12.1 (2022-11-09)
====================

Maintenance and bug fix release.

- Fix incorrect project modify API settings in production
- Fix category member role removal
- Fix Tooz and Redis connection issue handling
- Fix unhandled project locking errors
- Optimize germline study rendering and cache updating
- Upgrade Vue app dependencies
- Minor updates and bug fixes


v0.12.0 (2022-10-14)
====================

Release for integrating SODAR Taskflow with SODAR.

- Add Taskflowbackend app from SODAR Core
- Add Taskflow functionality from SODAR Taskflow v0.6.2
- Implement SODAR Core v0.11 project modify API
- Add hyperlink support for "external links" sample sheet columns


v0.11.3 (2022-07-20)
====================

Release for minor updates, maintenance and bug fixes.

- Support for additional sample sheet templates
- Hide uneditable sheet template fields in forms
- Minor updates and general bug fixes
- Upgrade Vue app dependencies
- Upgrade to SODAR Core v0.10.13
- Update manual and remove separate dev docs


v0.11.2 (2022-03-04)
====================

Release for minor updates, maintenance and bug fixes.

- Fix known sample sheet replacing issues
- Fix iRODS file search issues
- Minor updates and general bug fixes
- Upgrade to ag-grid v27
- Upgrade to SODAR Core v0.10.10


v0.11.1 (2022-02-04)
====================

Release for minor updates, maintenance and bug fixes.

- Deployment and iRODS improvements
- Upgrade Python dependencies
- Drop Python v3.7 support, add Python v3.10 support
- Minor updates and bug fixes
- Upgrade to SODAR Core v0.10.8


v0.11.0 (2021-12-16)
====================

Major feature update.

- Add simple link support to string cells in sample sheets
- Add generic raw data assay plugin
- Add assay plugin override via ISA-Tab comments
- Add default ontology column value
- Add user alerts and member emails for landing zone actions
- Add user alerts for sample sheet iRODS cache updates
- Add user message to landing zones upon successful moving
- Add "finished" parameter to LandingZoneListAPIView to access finished zones
- Add locked status info to landingzones UI and LandingZoneRetrieveAPIView
- Add descriptions and batch deletion for sample sheet versions
- Add automatic study/assay table filtering from search results
- Add collections to iRODS file list modals for landing zons
- Manual clearing of finished landing zones in UI no longer needed
- Upgrade to SODAR Core v0.10.7


v0.10.1 (2021-07-07)
====================

Maintenance and bug fix release.

- Docker setup fixes and improvements
- Site settings improvements
- Upgrade Vue app dependencies
- Minor updates and bug fixes
- Upgrade to SODAR Core v0.10.3


v0.10.0 (2021-06-11)
====================

Update for multiple new features and major SODAR Core upgrade.

- iRODS delete requests for data objects and collections
- Diff comparison for sample sheet versions
- Sample sheet creation from templates using cubi-tk
- Sample sheet read-only mirroring from another project or site
- Per-project restriction of column configuration updates
- Support for project public guest access
- Optional automated creation of expected landing zone collections
- Allow sheet export and version viewing for guest users
- Upgrade to SODAR Core v0.10


v0.9.0 (2021-02-05)
===================

Major update for ontology editing, UCSC Genome Browser integration and other new
features.

- Ontology editing and lookup support
- iRODS ticket and track hub support for UCSC Genome Browser integration
- iRODS data administration features
- Microarray assay support
- Support for missing column types in sample sheet editor
- Multi-term search support
- File status query REST API endpoint
- Landing zone UUID copying
- Major samplesheets vue app refactoring and testing
- Upgrade to SODAR Core v0.9.0


v0.8.0 (2020-09-15)
===================

Major release for row editing and other editor improvements.

- Sample sheet row insertion
- Sample sheet row deletion
- Improved cell editing support
- Sheet display config saving
- Sheet config versioning and updating
- Landing zone validation triggering with uploaded file
- API improvements


v0.7.1 (2020-04-27)
===================

Release for API updates, minor features and maintenance.

- Add tokens app from django-sodar-core
- Upgrade to django-sodar-core v0.8.1
- Add samplesheets REST API views for iRODS collection creation and sheet import
- Add REST API documentation in manual


v0.7.0 (2020-02-12)
===================

Major release for sample sheet editor, API and small files updates

- Add initial sample sheet editor for modifying basic cell values
- Add column configuring for sample sheet editor
- Add sample sheet version browsing, restoring, export and deletion
- Add initial REST API for landing zones and sample sheets
- Add shortcut columns to project list
- Move small files to iRODS, remove filesfolders app
- Refactor iRODS connections in irodsbackend
- Improve inline file linking for metabolomics assay apps
- Upgrade to django-sodar-core v0.7.2 and altamISA


v0.6.1 (2019-11-15)
===================

Release for iRODS updates and maintenance.

- Enable supplying optional iRODS environment files for connections
- iRODS logging improvements


v0.6.0 (2019-10-21)
===================

Release for ISAtab exporting, ISAtab handling updates and sample sheet rendering
improvements.

- Add ISAtab exporting
- Upgrade to altamISA v0.2.5, refactor importing for full ISA model support
- Add rendering for multiple missing columns
- Add saving of original ISAtab data into the SODAR database
- Add IGV merge shortcuts
- Add multi-file ISAtab importing
- Enforce row order in studies
- Replace TSV table export with Excel export
- Add support for panel sequencing and metabolite profiling in assays
- Upgrade to django-sodar-core v0.7.0
- Fix major issues with multi-cell copying


v0.5.1 (2019-07-09)
===================

ISAtab parser update and sample sheet viewer improvements.

- Upgrade to altamISA v0.1 for importing sample sheets
- Update models, parsing and rendering for the new parser API
- Add displaying of parser warnings
- Various sample sheet rendering improvements and fixes
- Upgrade to SODAR Core v0.6.2


v0.5.0 (2019-06-05)
===================

Release for a major sample sheet viewer update.

- New sample sheet viewer built from scratch on vue.js and ag-grid
- New design for study shortcuts
- Multi-cell selection and clipboard copying
- Table column selection
- Table column resizing
- iRODS file information caching
- iRODS collection list filtering


v0.4.6 (2019-04-25)
===================

Hotfix and maintenance release.

- Fix crash for sample sheets replacement with duplicate study names
- Upgrade site for SODAR Core v0.5.1


v0.4.5 (2019-04-11)
===================

Maintenance release.

- Fix hard coded WebDAV URL in study app IGV links
- Add missing SODAR Core v0.5 settings variables


v0.4.4 (2019-04-03)
===================

Minor maintenance release.

- Add copying of HPO term IDs to clipboard
- Upgrade to SODAR Core v0.5.0
- Bug fixes


v0.4.3 (2019-03-07)
===================

Release for iRODS query optimization, sample sheet rendering improvements and
user management improvements.

- Add iRODS linking support for transcription profiling
- Add performer and perform date rendering
- Render multiple ontology links within sample sheet cell
- Fix problems with iRODS button updating and timeouts
- Security updates for Landing Zones
- Upgrade to SODAR Core v0.4.5
- User management improvements from SODAR Core v0.4.5


v0.4.2 (2019-02-04)
===================

Release for iRODS UI improvements, catching up with SODAR Core and minor fixes.

- Client-side updating of iRODS links
- Reduce unnecessary iRODS connections
- Upgrade project and requirements for SODAR Core v0.4.3
- Cleanup and refactoring to match SODAR Core v0.4.3
- Remove most local JS/CSS includes
- Reformat using Black


v0.4.1 (2018-12-19)
===================

Minor update and bug fix release.

- Upgrade site to SODAR Core v0.4.0
- Remove local filesfolders app, import from SODAR Core
- Improve alternative material name search
- Optimize iRODS file search
- Secure SODAR Taskflow API views


v0.4.0 (2018-10-26)
===================

Update for integrating SODAR with SODAR Core.

- Site now based on SODAR Core v0.3.0
- Add remote project metadata synchronization from SODAR Core
- Remove formerly local apps now provided by SODAR Core (most notably
  projectroles and timeline)
- Finalize rebranding project to SODAR


v0.3.3 (2018-09-25)
===================

Update adding an app for cancer study shortcuts in samplesheets.

- Add cancer study app
- Refactor germline study app
- Add general samplesheets helpers and utilities


v0.3.2 (2018-09-11)
===================

Minor bug fix and documentation update.

- Add BIH Proteomics data transfer docs (from Mathias Kuhring)
- Fix ISAtab replacing failure if encountering an error in the investigation
  file
- Fix dropdown menu overflow issue in certain tables


v0.3.1 (2018-08-24)
===================

Release for app ui/functionality updates and fixes for v0.3.0.

- Optional automated unpacking for zip archives in Small Files
- Option for validating landing zone files without moving
- Major improvements in iRODS file querying and irodsbackend API
- Redesigned search view
- Search for iRODS files
- External ID display and annotation for samples
- Samplesheets layout improvements
- Enable using content apps for multiple assay types
- Proof-of-concept ID querying API


v0.3.0 (2018-07-03)
===================

Final v0.3.0 release.

- Rebrand site as SODAR
- Separate config apps into study and sample sub-apps in samplesheets
- Add special configuration sub-apps to landingzones
- Improve iRODS links and file navigation
- Add a Sphinx-based user manual
- Add IGV session creation for germline projects


v0.3.0b (2018-06-05)
====================

Beta v0.3.0 release.

- iRODS integration (with omics_taskflow v0.2.0b)
- Landing Zones app added for managing file uploads in iRODS
- Add sample sheet configuration specific sub-apps, bih_germline as a demo case
- Irodsinfo app for configuring iRODS connection


v0.2.0 (2018-04-13)
===================

Release for v0.2 milestone.

- Add new samplesheets app with ISAtab support
- New URL scheme using object UUIDs
- Remove "project staff" role


v0.1 (2018-01-26)
=================

Initial release adapted from the Omics Data Access prototype.
