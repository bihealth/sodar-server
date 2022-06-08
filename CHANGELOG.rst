SODAR Changelog
^^^^^^^^^^^^^^^

Changelog for the SODAR project. Loosely follows the
`Keep a Changelog <http://keepachangelog.com/en/1.0.0/>`_ guidelines.

Note that the issue IDs here refer to ones in the private CUBI GitLab.


Unreleased
==========

Changed
-------

- **General**
    - Upgrade to django-sodar-core v0.10.13-WIP (#1391, #1406, #1418)
    - Upgrade to black v22.3.0 (sodar_core#972)
    - Default ``BASICAUTH_REALM`` message (#1410)
    - Add ``LocalAuthAPIView`` URL to ``SECURE_REDIRECT_EXEMPT`` (#1411)
    - Rename default iRODS zone into ``sodarZone`` (#1417)
    - Manual updates (#1386, #1387, #1408)
    - Combine development documentation into manual (#1345)
- **Samplesheets**
    - Update Vue app browserslist (#1424)

Fixed
-----

- **General**
    - ``build-docker.sh`` failing with special characters in tag name (#1385)
- **Irodsinfo**
    - Info page title (#1416)
- **Samplesheets**
    - Unset study protocol export ordering (#1419)
    - Bootstrap tooltip issues in sheet tables (#1415)

Removed
-------

- **General**
    - Login page user domain autofill (#1409)
    - Custom login template (#1409)
    - Separate development documentation (#1345)


v0.11.2 (2022-03-04)
====================

Added
-----

- **General**
    - ``.readthedocs.yaml`` file (#1362)
- **Samplesheets**
    - ``Investigation.get_assays()`` helper (#1359)
    - View tests for search (#556)

Changed
-------

- **General**
    - Upgrade to django-sodar-core v0.10.10 (#1361, #1376)
    - Link manual to readthedocs.io (#1358)
    - Upgrade to python-irodsclient v1.1.2 (#1389)
- **Landingzones**
    - Make ``description`` optional in ``_make_landing_zone()`` (#1360)
- **Samplesheets**
    - Allow replacing sheets if unfinished landing zones exist (#1356)
    - Update project list file column legend (#1366)
    - Upgrade Vue app dependencies (#1369)
    - Upgrade Vue app to ag-grid v27 (#1370)
    - Improve search results layout (#1373)

Fixed
-----

- **General**
    - Invalid Python version in readthedocs build (#1362)
- **Landingzones**
    - Zone list title column layout issues (#1380)
- **Samplesheets**
    - ``LandingZone`` objects deleted by API sheet replacing (#1356)
    - Invalid ``Investigation`` timeline object reference for sheet replacing (#1357)
    - ``IrodsStatsBadge`` query error handling (#1371)
    - Keyword ``type:file`` not limiting search (#1374)
    - Redundant iRODS connections in search result rendering (#1375)
    - Tooltip hide not working in ontology column config (#1379)

Removed
-------

- **General**
    - Local manual build (#1358)
- **Landingzones**
    - Unused ``sodar-popup-overlay`` elements from ``project_zones.html`` (#1363)


v0.11.1 (2022-02-04)
====================

Added
-----

- **Irodsbackend**
    - ``format_env()`` helper for iRODS environments (#1351)
- **Irodsinfo**
    - Use ``IRODS_HOST_FQDN`` for client environment and display (#1349)
- **Samplesheets**
    - Toggle WebDAV IGV proxy with ``IRODS_WEBDAV_IGV_PROXY`` (#1324)

Changed
-------

- **General**
    - Upgrade minimum Python version to v3.8, add v3.10 support (sodar_core#885)
    - Upgrade to django-sodar-core v0.10.8 (#1337)
    - Upgrade Python dependencies (#673, #1337, #1348, sodar_core#884, sodar_core#901, sodar_core#902)
    - Upgrade to Chromedriver v97 (sodar_core#905)
- **Samplesheets**
    - Upgrade Vue app dependencies (#1330)

Fixed
-----

- **General**
    - Manual building in readthedocs (#1343)
- **Irodsinfo**
    - Invalid value formats in iRODS environment generation (#1351)
- **Ontologyaccess**
    - Opening OWL data for parsing not working for specific URLs (#1352)


v0.11.0 (2021-12-16)
====================

Added
-----

- **General**
    - Siteinfo app in default ``LOGGING_APPS`` value (#1219)
    - ``LOGGING_LEVEL`` setting (sodar_core#822)
    - ``PROJECTROLES_EMAIL_HEADER`` and ``PROJECTROLES_EMAIL_FOOTER`` settings (#1231)
    - Codacy coverage reporting (#1169)
- **Irodsbackend**
    - ``colls`` parameter in list retrieval (#1156)
    - ``IRODS_ENV_DEFAULT`` setting (#1260)
    - ``LocalAuthAPIView`` REST API view and ``IRODS_SODAR_AUTH`` setting (#1263)
- **Landingzones**
    - ``busyzones`` management command (#1212, #1314)
    - App alerts for sheet cache updates (#1000)
    - App alerts for zone owner for zone actions (#1204, #1240)
    - ``member_notify_move`` app setting (#1203)
    - Project member notifications from zone moving (#1203, #1232)
    - ``LandingZone.user_message`` field (#1203)
    - ``finished`` parameter for ``LandingZoneListAPIView`` (#1234)
    - ``LandingZone.is_locked()`` helper (#321)
    - Zone locked status in UI and ``LandingZoneRetrieveAPIView`` (#321)
    - Display collections in iRODS file list (#1156)
    - UI documentation in user manual (#1181)
- **Ontologyaccess**
    - App documentation in user manual (#1301)
- **Samplesheets**
    - Simple link support for string cell rendering (#1001)
    - ``generic_raw`` assay plugin (#1128)
    - Overriding assay plugin via assay comment (#1128)
    - App alerts for sheet cache updates (#1000, #1265)
    - Tooltip to clarify the Finish Editing button (#1109)
    - Tooltips for buttons disabled due to an unsaved row (#1056)
    - Default ontology column value (#1061)
    - Confirmation for field value overwrite on node rename (#1060)
    - Sheet version description (#754)
    - Batch sheet version deletion (#773)
    - Assay app support for "transcriptome profiling" measurement type (#1255)
    - Saving version with description in editor UI (#1109)
    - Automatic study/assay table filtering from search results (#634)
    - UI documentation in user manual (#1180)

Changed
-------

- **General**
    - Upgrade to django-sodar-core v0.10.7 (#1217, #1220, #1243, #1272, #1332)
    - Upgrade to python-irodsclient v1.0.0 (#1223)
    - Upgrade to Chromedriver v96 (sodar_core#772, #1254, sodar_core#847, sodar_core#852)
    - Upgrade to Node v12
    - Improve production logging (#1257)
    - Upgrade to django-webpack-loader v1.4.1 (#1198)
    - Upgrade to redis v3.5.3 (#1297)
    - Use ``ManagementCommandLogger`` for command output (#1276)
    - Update user manual (#1304, #1318)
    - Replace deprecated ``MAINTAINER`` label in Dockerfile (#1316)
    - Enable setting ``SECURE_REDIRECT_EXEMPT`` in env vars (#1331)
- **Irodsbackend**
    - Retrieve iRODS config from ``IRODS_ENV_BACKEND`` setting (#1221)
    - Use data attributes in templates (sodar_core#530)
    - Rename ``data_objects`` to ``irods_data`` in return data (#1156)
    - Get default iRODS environment values from default env (#1260)
- **Irodsinfo**
    - Retrieve iRODS config from ``IRODS_ENV_CLIENT`` setting (#1221)
    - Display ``IRODS_ENV_CLIENT`` in siteinfo via ``info_settings``
    - Get default iRODS environment values from default env (#1260)
- **Landingzones**
    - Do not load finished landing zones in zone list view (#1205)
    - Rename ``STATUS_ALLOW_CLEAR`` to ``STATUS_FINISHED`` (#1205)
    - UI improvements in project zone list (#1235)
    - Hide zones with ``NOT CREATED`` status from detail card (#1236)
    - Handle ``NOT CREATED`` landing zone status (#1237)
    - Use ``CurrentUserFormMixin`` in forms (#660)
    - Enable automated collection generation by default in UI (#1266)
    - Clarify collection creation message in UI (#1275)
    - Default status info for ``MOVING`` (#1305)
    - Do not count inactive zones in project list (#1306)
- **Samplesheets**
    - Move ``TestSheetSyncBase`` into ``test_views_taskflow``
    - Update app setting labels (#1230)
    - Use ``CurrentUserFormMixin`` in forms (#660)
    - Rename ``get_name()`` and ``get_full_name()`` in ``ISATab`` model (#1247)
    - Update sheet version list layout (#1246)
    - Replace version compare menu with operation dropdown entry (#1251)
    - Update subpage navigation (#1252)
    - General refactoring (#1248, #1250, #1253)
    - Move Ajax view version saving to ``SheetVersionMixin`` (#1109)
    - Use ``AppSettingAPI.delete_setting()`` for display config deletion (#854)
    - Make UI specific data optional in ``build_study_tables()`` (#694)
    - Do not require user for ``sheet_sync_task`` (#1273)
    - Hide navigation dropdown if no sheets are available (#1285)
    - Reverse import/create order in Sheet Operations dropdown (#1286)
    - Improve ontology editor layout (#1293)
    - Improve study and assay title layout (#1291)
    - Improve iRODS access ticket list layout (#1302)
    - Remote sheet sync refactoring (#1317, #1325, #1326)
    - Upgrade Vue app dependencies (#1328, #1329)

Fixed
-----

- **General**
    - API version settings not updated (#1218)
    - Disable cache as workaround for Docker build issues (#1225)
    - Github Actions CI failure by old package version (sodar_core#821)
    - Build warning in ``docs_dev`` (#1182)
- **Irodsadmin**
    - Missing cleanup in command test ``tearDown()`` (#1244)
- **Irodsbackend**
    - Redundant slash prefix for root level items in collection list (#1245)
    - ``IRODS_ENV_BACKEND`` value conversion issues (#1259)
    - Unavailable iRODS connection not handled in ``BaseIrodsAjaxView`` (#1322)
- **Landingzones**
    - ``PROJECTROLES_SEND_EMAIL`` not checked in Taskflow views (#1229)
    - Collection hint alert from zone list UI (#1266)
    - Zone move failure on Celery task crash in ``TaskflowZoneStatusSetAPIView`` (#1298)
    - ``status_info`` overflow crash in ``TaskflowZoneStatusSetAPIView`` (#1307)
    - Uncaught exceptions in ``inactivezones`` (#1311)
- **Ontologyaccess**
    - Minor layout issues (#1312)
- **Samplesheets**
    - Missing label for ``public_access_ticket`` app setting (#1230)
    - Incorrect ``ISATab`` timestamp in export and compare dropdown (#1247)
    - Unhandled backend exceptions in ``update_project_cache_task()`` (#1265)
    - Vue app study navigation failure with additional URL params (#1269)
    - Assay shortcut card extra link icons (#1271)
    - Source map errors in production (#1198)
    - Numeric column default value invalid if range is unset (#1281)
    - ``ColumnToggleModal`` errors on entering/exiting edit mode (#1280)
    - Editability not updated in ``ColumnToggleModal`` without grid reload (#1279)
    - First column width breaking in Parser Warnings table (#1287)
    - Template creation link visible in sheet replace form (#1288)
    - Default suffix icon in ``ColumnConfigModal`` (#1290)
    - Ontology editor edit/check button icon misalignment (#1292)
    - iRODS file list modal button column alignment (#1299)
    - Random crash in ``StudyShortcutsRenderer`` unit tests (#1294)
    - Sheet import and create view access permitted with sheet sync enabled (#1309)
    - Project list sheet import link visible with sheet sync enabled (#1309)
    - No placeholder for missing investigation title in details card (#1313)

Removed
-------

- **General**
    - ``ADMIN_URL`` setting from ``production.py`` (#1228)
- **Irodsbackend**
    - ``IRODS_ENV_PATH`` setting (#1221)
- **Irodsinfo**
    - ``IRODSINFO_ENV_PATH`` setting (#1221)
    - ``IRODSINFO_SSL_VERIFY`` setting (#1226)
- **Landingzones**
    - ``ZoneClearView`` UI view (#1205)
    - ``_list_buttons.html`` template (#1205)
- **Samplesheets**
    - ``SampleSheetVersionCompareForm`` (#1251)
    - Unused ``config`` argument from ``SampleSheetIO.save_isa()``
    - Unused ``basic_val`` arg from ``_add_cell()`` (#1262)


v0.10.1 (2021-07-07)
====================

Added
-----

- **General**
    - ``LABEL`` and ``MAINTAINER`` in ``Dockerfile`` (#1186)
    - Manual building in Docker setup (#1195)
    - SAML configuration (#990)
    - ``LOGGING_APPS`` and ``LOGGING_FILE_PATH`` Django settings (#1209)

Changed
-------

- **General**
    - Upgrade to django-sodar-core v0.10.3 (#1201)
    - Allow modifying all relevant SODAR Django settings from env
- **Samplesheets**
    - Upgrade vue app dependencies (#1185)
    - Refactor vue app code and tests for new dependencies (#1185)
    - Preserve line breaks in parser warnings (#1188)
    - Move ``DEFAULT_EXTERNAL_LINK_LABELS`` to ``constants``

Fixed
-----

- **General**
    - Docker entry points for Celery and Celerybeat (#1193)
    - Docker image build issues (#1194)
    - Missing migrations for ``JSONField`` and site (#1196)
    - ``irodsadmin`` debug logging disabled (#1209)
    - Manual layout broken by ``docutils>=0.17`` (#1210)
- **Samplesheets**
    - Loading icon in vue app iRODS status badge (#1192)
    - Workaround for Webpack source map file crash (#1198)


v0.10.0 (2021-06-11)
====================

Added
-----

- **General**
    - Release notes and changelog sections in manual (#1098)
    - ``setup_database.sh`` from SODAR Core
    - Enable ``appalerts`` app (#1124)
    - Display relevant Django settings values in ``siteinfo`` app (#1123)
    - ``taskflowbackend`` in site logging (#1137)
    - New Docker setup (#1129, #1163, #1165)
    - GitHub Actions CI (#1033)
    - iRODS study and assay data linking documentation in manual (#1127)
- **Irodsbackend**
    - Support for ``IRODS_ROOT_PATH`` setting (#1067)
    - ``get_root_path()`` and ``get_projects_path()`` helpers (#1067)
    - Optional ``user_name`` and ``user_pass`` in ``IrodsAPI`` init kwargs (#1139)
    - Public guest access support for Ajax queries (#1140, #1144)
- **Landingzones**
    - Optional automated creation of expected zone collections (#391)
    - ``_assert_zone_coll()`` helper in ``LandingZoneTaskflowMixin``
- **Samplesheets**
    - Warning for unrecognized assay plugin in sample sheet import (#1070)
    - Sheet creation from templates using cubi-tk (#1068)
    - ``clean_sheet_dir_name()`` helper
    - iRODS delete requests for data objects and collections (#277, #1087, #1089, #1090, #1093, #1134)
    - Allow per-project restriction of column config updates (#995)
    - Diff comparison for sheet versions (#1007, #1110, #1117)
    - Enable remote sync for sample sheets (#959, #1102, #1103)
    - ``Icon`` component in vue app for django-iconify icon access (#1113)
    - App alerts for iRODS data request actions (#1084)
    - Public guest access support for sample data (#1100)
    - ``get_webdav_url()`` helper (#1100)
    - ``view_versions`` permission (#1138)
    - Management command tests (#1170)

Changed
-------

- **General**
    - Upgrade to django-sodar-core v0.10.2 (#1096, #1113, #1118, #1121, #1135, #1158, #1166)
    - Upgrade to Python v3.8 and Django v3.2 (#1113)
    - Update project icons (#1113, #1125, #1154)
    - Unify ISA-Tab naming (#1082)
    - Upgrade to Chromedriver v90 (sodar_core#731)
    - Upgrade to altamISA v0.2.9 (#1099, #1106)
    - Upgrade versioneer
    - Upgrade general python dependencies (#1112)
    - Update taskflow actions for SODAR Taskflow v0.5 compatibility
    - Cleanup for public GitHub release (#1119)
- **Irodsbackend**
    - Split long queries in ``get_objs_recursively()`` (#1132)
    - Refactor Ajax views (#841)
    - Require ``project`` and ``user`` args for ``get_webdav_url()`` template tag (#1144)
- **Irodsinfo**
    - Move iRODS connecting guide into the user manual (#262)
- **Samplesheets**
    - Fail gracefully for ISAtab import with empty tables (#903, #1075)
    - Implement study/assay app retrieval in model ``get_plugin()`` helpers (#1076)
    - Change timeline event names for sheet import/create/replace (#1079)
    - Refactor and simplify view pagination settings
    - Provide sodar context alert data as HTML instead of string (#1089)
    - Unify iRODS URL patterns (#1086)
    - Duplicate ``sodar_uuid`` views in REST API nested lists (#1074)
    - Unify subpage navigation (#1085)
    - Reorder critical warning check and render test in sheet import (#1107)
    - Upgrade Vue app dependencies (#1114)
    - Rename ``IrodsCollsCreateView``
    - Enable public guest access to project sheets view (#1141)
    - Enable sheet export for project guests (#1138)
    - Enable sheet version viewing and export for project guests (#1138)
    - Allow no user in ``update_project_cache_task()`` (#1171)
    - Use logging in ``syncnames`` (#1170)

Fixed
-----

- **General**
    - Production config requirement in ``docs_manual``
- **Irodsadmin**
    - Irodsorphans project UUID not returned if path ends in project UUID (#1071)
- **Irodsbackend**
    - Long queries raising ``CAT_SQL_ERR`` in iRODS (#1132)
    - Redundant iRODS connection opened by ``_check_collection_perm()`` (#1142)
    - Missing permission check in ``IrodsStatisticsAjaxView`` ``POST`` request (#1143)
- **Irodsinfo**
    - Server status card layout on low resolutions (#1176)
- **Landingzones**
    - Root level backend plugin retrieval in template tags
    - CSS in project zone list (#1027)
    - Uncaught irodsbackend exceptions in ``TriggerZoneMoveTask`` (#1148)
    - Project list column retrieval failing with anonymous user (#1155)
    - Inactive zones deleted from all projects on zone clear (#1150)
- **Samplesheets**
    - MaxQuant results not correctly linked in ``pep_ms`` assay app (#1072)
    - Incorrect timeline event for ``sheet_create`` (#1080)
    - Assay shortcut card layout breaking on Chrome (#1094)
    - Node names not properly sanitized on sheet import (#798)
    - Root level backend plugin retrieval in template tags

Removed
-------

- **General**
    - Legacy ``raven`` dependency (#1147)
    - References to unused ``django-db-file-storage`` component (#1153)
    - Legacy Docker setup (#1129)
    - ``syncgroups`` user command, updated version found in ``projectroles`` (#1172)
    - Unused ``sodar.users.utils`` (#1172)
    - Unused ``.travis.yml``
    - ``backports.lzma`` dependency (#1197)
- **Irodsbackend**
    - Support for Ajax queries without project
    - Unused template tags ``get_webdav_url_anon()`` and ``get_webdav_user_anon()``
    - ``is_webdav_enabled()`` template tag, use ``get_django_setting()`` instead
- **Samplesheets**
    - ``find_study_plugin()`` helper, use ``Study.get_plugin()`` instead (#1076)
    - ``find_assay_plugin()`` helper, use ``Assay.get_plugin()`` instead (#1076)


v0.9.0 (2021-02-05)
===================

Added
-----

- **General**
    - Missing user model migration
    - ``Makefile`` for selected management commands (#989)
- **Irodsadmin**
    - Add app for iRODS data administration (#972)
    - ``irodsorphans`` management command (#972, #997, #1035, #1045)
- **Irodsbackend**
    - ``get_query()`` helper for ``SpecificQuery`` initialization (#1003)
    - Support for multi-term search (#1065)
- **Landingzones**
    - Zone UUID clipboard copying link (#970)
    - ``inactivezones`` management command (#1010, #1046)
- **Ontologyaccess**
    - Add site app for ontology storage and access (#937, #947)
    - ``importobo`` and ``importomim`` management commands (#937, #980)
    - ``ontologyaccess_backend`` backend plugin (#958)
- **Samplesheets**
    - ``microarray`` assay app (#941)
    - ``_update_cache_rows()`` helper for assay app plugins (#954)
    - ``NodeMixin`` for node field/header helpers (#922)
    - Ontology term editing (#688, #699)
    - Extract label editing as string (#964)
    - Simple editing for external links columns (#976)
    - ``SampleDataFileExistsAPIView`` for querying file status by checksum (#1003)
    - Track hub and iRODS ticket support for UCSC Genome Browser integration (#238)
    - Django setting ``SHEETS_ONTOLOGY_URL_SKIP`` for template skip patterns (#1022)
    - Support for multi-term search (#1065)

Changed
-------

- **General**
    - Upgrade to altamISA v0.2.7
    - Upgrade to Bootstrap v4.5.3 and jQuery v3.5.1 (#1011)
    - Upgrade to Chromedriver v87
    - Upgrade to python-irodsclient v0.8.6 (#1009, #1058)
    - Upgrade to django-sodar-core v0.9.0 (#1051)
    - Refactor ``Project.get_full_title()`` usage (#1062)
    - Update iRODS install instructions in ``docs_dev`` (#1028)
- **Irodsbackend**
    - Standardize Ajax view output (#841)
    - Support ``name_like`` as a list in ``get_objs_recursively()`` (#1065)
- **Irodsinfo**
    - Update iCommands instructions (#1028)
- **Samplesheets**
    - Display assay plugin icon for all users with sheet edit permissions (#940)
    - Refactor assay row cache updating (#954)
    - Refactor ontology value rendering (#693)
    - Move ``ATTR_HEADER_MAP`` to ``models``
    - Refactor recognizing ontology/unit columns in rendering (#962)
    - Disable "Finish Editing" link with unsaved rows (#987)
    - General vue app refactoring (#747)
    - Prevent insertion of identical rows (#1023)
    - Move iRODS content setup for ajax views to ``plugins.get_irods_content()``
    - Rename Ajax views and standardize output (#857, #858)
    - Change default value of ``allow_editing`` to ``True`` (#1069)

Fixed
-----

- **General**
    - Missing raven dependency in production config (#1048)
- **Samplesheets**
    - Assay iRODS links enabled if null path is returned by assay app (#951)
    - Empty ontology/unit column type not recognized in rendering (#962)
    - Legacy ``field`` header type still in use
    - Row insert failing if the last node is a process (#974, #975)
    - Row insert failing with single column source node (#965, #986)
    - Sample deleted from study not removed from assay sample selection (#988)
    - Default value in column config not validated against range (#1031)
    - Editor input not correctly trimmed (#1032)
    - Icon updating on row deletion cancel (#1012)
    - Ontology URL template forced on incompatible accession URLs (#1022)
    - Redundant iRODS queries for empty paths in ``_update_cache_rows()`` (#957)
    - Saving multi-column node for a new row using default suffix (#1040)
    - ``UNIT`` column type override if empty unit given in config (#1052)
    - Column config copy/paste enabled for contact, date and external links (#1053)
    - Incompatible format not handle in column config paste (#1029)

Removed
-------

- **General**
    - Management commands replaced by ``Makefile`` (#989)
- **Irodsbackend**
    - ``_get_obj_list()`` and ``_get_obj_stats()`` helpers (#1066)
- **Samplesheets**
    - Workarounds for legacy sample sheet imports (#946)


v0.8.0 (2020-09-15)
===================

Added
-----

- **General**
    - Celery beat setup (#702)
    - Configuration of support contact info in footer via site settings (#863)
- **Landingzones**
    - Automated triggering of landing zone validation/moving by iRODS file (#702)
- **Samplesheets**
    - ISAtab export through the REST API via ``SampleSheetISAExportAPIView`` (#849, #851)
    - Sample sheet column display configuration saving (#539)
    - Material and process renaming (#852)
    - Study and assay iRODS paths in ``InvestigationRetrieveAPIView`` (#895)
    - Protocol selection (#871)
    - Editing of performer, perform date and contacts (#881)
    - Editing of non-ontology list values (#886)
    - Display ``name_type`` for processes
    - Set default protocol automatically in edit config (#879)
    - Row insertion (#834)
    - Row deletion (#868)
    - Sheet config versioning (#904)
    - Automated rebuilding of expired sheet configs (#904)
    - Node name suffix config and automated filling (#912, #925)
    - ``get_node_obj()`` helper (#922)
    - Update sheet config default protocols on sheet restore (#901)
    - Export unarchiving notification for Windows users (#894)

Changed
-------

- **General**
    - Upgrade to django-sodar-core v0.8.3-WIP
    - Move ISAtab export functionality to ``SampleSheetISAExportMixin`` (#849)
    - Upgrade to Chromedriver v85 (sodar_core#569)
- **Irodsbackend**
    - Improve connection error logging
- **Irodsinfo**
    - Improve iRODS server/backend status (#908, #909)
- **Landingzones**
    - Refactor zone modification mixins in ``landingzones.views``
- **Samplesheets**
    - Re-initialize Vue app with Vue-CLI v4 (#837)
    - Partial refactoring and cleanup of Vue app code (#537, #837)
    - Always store original header name in table rendering
    - Allow column config editing with ``edit_sheet`` permission (#880)
    - Allow empty ``DATA`` material names in editing (#898)
    - Refactor helpers in ``SampleSheetTableBuilder``
    - Refactor sheet config helpers into ``SheetConfigAPI`` (#905)
    - Include top header in column width estimation for rendering (#649)
    - Use node header for recognizing unit enabled columns without data (#914)
    - Prevent simultaneous editing of cells in multiple tables (#765)
    - Preserve display configs on sheet replace if headers match (#906, #933)

Fixed
-----

- **General**
    - Hardcoded plugin settings in ``production`` config (#910)
- **Samplesheets**
    - Row sorting not working with updated column type definitions (#847)
    - Lists of strings assigned ``ONTOLOGY`` column type in rendering (#885)
    - Last single column node not visible in ``ColumnToggleModal`` (#877)
    - Column config update randomly breaking table rendering (#850)
    - Whole cell copying active when in cell edit mode (#882)
    - File link CSS in edit mode (#896)
    - Data material name regex not accepting common file name characters (#875)
    - Incorrect padding for edit button in field header CSS (#862)
    - Prevent user for enabling unit for columns where it isn't supported (#889)
    - Keyboard event handling issues in ``DataCellEditor`` (#690, #917, #919)
    - Do not look for iRODS link columns in vue app if in edit mode (#866)
    - Contact column width estimation (#887)

Removed
-------

- **General**
    - Unused ``Pillow`` dependency (sodar_core#575)


v0.7.1 (2020-04-27)
===================

Added
-----

- **Samplesheets**
    - ``IrodsCollsCreateAPIView`` for iRODS collections creation via API (#826)
    - Host name input confirmation for sample sheet and data deletion (#833)
    - ``SampleSheetImportAPIView`` for ISAtab import via REST API (#802)
    - Study identifier display in Overview (#791)
    - Pagination in sheet version list (#743)
- **Tokens**
    - Enable app from django-sodar-core v0.8.0+ (#822)

Changed
-------

- **General**
    - Upgrade to Django v1.11.29
    - Upgrade to django-sodar-core v0.8.1 (#835, #845)
    - Upgrade Python requirements to match djagno-sodar-core v0.8.0 (#835)
    - Upgrade to Chromedriver v80
    - Rename references to iRODS collections (#785)
    - Rename ``IRODS_SAMPLE_COLL`` and ``IRODS_LANDING_ZONE_COLL`` settings (#785)
    - Rename the ``samplesheets.create_colls`` permission (#785)
    - Use base Ajax API view classes from SODAR Core (#805)
- **Landingzones**
    - Disallow replacing sample sheets if active landing zones exist (#713)
    - Display moved and deleted zones of other users with ``view_zones_all`` perm (#806)
    - Return landing zone iRODS path on creation (#843)
    - Use ``SODARUserSerializer`` in ``LandingZoneSerializer`` (#842)
- **Samplesheets**
    - Upgrade non-breaking Vue app dependencies (#836)
    - Reorganize views and URL patterns (#801)
    - Refactor Ajax views and URL patterns (#736, #824)
    - Improve sheet import logging (#832)
    - Move ISAtab Zip archive validation to ``SampleSheetIO.get_zip_file()``
    - Move ISAtab multi-file reading to ``SampleSheetIO.get_isa_from_files()``
    - Refactor ``SampleSheetImportMixin`` to work with API views
    - Hide path from sheet configuration information (#779)
    - Improve notation for missing study shortcut file types (#799)
    - Temporarily disable Bootstrap tooltips in custom project list cells (#787)

Fixed
-----

- **Irodsbackend**
    - Ajax view permission checking and status codes
    - Hardcoded time zone reference in ``api._get_datetime()`` (#807)
- **Landingzones**
    - REST API view permission checks not working with Knox token auth (#823)
    - Title suffix not optional in ``LandingZone`` serializer (#825)
    - Initial workaround for active landing zone deletion on sheet replace (#713)
- **Samplesheets**
    - REST API view permission checks not working with Knox token auth (#823)
    - Crashes caused by sheet config not correctly updated on sheet replace (#829)
    - Sample sheet version saved for unsuccessful replace (#838)
    - Editor select box padding for Firefox and Chrome (#726)
    - CSS issue with ``sodar-list-btn`` and Chrome (#844, sodar_core#529)

Removed
-------

- **General**
    - Unused ``django-db-file-storage`` requirement
- **Samplesheets**
    - Unused ``models.get_zone_dir()`` and ``io.get_assay_dirs()`` helpers
    - Base API view classes moved to SODAR Core (#800)
    - Unneeded ``SheetSubmitBaseAPIView`` base class


v0.7.0 (2020-02-12)
===================

Added
-----

- **General**
    - Support for local third party JS/CSS includes (#770)
    - Sentry support (#476)
    - ``ENABLE_IRODS`` Django setting (#796)
- **Irodsbackend**
    - Enforce MD5 hash scheme in client configuration (#740)
    - Enable ``conn`` keyword argument in API initialization (#793)
- **Landingzones**
    - Extra columns for project list (#579)
    - Missing permission and view tests
    - Initial REST API (#780)
- **Samplesheets**
    - Editing of selected sample sheet column values (#550)
    - Project settings for sample sheet configuration (#687)
    - ``manage_sheet`` permission (#696)
    - Column management UI for sample sheet configuring (#698)
    - ``get_name()`` helper in ``ISATab``
    - Saved sample sheet version browsing and deletion (#662)
    - Sample sheet version export (#739)
    - Sample sheet version restoring (#701)
    - Save and restore sheet configuration with ``ISATab`` version
    - Deletion of ``ISATab`` versions on sheet delete (#746)
    - Extra columns for project list (#579)
    - ``MiscFiles`` assay shortcut for all assays (#766)
    - ``ResultsReports`` assay shortcut for all assays (#767)
    - Investigation info retrieval API view (#780)
    - ``utils.get_top_header()`` helper (#817)
    - Linking for metabolite assignment files in ``meta_ms`` assay app (#817)
    - Hack for "Report File" column file linking (#817)

Changed
-------

- **General**
    - Upgrade to django-sodar-core v0.7.2
    - Upgrade to python-irodsclient v0.8.2 (#731)
    - Upgrade to altamISA v0.2.6
    - Upgrade to Chromedriver v79
    - Upgrade to Django v1.11.27
    - Enable logging propagation (#792)
    - Only log ``ERROR`` level messages if not in debug mode (#526)
- **Irodsbackend**
    - Refactor ``api.get_info()``
    - Refactor iRODS connection handling in API (#793)
- **Irodsinfo**
    - Display iRODS server information when connection fails (#761)
- **Landingzones**
    - Prevent opening unnecessary iRODS connections with irodsbackend API (#796)
    - Reorganize views and URL patterns (#801)
- **Samplesheets**
    - Rename ``table_data`` member to ``tables`` in rendered table data (#219)
    - Move ``_get_isatab_files()`` and ``_fail_isa()`` into ``SampleSheetIOMixin``
    - Refactor ``utils.get_index_by_header()``
    - Replace ``v-clipboard`` package with ``vue-clipboard2`` (#719)
    - Move UI notifications to ``NotifyBadge.vue`` (#718)
    - Refactor column data retrieval in ``ColumnToggleModal`` (#710)
    - Rename ``getGridOptions()`` to ``initGridOptions()`` (#721)
    - Dynamically add/omit cell unit, link and tooltip in rendering (#708)
    - Improve column type detection (#730)
    - Refactor sample sheet import/replace handling in views (#701)
    - Replace extra content table with standard assay shortcut table (#782)
    - Change assay sub-app ``get_extra_table()`` into ``get_shortcuts()`` (#782)
    - Change ``ExtraContentTable.vue`` into ``AssayShortcutCard.vue`` (#782)
    - Prevent opening unnecessary iRODS connections with irodsbackend API (#796)
    - Remove file suffix restriction from assay app data file linking (#817)

Fixed
-----

- **Irodsbackend**
    - Cleanup skipped by uncaught exceptions in ``init_irods()`` (#723)
    - Data object replicates included in file and stats queries (#722)
- **Landingzones**
    - Cache update initiated synchronously in TaskflowZoneStatusSetAPIView (#783)
    - Missing zone status checks in zone deletion/moving views (#813)
- **Samplesheets**
    - ``getGridOptionsByUuid()`` returned column API instead of grid options (#706)
    - ``getGridOptionsByUuid()`` returned initial options without applied updates (#721)
    - Incorrect Investigation UUID passed to ``ISATab`` on replace (#742)
    - Restrictive tooltip boundary value in ``IrodsButtons.vue``
    - Study UUID changed if modifying study identifier when replacing sheets (#789)

Removed
-------

- **General**
    - Unused raven requirement (#476)
- **Filesfolders**
    - Remove app as files will be placed under ``MiscFiles`` in iRODS (#766)
- **Irodsbackend**
    - ``test_connection()`` helper (#795)
- **Samplesheets**
    - Unused ``study_row_limit`` setting (#641)
    - Support for SODAR v0.5.1 parsing of characteristics lists (#619)
    - Support for old style comments parsing (#631)
    - Redundant ``columnValues`` structure (#711)
    - ``link_file``, ``num_col`` and ``align`` parameters from rendering (#708)
    - ``get_assay_list_url()`` template tag (#737)
    - Unused ``SourceIDQueryAPIView`` and related classes (#820)


v0.6.1 (2019-11-15)
===================

Added
-----

- **Irodsbackend**
    - Supply optional iRODS options in environment file (#714)
    - ``IRODS_ENV_PATH`` settings variable (#714)
- **Irodsinfo**
    - Supply optional iRODS options in environment file (#717)
    - ``IRODSINFO_ENV_PATH`` settings variable (#717)
    - Logging for environment generating and certificate loading

Changed
-------

- **Irodsbackend**
    - Enable reading ``IRODS_CERT_PATH`` from environment variables
    - Improve connection logging
    - Refactor ``api.test_connection()`` (#715)

Fixed
-----

- **Landingzones**
    - Misleading alert text in ``landingzone_confirm_move.html`` (#689)
- **Samplesheets**
    - Initial study context sorted by title instead of parsing order (#692)
    - Rendering crash from missing value type check for units (#697)


v0.6.0 (2019-10-21)
===================

Added
-----

- **General**
    - Missing Celery broker URL in ``env.example`` (#607)
- **Samplesheets**
    - ISAtab export (#95)
    - Model support and parsing for multiple missing ISAtab fields (#95, #581, #626)
    - ``extra_material_type`` field in ``GenericMaterial``
    - ``archive_name`` field in ``Investigation``
    - Temporary ``get_comment()`` and ``get_comments()`` helpers (#629, #631)
    - Timeline logging for import and export warnings (#639)
    - Timeline logging for failed ISAtab import (#642)
    - ``SHEETS_ALLOW_CRITICAL`` setting for handling critical import warnings (#573)
    - PacBio support in ``dna_sequencing`` assay app (#628)
    - Rendering for Assay Design REF columns (#652)
    - Rendering for First Dimension and Second Dimension columns (#652, #653)
    - Saving of original ISAtab data into the SODAR database (#651)
    - ``get_igv_irods_url()`` helper (#402)
    - IGV merge shortcuts in study links modal (#402)
    - ISAtab import from multiple uncompressed files (#593)
    - ISAtab export option for ``RemoteSheetGetAPIView`` (#670)
    - Support for ``Study`` and ``Assay`` in ``get_object_link()``
    - Timeline logging for ISAtab and Excel export
    - Assay app ``meta_ms`` for metabolite profiling / mass spectrometry (#675)
    - Ability to define alerts in context API view (#681)
    - Alert for sheets parsed with an old altamISA version (#681)

Changed
-------

- **General**
    - Upgrade site to django-sodar-core v0.7.0
    - Upgrade Python requirements to match django-sodar-core v0.7.0
    - Move graph creation dependencies to ``local_extra.txt`` (#609)
    - Move redis requirement to base.txt (#610)
    - Include backend Javascript and CSS as implemented in django-sodar-core v0.7.0 (#533)
    - Upgrade to Chromedriver v77
- **Samplesheets**
    - Color potentially dangerous links (sodar_core#64)
    - Refactor sheet cell data access and sorting (#597)
    - Upgrade Vue.js app dependencies (#580)
    - Update ISAtab importing to support altamISA v0.2+ (#617)
    - Improve characteristics list parsing (#616, #618)
    - Always import ``material_type`` field for ``GenericMaterial``
    - Do not replace title or description in ``Investigation`` if not provided
    - Display configuration in Overview as badge
    - Improve comments display in Overview (#632)
    - Refactor ``io`` module into a class (#562)
    - Suppress altamISA warnings during testing (#637)
    - Fail when encountering critical altamISA warnings in ISAtab import (#573)
    - Use file name as study/assay key in parser warning data (#644)
    - Upgrade to altamISA v0.2.5 (#676)
    - Rename and refactor ``get_igv_session_url()`` (#402)
    - Use reference table building classes from altamISA
    - Enforce ordering in ``Study.get_nodes()`` to maintain row order (#510)
    - Ignore file name when searching for germline study pedigree files (#602)
    - Replace TSV table export with Excel file export (#613)
    - Allow ``ACTIVE`` landing zones when replacing sample sheets
    - Sort displayed studies and assays by parsing order instead of file name (#683)

Fixed
-----

- **General**
    - Missing .venv ignore in Flake8 config (sodar_core#300)
    - Installation document omissions (#606)
    - Columns with integer and float values sorted lexicographically (#596)
- **Samplesheets**
    - "Sequence item 1" render error manifesting with BII-I-1 example (#620)
    - Redundant unit/value parsing for comments during import (#629)
    - Missing label for unknown configuration in Overview (#638)
    - Overview statistics table margin change (#630)
    - Leftover database objects from ISAtab import crash (#643)
    - Extract label rendering as an ontology term (#563)
    - Cache updated on sheet replace with iRODS collections not created (#622)
    - Name column rendering for Labeled Extract Name materials (#652)
    - Data File name column rendering (#652)
    - Crash in importing First Dimension and Second Dimension fields (#653)
    - Display value copied to clipboard instead of full value in multi-cell select (#521)
    - Multi-cell clipboard copying wrong cells with custom row ordering (#664)
    - Crash in search if iRODS connection fails (#680)
    - Parser warnings layout breaking with long strings (#685)

Removed
-------

- **General**
    - Unused storage requirements from production config (#610)
- **Samplesheets**
    - Reference table building classes from ``rendering.py``
    - ``write_csv_table()`` helper from ``samplesheets.utils`` (#613)


v0.5.1 (2019-07-09)
===================

Added
-----

- **Samplesheets**
    - iRODS data corruption warning in sheet replacing (#557)
    - Temporary setting ``SHEETS_ENABLE_CACHE`` to fix CI (#556)
    - ``Investigation`` model fields ``parser_version`` and ``parser_warning`` (#527)
    - Multiple new model fields to support AltamISA v0.1 API (#527)
    - ``_get_value()`` helper in rendering
    - altamISA version storing and logging in rendering (#527)
    - altamISA v0.1 validation (#527)
    - Handling of altamISA warnings (#527)
    - Helper script ``run_demo.sh`` to run in local demo mode
    - Vue.js app view for displaying parser warnings
    - Support for altamISA v0.1 column sorting (#86, #566)
    - Display comments, performer and perform date in tables
    - ``_get_ontology_url()`` helper in ``SampleSheetTableBuilder``

Changed
-------

- **General**
    - Upgrade site to django-sodar-core v0.6.2 (#569)
    - Update ``setup.py`` (#551)
- **Samplesheets**
    - Update project iRODS cache when replacing sheets (#554)
    - Use ``delete_cache()`` in ``TaskflowSheetDeleteAPIView`` (sodar_core#257)
    - Upgrade to CUBI altamISA parser v0.1 (#527)
    - Update ISAtab importing for altamISA v0.1 (#527)
    - Update models for altamISA v0.1 (#527)
    - Raise exception from parser errors when in debug mode
    - Update test ISAtab files for altamISA v0.1 (#527)
    - Refactor ``io`` module
    - Improve ``io`` module logging
    - Change ``GenericMaterial.extract_label`` into a JSON field (#527)
    - Update project iRODS cache when creating or updating iRODS collections (#565)
    - Disable operations dropdown for guest users (#497)
    - Refactor Vue.js subpage navigation
    - Refactor legacy table rendering (#111, #566)
    - Store ontology URL template in ``settings.SHEETS_ONTOLOGY_URL_TEMPLATE``
    - Align columns uniformly with cells containing integer or float values (#598)
    - Clarify "sample repository available" message on details page card (#587)

Fixed
-----

- **Samplesheets**
    - Assay UUIDs modified when replacing sheets (#554)
    - Default ``fetch()`` credentials failing with certain old browsers (#559)
    - Crash in germline study app ``get_shortcut_column()`` with empty family column (#560)
    - Germline study app ``update_cache()`` failing with empty family column
    - Sheet deletion error not displayed to user (#568)
    - Crash in ``SampleSheetStudyTablesGetAPIView`` if ``Study`` object not found (#578)
    - Leading or trailing spaces in parsed field values (#584)
    - Crash in germline study app ``get_shortcut_column()`` if IGV URL was not generated (#589)
    - Errors in ``DataCellRenderer`` trying to access unset ``renderData`` (#595)
    - Contact fields not rendered if using non-standard notation (#595)

Removed
-------

- **Samplesheets**
    - Model fields ``characteristic_cat`` and ``unit_cat`` from ``Study``
    - Model field ``header`` from ``Study`` and ``Assay``
    - Model field ``scan_name`` from ``Process``
    - Redundant warning for missing protocol reference in ISAtab import
    - Duplicate database indexes (#582)


v0.5.0 (2019-06-05)
===================

Added
-----

- **General**
    - Unsupported browser warning (#535)
- **Irodsbackend**
    - API function ``get_url()`` (#438)
    - iRODS collection path sanitizing (#488)
    - Statistics for the siteinfo app (#503)
    - API function ``test_connection()`` (#514)
- **Irodsinfo**
    - ``IRODSINFO_SSL_VERIFY`` setting for toggling SSL verification in iRODS configuration JSON (#516)
- **Landingzones**
    - Call samplesheets project cache updating after moving zone files (#508)
- **Samplesheets**
    - New Vue.js based sample sheets viewer (#426)
    - Get shortcut table data from study apps using ``get_shortcut_table()``
    - ``get_sheets_url()`` helper
    - Sodarcache iRODS file info caching for study apps (#241)
    - ``set_configuration()`` helper for unit tests
    - ``get_igv_url()`` helper in study app utils
    - ``get_study_libraries()`` helper in samplesheets.utils
    - ``get_extra_table()`` function in ``SampleSheetAssayPluginPoint``
    - ``app_name`` member in ``SampleSheetAssayPluginPoint``
    - Multi-cell selection and clipboard copying
    - Temporary manual sample sheet cache updating (#474)
    - Deletion of project samplesheets cache on sheet/data deletion (#509)
    - Temporary view ``RemoteSheetGetAPIView`` for remote sample sheet access (#388, #523)
    - UI for toggling column visibility (#466)
    - Filtering for iRODS collection list modal (#18, #467)

Changed
-------

- **General**
    - Upgrade site to django-sodar-core v0.6.0
    - Update login template to match django-sodar-core v0.6.0
- **Irodsbackend**
    - Modify stats badge appearance
    - Refactor URL arguments and URL patterns regarding query strings (#455)
    - Properly URL encode query strings (#456)
    - Always return JSON from API views (#457)
    - Update title and description in plugin
    - Rename ``get_subdir()`` into ``get_sub_path()`` (#495)
    - Disable loading backend javascript for each page (#532, sodar_core#261)
- **Landingzones**
    - Use ``get_info_link()`` for zone descriptions (#501)
    - Temporarily load ``irodsbackend.js`` by a manual include (#532, sodar_core#261)
- **Samplesheets**
    - Update and refactor server side rendering for client-side sheet UI (#426)
    - URL patterns for ``samplesheets:project_sheet`` updated for Vue.js routes (#426)
    - Refactor and update sample sheet rendering for new renderer (#111, #426)
    - Expect full table data with headers for assay app ``get_row_path()``
    - Add table data to ``get_last_material_name()`` args
    - Return iRODS path instead of Davrods URL from study app file locating helpers
    - Redesign study apps to work with Vue.js viewer (#436)
    - Display study shortcuts as link column instead of separate table (#464)
    - Do not display shortcuts in cancer study app for mass spectrometry assays (workaround for #482)
    - Move ``get_material_count()`` from views into Investigation model
    - Disable sheet replacing if active landing zones exist in the project (#525)
    - Temporarily load ``irodsbackend.js`` by a manual include in details card (#532, sodar_core#261)
    - Move TSV table generation into ``utils.write_csv_table()`` (#523)

Fixed
-----

- **Irodsbackend**
    - Exceptions raised by API for collection paths with trailing slash (#488)
    - Crash from invalid iRODS authentication in multiple locations (#514)
- **Irodsinfo**
    - Crash from invalid iRODS authentication in ``IrodsInfoView`` (#514)
- **Samplesheets**
    - Crash from certain queries if inactive ``Investigation`` objects are present for project (#544)

Removed
-------

- **Irodsinfo**
    - iRODS certificate issue workaround (#516)
- **Landingzones**
    - Unused ``get_info()`` definition in  project app plugin (#541)
- **Samplesheets**
    - DataTables sample sheet rendering (#100, #223)
    - Unused views, templates and templatetags from main and sub apps (#462)
    - Member variable ``study_template`` in ``SampleSheetStudyPluginPoint`` (#462)
    - JQuery updating in ``samplesheets.js`` (#462, #473)
    - Local DataTables includes (#462)
    - JQuery Dragscroll (#462)
    - Old "hide study columns" functionality from assay tables (#466)
    - Unused ``get_info()`` definition in  project app plugin (#541)


v0.4.6 (2019-04-25)
===================

Added
-----

- **Samplesheets**
    - Validate existence and uniqueness of study identifiers during import (#483)

Changed
-------

- **General**
    - Upgrade site to django-sodar-core v0.5.1 (#480)
    - Upgrade to ChromeDriver v74 (sodar_core#221)
- **Samplesheets**
    - Identify studies in investigation replacing by identifier instead of title (#483)

Fixed
-----

- **Samplesheets**
    - Crash in investigation replacing if study titles are not unique (#483)


v0.4.5 (2019-04-11)
===================

Fixed
-----

- **Samplesheets**
    - Hard coded WebDAV URL in IGV links (#468)
    - Add missing SODAR Core v0.5.0 settings variables (#469)


v0.4.4 (2019-04-03)
===================

Added
-----

- **Samplesheets**
    - Copying HPO term IDs into clipboard (#454)

Changed
-------

- **General**
    - Upgrade to django-sodar-core v0.5.0

Fixed
-----

- **Irodsbackend**
    - Repeated CSS overrides moved to ``irodsbackend.css`` (#452)
- **Samplesheets**
    - Tooltips broke study app table layout in small tables (#458)


v0.4.3 (2019-03-07)
===================

Added
-----

- **Irodsbackend**
    - ``IRODS_QUERY_BATCH_SIZE`` setting for batch queries (#432)
- **Samplesheets**
    - Support for multiple ontology links in ``_get_ontology_link()`` (#431)
    - Hack for providing correct HPO ontology into links (#431)
    - Rendering for HPO term links (#431)
    - Rendering for performer and perform date (#187)
    - Transcription profiling support in dna_sequencing assay app (#443)
    - Use ``IRODS_QUERY_BATCH_SIZE`` for iRODS updating (#432)
    - External link label ``x-generic-remote`` (#448)

Changed
-------

- **General**
    - Upgrade to django-sodar-core v0.4.5
- **Landingzones**
    - Secure Taskflow API views with ``BaseTaskflowAPIView`` (#435)
    - Adjust form textarea height (#437)
- **Samplesheets**
    - Improve exception reporting in ``SampleSheetTableBuilder`` (#433)
    - Secure Taskflow API views with ``BaseTaskflowAPIView`` (#435)
    - Support email link rendering for "contact" fields (#439)
    - Refactor contact field rendering (#439)
    - Query iRODS stats in batches (#432)
    - Enable iRODS buttons by default (#432)
    - Display external ID if label is not found (#449)

Fixed
-----

- **General**
    - Add missing ``.coveragerc`` excludes (#427)
- **Samplesheets**
    - iRODS button status updating for Proteomics projects (#428)
    - General iRODS button status only updated once per page load (#429)
    - Performance issues in iRODS stats querying with large data (#432)
    - iRDOS buttons not disabled if iRODS collections not created (#445)
    - ISAtab upload wiget error not displayed without Bootstrap 4 workarounds (sodar_core#164)

Removed
-------

- **General**
    - Old Bootstrap 4 workarounds for django-crispy-forms (sodar_core#157)
- **Samplesheets**
    - iRODS wait icon from study apps and assay tables (#430)


v0.4.2 (2019-02-04)
===================

Added
-----

- **General**
    - Formatting with Black
    - Flake8 and Black checks in CI (#422)
    - General code cleanup and refactoring (#422)
    - ``IRODSBACKEND_STATUS_INTERVAL`` setting passed to JQuery (#423)
- **Irodsbackend**
    - Support for POST in Ajax views (#416)
    - App specific rules (#418)
    - Client side enabling/disabling of iRODS links buttons (#260)
    - Get status updating interval from setting variable (#423)
    - API view permission tests (#386, #417)
- **Samplesheets**
    - Support alternative notation in contact fields (#382)

Changed
-------

- **General**
    - Upgrade minimum Python version requirement to 3.6 (sodar_core#102)
    - Update and cleanup Gitlab-CI setup (sodar_core#85)
    - Update Chrome Driver for UI tests
    - Cleanup Chrome setup
    - Update ``login.html`` override to add site messages (sodar_core#105)
    - Update site dependency utilities to match django-sodar-core v0.4.1+ (sodar_core#90)
    - Upgrade to django-sodar-core v0.4.3
    - Upgrade dependencies to match django-sodar-core v0.4.2+ (#420)
    - Disable ``USE_I18N`` (sodar_core#117)
    - Changed ``CONTRIBUTORS.txt`` into ``AUTHORS.rst``
- **Irodsbackend**
    - Refactor Ajax API views (#416)
    - Limit the amount of iRODS queries (#414)
- **Landingzones**
    - Rename Taskflow specific API views (sodar_core#104)
- **Samplesheets**
    - Rename Taskflow specific API views (sodar_core#104)
    - Only allow superuser or project owner to delete sheet with iRODS data (#424)

Fixed
-----

- **General**
    - Login URL was not set to ``sodar/users/login.html``
    - Django docs references (sodar_core#131)
    - ``ProjectAccessMixin.get_project()`` calls
- **Samplesheets**
    - DataTables scrolling issue with Bootstrap 4.2.1 (#421)
    - Workaround for DataTables vertical overflow bug (#369)

Removed
-------

- **General**
    - Unused templates in ``sodar/pages``
    - Unused URL mapping to ``about.html``
    - Local JS/CSS includes for JQuery, Bootstrap and other JS helpers (#379, #420)
    - Legacy Python2 ``super()`` calls (sodar_core#118)
    - Redundant ``is_superuser`` predicates from rules (sodar_core#138)
- **Irodsbackend**
    - Unused module ``admin.py``
- **Samplesheets**
    - Unused dropup app buttons mode in templates (sodar_core#108)


v0.4.1 (2018-12-19)
===================

Added
-----

- **General**
    - ``TASKFLOW_TEST_MODE`` setting for test iRODS server support (sodar_core#67)
    - Missing LDAP dev setup script (#385)
- **Irodsbackend**
    - Project UUID parsing support for ``get_uuid_from_path()``

Changed
-------

- **General**
    - Update list button and dropdown classes (#381)
    - Upgrade to django-sodar-core v0.4.0
    - Use ``TASKFLOW_SODAR_SECRET`` for securing Taskflow API views (sodar_core#46)
- **Filesfolders**
    - Import app from django-sodar-core v0.4.0 (#403)
- **Landingzones**
    - Use ``SODAR_API_DEFAULT_HOST`` in email generation (#396)
    - Hide deleted zones in project overview (#394)
- **Samplesheets**
    - Normalize alternative material names as lowercase to optimize search (#390)
    - Add real material name in ``alt_names`` as lowercase (#390)
    - Reduce Django queries to optimize iRODS file search (#393)
    - Replace IRODS query limit settings with ``SHEETS_IRODS_LIMIT`` (#393)
    - Cancer study app: only show shortcuts for genome/exome seq assays (#398)
    - Move germline specific template tags in germline study app (#399)
    - Refactor study app views (#406)

Fixed
-----

- **General**
    - Potential inheritance issues in test classes (sodar_core#74)
- **Irodsbackend**
    - ``TypeError`` in ``get_path()`` not correctly raised with invalid object class name (#404)
    - iRODS connections not properly cleaned up in Ajax API views (#413)
    - Ensure iRODS connection cleanup after exiting a decorated function
- **Irodsinfo**
    - ``NetworkException`` not caught if iRODS server is unavailable (#395)
- **Landingzones**
    - Invalid URLs in zone status update emails (#396)
- **Samplesheets**
    - Cancer study app source query not filtered by study (#389)
    - Handle cancer app library assay linking errors (#404)
    - Assay links in study overview card (#405)
    - Study app shortcut exceptions always redirected to default study (#406)
    - Cancer study IGV shortcut crash if samples not found (#407)

Removed
-------

- **General**
    - Unneeded gunicorn dependency in ``settings/local.py`` (#383)
- **Filesfolders**
    - Local app removed (#403)
- **Landingzones**
    - Unused ``get_irods_cmd()`` template tag


v0.4.0 (2018-10-26)
===================

Added
-----

- **Adminalerts**
    - Import app from djagno-sodar-core
- **Projectroles**
    - Import app from django-sodar-core
- **Taskflowbackend**
    - Import app from django-sodar-core
- **Timeline**
    - Import app from django-sodar-core
- **Userprofile**
    - Import app from django-sodar-core

Changed
-------

- **General**
    - Update Django to v1.11.16 (#370)
    - Update requirements to match django-sodar-core v0.3.0 (#370)
    - Update SODAR app requirements to current versions
    - Rebrand project and site as ``sodar`` (#166)
    - Update ``SODAR_CONSTANTS`` dependencies in local apps (#370)
    - Update ``sodar_uuid`` model fields and references in local apps (#370)
    - Update ``sodar_url`` references in local apps (#370)
    - Update default templates (#370)
    - Move login Javascript to ``login.js``
    - Update development documentation
- **Samplesheets**
    - Improve data table CSS during DataTables init (#359)

Fixed
-----

- **Irodsbackend**
    - Viewing iRODS file list on an empty collection failed (#375)
    - WebDAV URL copying tooltip not rendered correctly inside DataTables (#377)
- **Samplesheets**
    - IGV session file generating crash if VCF file was not found (#372)

Removed
-------

- **General**
    - Local Django apps included in SODAR Core v0.3.0 (#370)
    - Unused django-extra-views requirement
    - Unused user templates (#370)
- **Samplesheets**
    - Duplicate DataTables CSS includes


v0.3.3 (2018-09-25)
===================

Added
-----

- **Samplesheets**
    - Cancer study app (#371)
    - Generic IGV session file generating function ``get_igv_xml()`` in ``studyapps.utils``
    - ``get_sources()`` helper in ``Study`` model
    - ``get_samples()`` helper in ``GenericMaterial`` model
    - ``get_sample_libraries()`` helper in ``samplesheets.utils``

Changed
-------

- **Samplesheets**
    - Use ``get_igv_xml()`` in germline study app
    - Use ``get_sample_libraries()`` in DNA sequencing assay app


v0.3.2 (2018-09-11)
===================

Added
-----

- **General**
    - BIH Proteomics data transfer docs (Mathias Kuhring)

Changed
-------

- **Projectroles**
    - Use ``omics-search-card-body`` instead of ``omics-card-body-table`` (#364)

Fixed
-----

- **General**
    - Dropdown menu overflow hiding in ``omics-card-body-table`` classes (#364)
- **Samplesheets**
    - Investigation parsing failure when replacing isatab deleted previous version (#365)

Removed
-------

- **Landingzones**
    - Usage of ``popupNoFilesHtml`` (will be removed from omics_core)


v0.3.1 (2018-08-24)
===================

Added
-----

- **General**
    - ``SITE_SUBTITLE`` setting to show beta status or something similar (#311)
    - API settings ``SODAR_API_DEFAULT_VERSION`` and ``SODAR_API_MEDIA_TYPE``
    - Domain/system user groups set on login or by management command ``syncgroups`` (#313)
    - CSS classes for ``badge-group`` (#349)
- **Adminalerts**
    - Enable Markdown in alert description (#196)
    - Display user in alert details (#330)
- **Filesfolders**
    - Text style depending on item flag (#303)
    - Optional automated unpacking for uploaded zip files (#327)
    - Setting ``FILESFOLDERS_MAX_ARCHIVE_SIZE`` (#327)
    - ``search()`` function in plugin (#335)
- **Irodsbackend**
    - Generic iRODS file statistics view, template tags and Javascript (#181, #188)
    - Missing support for Investigation objects in ``get_path()`` (#292)
    - iRODS collection query Javascript (#295)
    - Display collection name in iRODS collection list
    - ``IrodsObjectListAPIView`` for iRODS collection list queries (#308)
    - ``BaseIrodsAPIView`` for implementing views
    - Logging for error cases (#310)
    - ``get_sample_path()`` and ``get_uuid_from_path()`` helpers (#289)
    - Param ``like_name`` into data object querying (#289)
- **Landingzones**
    - Send email when zone status is set as ``MOVED`` or ``FAILED`` (#280)
    - Unit tests for ``ZoneStatusSetAPIView``
    - Display iRODS stats in details card (#188)
    - Ability to add extra flow parameters with ``get_extra_flow_data()`` (#297)
    - Script user workaround for non-working tickets in the proteomics use case (#297)
    - Option for validating files without moving (#333)
    - Missing unit tests for ``LandingZoneMoveView`` (#248)
- **Projectroles**
    - Helper ``email.send_generic_mail()`` (#280)
    - Common template tag ``check_backend()``
    - Define backend app javascript include in plugin (#300)
    - Common template tag ``get_setting()``
    - ``CurrentUserFormMixin`` for providing current using to forms as ``current_user``
    - Helper mixin ``KnoxAuthMixin`` for views testing
    - Sanitize search input (#332)
    - Handle project list title cell overflow (#306)
    - No results alert for search (#288)
    - DataTables rendering for search results (#328)
    - Result count in search results (#338)
    - Settings variable ``PROJECTROLES_SEARCH_PAGINATION`` (#328)
    - Pagination for search results (#328)
    - Filtering for search results (#328)
- **Samplesheets**
    - Display original study/assay filenames as tooltips (#283)
    - Display assays for samples in search results (#157)
    - Helper function ``GenericMaterial.get_sample_assays()`` (#157)
    - Auto-populate field ``alt_names`` in the ``GenericMaterial`` model (#285)
    - Management command ``syncnames`` to update ``alt_names`` (#285)
    - Display project/study file statistics using irodsbackend (#188)
    - Display stats on the project details page card (#188)
    - Proof-of-concept ID Querying API with token authentication
    - iRODS files searchable in site search (#289)
    - Highlighting of search strings (#341)
    - Custom display for "external links" fields (#349)
    - Settings variable ``SHEETS_EXTERNAL_LINK_LABELS`` (#349)
    - Custom display for different "contact" fields
    - Handle sheet table cell overflow
    - Settings variable ``SHEETS_MAX_COLUMN_WIDTH``
    - ``search()`` function in plugin (#335)
    - Settings variables ``SHEETS_IRODS_LIMIT_PROJECT`` and ``SHEETS_IRODS_LIMIT_TOTAL`` (#289)

Changed
-------

- **General**
    - Search button CSS (#351)
    - Refactor search views to allow multiple result sets from apps (#335)
    - Implement search in ``ProjectAppPlugin.search()`` instead of template tags (#335)
- **Adminalerts**
    - Update user when updating alert (#179)
- **Filesfolders**
    - Refactor timeline event creation for object modification
    - Unify project title printing in search with other apps (#335)
- **Irodsbackend**
    - Optimize iRODS queries for increased performance (#242)
    - Improve collection listing popup layout
    - Check user perms for iRODS collection when performing queries
    - Omit ``icp`` from iRODS path when copying to clipboard (#319)
- **Landingzones**
    - Use irodsbackend code for statistics queries (#188)
    - Refactor ``irods_backend`` references in templates
    - Move javascript to separate file (#181)
    - Hide deleted zones from "other zones" (#302)
    - Use irodsbackend code for collection listing (#295)
    - Sort zones in list by zone tiele (#312)
- **Projectroles**
    - Minor email refactoring (#280)
    - Hide system users from normal users' UI in member selection (#347)
    - Hide search elements if no results are found (#288)
- **Samplesheets**
    - Search for VCF files under all family members in germline app (#275)
    - Include ``alt_name`` in GenericMaterial search (#285)
    - Improve search results layout
    - Display investigation title on project card (#293)
    - Refactor ``irods_backend`` references in templates
    - Use irodsbackend code for collection listing (#295)
    - Move irods buttons to irodsbackend (#301)
    - Move irods clipboard javascript to irodsbackend (#301)
    - Move javascript to separate file (#181)
    - Allow multiple assay field combinations for selecting assay plugin (#315)
    - Enable genome_seq_nucleotide_seq app also for exomes (#315)
    - Rename genome_seq_nucleotide_seq into dna_sequencing (#315)
    - Refactor site search (#289)
    - Exclude "name" column from automated aligning (#350)

Fixed
-----

- **General**
    - Popover width in CSS (#291)
- **Irodsbackend**
    - Handle missing user auth in API views without raising an exception (#337)
- **Landingzones**
    - Incorrectly calculated ``LANDINGZONES_STATUS_INTERVAL`` (#305)
- **Projectroles**
    - Extra spaces and tabs broke search (#290)
    - Search not enabled if selecting previous input with mouse (#307)
    - Case conversion issue caused ``highlight_search_term()`` to fail (#341)
- **Samplesheets**
    - Show correct target in germline app ``FileRedirectView`` message (#275)
    - Source/sample name search resulted in a template crash (#287)
    - CSS highlight bug in nav dropdown
    - Content app DataTable header broke layout if following assay anchor (#224)
    - Wrong CSS class in pep_ms (#318)
    - Assays not filtered by project in sample search (#358)
- **Timeline**
    - Not found label did not reflect timeline_mode (#346)

Removed
-------

- **General**
    - Unused ``ProjectAppPluginPoint.search_title`` attribute (#335)
- **Filesfolders**
    - ``find_filesfolders_items()`` template tag (#335)
- **Landingzones**
    - ``LandingZoneIrodsStatisticsGetAPIView`` and related redundant JQuery scripts
    - ``LANDINGZONES_STATISTICS_INTERVAL`` settings variable
    - ``LandingZoneIrodsObjectListAPIView``, use view in irodsbackend instead (#308)
- **Projectroles**
    - ``find_projects()`` template tag (#335)
- **Samplesheets**
    - MD5 display from file list view
    - Deprecated ``irods_base_dir`` from views
    - ``IrodsObjectListAPIView``, use view in irodsbackend instead (#308)
    - ``samplesheets_common.js``, functionality now in irodsbackend (#301)
    - ``utils.get_last_material_index()``, no longer used (#317)
    - ``find_samplesheets_items()`` template tag (#335)


v0.3.0 (2018-07-03)
===================

Added
-----

- **General**
    - Sphinx-based online user manual (#50)
    - Site favicon (#166)
- **Irodsbackend**
    - Proper cleanup of iRODS session on API deletion
    - Temporary iRODS ticket operations (#240)
- **Landingzones**
    - Status types ``DELETING`` and ``DELETED`` (#228)
    - Landing zone special configurations (#240)
    - Configapp sub-app plugin point (#240)
    - Configapp plugin for ``bih_proteomics_smb`` (#240)
    - More unit tests for views (#248)
- **Projectroles**
    - Tag ``force_wrap()`` in common template tags
- **Samplesheets**
    - Add genome_seq_nucleotide_seq assay app (#249)
    - Add pep_ms assay app (#245)
    - Object metadata in sample sheet table rendering (#254)
    - Show investigation configuration in study details table
    - WebDAV clipboard copying links (#257)
    - IGV integration and auth-basic support for germline study app

Changed
-------

- **General**
    - Update installation and development documentation (#237)
    - Rebrand site as SODAR (#166)
    - Separate manual from development docs (#50, #237)
    - Use Bootstrap4 modal instead of jquery.popupoverlay (#180)
    - Improve login user experience (#229)
- **Landingzones**
    - Make landing zone deletion async (#228)
    - Refactor zone list item rendering
    - Include iRODS buttons from ``_irods_buttons.html``
    - Display full zone title in project overview
    - Call ``cleanup_zone()`` in configapps when setting status to MOVED or DELETED (#240)
- **Projectroles**
    - Use modal for email preview popups (#180)
- **Samplesheets**
    - Clarify ISA parsing error message (#236)
    - Separate configapps into study and assay apps (#249)
    - Move ``get_row_path()`` to assay app (#249)
    - Make links column hideable by assay app (#249)
    - Move iRODS buttons in separate template for including
    - Change ``get_assay_path()`` into a more general ``get_irods_path()`` in template tags (#257)
    - Display study and assay links on the project details page (#257)
    - Move commonly used javascript to ``samplesheets_common.js`` (#181)
    - iCommands button copies link to clipboard without popup (#257)
    - Improve germline study app layout
    - General table layout updates

Fixed
-----

- **Landingzones**
    - Buttons not correctly activated during status update (#215)
    - Long landing zone names broke zone list table
    - iRODS client ``NetworkException`` not caught by ``LandingZoneStatisticsGetAPIView`` (#255)
- **Samplesheets**
    - Escape cell values (#233)
    - Study and Assay UUIDs changed during replace (#234)
    - Missing iCommands path in popup (#250)
    - Improve study and assay layout
    - Linking of BAM and VCF files if no assay plugin was found (#264)
    - Incorrectly filled ``Family`` field broke germline study rendering (#270)
- **Timeline**
    - Long labels broke timeline table (#225)

Removed
-------

- **General**
    - jquery.popupoverlay dependencies (#180)
- **Landingzones**
    - ZoneDeleteAPIView as it's not needed anymore due to async deletion (#228)


v0.3.0b (2018-06-05)
====================

Added
-----

- **General**
    - Admin link for superuser (#134)
    - Common ``popupWaitHtml`` and ``popupNoFilesHtml`` Javascript variables
    - Clipboard.js for helping clipboard operations
    - CSS styling for ``.omics-code-input``
    - Height check for project sidebar and dropdown menu switching (#156)
- **Irodsbackend**
    - Add irodsbackend app (#139)
    - Add ``get_path()`` for retrieving iRODS paths for Django objects
    - Template tag ``get_irods_path()`` to get object iRODS path in template
    - Add ``get_session()`` for direct iRODS API access
    - Add ``collection_exists()`` to check collection availability
- **Irodsinfo**
    - Add irodsinfo site app (#183)
- **Landingzones**
    - Add landingzones app (#139)
- **Projectroles**
    - Settings updating to Taskflow for project creation and modification (#139)
    - Add ``get_all_settings()`` and ``get_default_setting()`` in ``project_settings``
    - Add ``get_class()`` in ``projectroles_common_tags``
- **Samplesheets**
    - iRODS directory creation (#139)
    - iRODS link and iCommands display (#139)
    - Render optional hidden HTML attributes for cell meta data (#139)
    - Add ``get_dir()`` and ``get_display_name()`` helpers to Study and Assay
    - Add ``SampleSheetTaskflowMixin`` for Taskflow test helpers
    - Row numbers for sample sheet tables (#155)
    - Tour help (#145)
    - Row limit to prevent import and rendering of huge data (#192)
    - Render extract label column
    - Project setting ``study_row_limit`` (#192)
    - Replacing sample sheets for limited modifications (#195)
    - ``SampleSheetConfigPlugin`` for sheet configuration specific sub-apps (#201)
    - Config app ``bih_germline`` as an example (#201)
    - Add ``get_configuration()`` in the ``Investigation`` model (#201)
    - Add ``get_irods_row_path()`` to iRODS path to sample sheet row (#172)
- **Taskflowbackend**
    - Add taskflowbackend app (#139)
    - Add optional ``omics_url`` kwarg to ``submit()``

Changed
-------

- **General**
    - Upgrade to Django 1.11.13
    - Upgrade to django-crispy-forms 1.7.1 (#153)
    - Upgrade to Boostrap 4.1.1 (#144)
    - Improve tour help layout
    - Upgrade to Gunicorn 19.8.1
    - Switch ordering of Filesfolders and Landingzones in project menu (#217)
- **Filesfolders**
    - Don't show empty folder label if subfolders exist (#135)
- **Irodsbackend**
    - Implement functionality of omics_irods_rest directly in the app
    - Rename ``get_object_list()`` into ``get_objects()``
    - Improve error handling in ``get_objects()``
- **Projectroles**
    - Use Taskflowbackend only for creating and modifying ``PROJECT`` type projects
    - Modify Taskflow API URLs
    - Refactor ``get_active_plugins()``
    - Refactor email sending
    - Properly log and report errors in email sending (#151)
    - Require email sending to succeed for creating invites (#149)
    - Modify ProjectStarringAPIView to use common permission mixins
    - Rename ``TestTaskflowViewBase`` to ``TestTaskflowBase``
    - Integrate ``TaskflowMixin`` into ``TestTaskflowBase``
    - Improve project list layout (#171)
    - Move iRODS info page into the irodsinfo app (#183)
    - Modify signature of ``_get_project()`` in ``ProjectAccessMixin``
    - Allow ``get_all_settings()`` and ``get_project_setting()`` with no project in ``project_settings``
- **Samplesheets**
    - Rename top header "legend" to "value" (#129)
    - Allow sample sheet upload for project contributor (#137)
    - Allow sample sheet deletion for project contributor (#168)
    - In taskflow operations, use ``omics_uuid`` instead of ``pk`` (#99)
    - Refactor table HTML rendering
    - Improve URLs for ontology linking (#170)
    - Hide columns with no data (#184)
    - Do not allow importing sheet or creating iRODS dirs if rendering fails (#192)
    - Upgrade altamISA to commit ``ddf54e9ab9b47d2b5a7d54ce65ea8aa673375f87`` (#191)
    - Display material subtype in top column (#200)
    - Display Process name if set (#207)
- **Taskflowbackend**
    - Use ``omics_uuid`` instead of ``pk`` (#139)
    - Only set up ``PROJECT`` type projects in ``synctaskflow``

Fixed
-----

- **General**
    - Add missing email settings in production config (#149)
    - Add ``python3-distutils`` to Xenial requirements to fix failing tests caused by recent updates
    - User links visible when logged out on low resolutions (#197)
    - Fix ``omics-card-table-bordered`` CSS
- **Filesfolders**
    - Broken link for subfolders with depth >1 (#136)
- **Projectroles**
    - Invalid URL in ``build_invite_url()`` caused a crash (#149)
    - Project creation failure using taskflow caused database corruption (#162)
    - Proper redirect from failed project creation to home or parent category
    - Project partially modified instead of rollback if update with taskflow failed (#163)
    - Project settings not correctly populated in ``TestTaskflowBase``
    - Allow ``_get_project()`` with top level app models from nested apps (#201)
    - README not modified when updating project with Taskflow enabled (#209)
- **Samplesheets**
    - Delete investigation if import fails (#138)
    - Assay sorting was not defined
    - Assay data could end up in the wrong table with multiple assays under a study (#169)
    - Correctly use ``request.session.real_referer`` for back/cancel links (#175)
    - Error rendering sheet tables caused app to crash (#182)
    - Building a redirect URL in export view caused a crash
    - Prevent double importing of Investigation (#189)
    - Zip file upload failed on Windows browsers (#198)
    - Remove possible duplicate sample rows from study tables (#199)
    - Extract label not correctly parsed
    - Back link not working in ``IrodsDirView`` (#206)
    - Invalid HTML from rendering extra cell classes together with ``text-right``
    - Correctly parse study description (#208)
    - Numerical value check for right-aligning (#218)
- **Timeline**
    - Fix event id parameter in Taskflow view

Removed
-------

- **General**
    - Removed Flynn workarounds, deploying on Flynn no longer supported (#133)
- **Projectroles**
    - "View Details" link in details page, not needed thanks to project sidebar
    - ``get_description()`` templatetag


v0.2.0 (2018-04-13)
===================

Added
-----

- **General**
    - Automated version numbering in footer (#130)
    - ``ProjectPermissionMixin`` for project apps
    - ``ProjectAccessMixin`` for retrieving project from UUID URL kwargs
    - The ``omics_uuid`` field in models where it was missing (#97)
    - Graph output with pygraphviz for local development
- **Projectroles**
    - Add ``get_project_link()`` in templatetags
- **Samplesheets**
    - Add samplesheets app
    - ISA specification compatible data model (#76)
    - Importing ISA investigations as sample sheets (#77)
    - Rendering and navigation of sample sheets (#79)
    - Simple sample sheet search (#87)
    - DataTables rendering of sheets (#81)

Changed
-------

- **General**
    - Upgrade site to Django 1.11.11
    - Upgrade site to Boostrap 4.0.0 Stable (#78)
    - Use ``omics_uuid`` instead of ``pk`` in URLs and templates (#97)
    - Rework URL scheme for consistency and compactness (#105)
    - Modify subtitle and page content containers for all apps
    - Sticky subtitle nav menu for pages with operations menus or navigation
    - Site-wide CSS tweaks
    - Rename ``details_position`` to ``plugin_ordering`` in plugins (#90)
    - Refactor app views with redundant ``SingleObjectMixin`` includes (#106)
    - Squashed/recreated database migrations (#120) (Note: site must be deployed on a fresh database in this version)
- **Projectroles**
    - Search view improvements
    - Refactor roles and invites views
    - Split ``get_link_state`` tag into ``get_app_link_state`` and ``get_pr_link_state`` to support new URLs (#105)
- **Timeline**
    - Use ``omics_uuid`` for object lookup in ``plugins.get_object_link()`` (#97)

Fixed
-----

- **General**
    - Update ChromeDriver to eliminate UI test crashes (#85)
    - User dropdown rendering depth (#82)
    - Error template layout breaking (#108)
- **Filesfolders**
    - Public link form widget always disabled when updating a file (#102)
    - Content type correctly returned for uploaded files and folder READMEs (#131)

Removed
-------

- **General**
    - Role "project staff" (#121)


v0.1 (2018-01-26)
=================

Added
-----

- **General**
    - Create new base project using the current version of `cookiecutter-django <https://github.com/pydanny/cookiecutter-django>`_
    - Additional unit tests for site apps
    - Changelog in ``CHANGELOG.rst``
    - User profile page (#29)
    - Highlight help link for new users (#30)
    - Support for multiple LDAP backends (#69)
- **Adminalerts**
    - Add adminalerts app (#17)
- **Filesfolders**
    - Import app from prototype
    - Page title to main files list
    - File, folder and link search (#21)
    - Item flagging (#38)
    - History links for items (#35)
    - Folder readme file rendering (#36)
- **Projectroles**
    - Import app from prototype
    - Sub-navbar with project breadcrumb (#20)
    - Move app and project editing links to project sidebar (#20)
    - Helper functions for project settings
    - Initial project and app object search (#16, #21)
    - More helper functions in Project model: ``get_parents()``, ``get_full_title()``
    - Project list filtering (#32)
    - Project tagging/starring functionality (#37)
    - History links for project members (#35)
    - Import roles from another owned project (#9)
    - User HTML tag in common templatetags (#71)
- **Timeline**
    - Import app and backend plugin from prototype
    - Object event view history and API (#35)
    - Project model support in event references

Changed
-------

- **General**
    - Update site for Django 1.11.9 (#1) and Python 3.6.3 (#2)
    - Update site to Bootstrap 4 Beta 3 (#70)
    - Update third-party libraries to their latest versions
    - Layout redesign (#20)
    - Switch from PhantomJS to Headless Chrome for UI tests (improved performance and stability, Bootstrap 4 Beta compatibility)
    - Include CSS and JS imports in testing configs and CI
    - General code refactoring and cleanup
    - Update installation instructions in ``INSTALL.rst``
    - Rename "actions" into "operations" (#41)
    - Message alert boxes made dismissable (#25)
    - Make tables and navs responsive to browser width
- **Filesfolders**
    - Redesign data model with inheritance to avoid field repetition
    - Internal app name is now ``filesfolders``
    - Project setting ``allow_public_links`` is now False by default (#43)
    - Include extra data in item creation and updating
    - Only allow one readme.* file in each folder (#36)
- **Projectroles**
    - Remove two-level restriction for project and category nesting in models
    - Only allow creation of categories on top level
    - Improved project list layout
    - Move ``OMICS_CONSTANTS`` from configuration into ``models.py``
    - Populate Role objects in a migration script instead of a fixture
    - Import patched ``django-plugins`` from GitHub instead of including in project directly
    - Include extra data in project creation and updating
    - Move Project settings helper functions to ``project_settings.py``
    - Disable help link instead of hiding if no tour help is available
    - Show notice card if no ReadMe is available for project (#42)
    - Refactor URL kwargs
    - Allow users with roles under category children to view category (#47)
    - Update text labels for role management to refer to "members" (#40)
    - Separate common template tags into ``projectroles_common_tags``
    - Move project settings forms to project creation/update view (#44)
    - Provide reload-safe referer URL in ``request.session.real_referer`` (#67)
- **Timeline**
    - Enable event details popover on the project details page
    - Limit details page list to successful events
    - Allow guest user to see non-classified events
    - Function ``add_event()`` raises proper ``ValueError`` exceptions

Fixed
-----

- **Filesfolders**
    - Redirects in exception cases in ``FilePublicLinkView``
    - Unexpected characters in file name broke the ``file_serve`` view (ODA #109)
    - Check for existing file if moving file during update (#56)
- **Projectroles**
    - Check for project title uniqueness
    - Don't allow matching titles for subproject and parent
    - App plugin element IDs in templates
    - Project context for role invite revocation page
    - Project type correctly displayed for user (#27)
- **Timeline**
    - Tour help anchoring for list navigation buttons
    - User column link was missing the ``mailto:`` protocol syntax

Removed
-------

- **General**
    - The unused ``get_info()`` function and its implementations from ``plugins`` (provide ``details_template`` instead)
    - Unused user app features
- **Filesfolders**
    - Redundant and deprecated fields/functions from the data model
    - Example project settings
- **Projectroles**
    - Temporary settings variables for demo and UI testing hacks
