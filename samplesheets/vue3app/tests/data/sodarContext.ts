import {
  type SodarContext,
  type SodarContextAssay,
  type SodarContextInvestigation,
  type SodarContextStudy
} from '@/stores/appStore.ts'
import {
  ASSAY_PATH,
  ASSAY_UUID,
  PROJECT_SAMPLE_PATH,
  PROJECT_UUID,
  STUDY_PATH,
  STUDY_UUID,
  USER_UUID
} from '../testConstants.ts'

export const sodarContextInvestigation: SodarContextInvestigation = {
  identifier: 'i_small',
  title: 'Small Investigation',
  description: '',
  comments: null
}

export const sodarContextAssay: SodarContextAssay = {
  name: 'small',
  display_name: 'Small',
  file_name: 'a_small.txt',
  measurement_type: 'exome sequencing assay',
  technology_type: 'nucleotide sequencing',
  technology_platform: '',
  comments: null,
  irods_path: ASSAY_PATH,
  plugin_name: null,
  plugin_title: null,
  display_row_links: false
}

export const sodarContextStudy: SodarContextStudy = {
  display_name: 'Small Germline Study',
  file_name: 's_small.txt',
  identifier: 's_small',
  title: 'Small Germline Study',
  description: '',
  comments: {
    'Study Grant Number': '',
    'Study Funding Agency': ''
  },
  irods_path: STUDY_PATH,
  table_url: 'http://0.0.0.0:8000/samplesheets/ajax/study/tables/' + STUDY_UUID,
  plugin_name: null,
  plugin_title: null,
  assays: { [ASSAY_UUID]: sodarContextAssay }
}

export const sodarContext: SodarContext = {
  configuration: null,
  inv_file_name: 'i_small.txt',
  irods_status: true,
  irods_path: PROJECT_SAMPLE_PATH,
  irods_backend_enabled: true,
  parser_version: '0.2.7',
  parser_warnings: true,
  irods_webdav_enabled: true,
  irods_webdav_url: 'https://davrods.local',
  external_link_labels: {
    'x-generic-remote': 'External ID',
    'x-sodar-example': {
      'label': 'Example ID',
      'url': null
    },
    'x-sodar-example-link': {
        'label': 'Example ID with hyperlink',
        'url': 'https://example.com/{id}'
    }
  },
  ontology_url_template: 'https://bioportal.bioontology.org/ontologies/' +
                         '{ontology_name}/?p=classes&conceptid={accession}',
  ontology_url_skip: ['bioontology.org'],
  min_col_width: 100,
  max_col_width: 300,
  allow_editing: true,
  alerts: [],
  csrf_token: 'k73YXvYB9kB8FXCaE3NO2tUGMGzsJCxW4YAk7Ga9jyUiLqh1a3jCY59n2lUelyZm',
  project_uuid: PROJECT_UUID,
  user_uuid: USER_UUID,
  sheet_sync_enabled: false,
  site_read_only: false,
  investigation: sodarContextInvestigation,
  studies: { [STUDY_UUID]: sodarContextStudy },
  perms: {
    'edit_sheet': true,
    'manage_sheet': true,
    'create_colls': true,
    'export_sheet': true,
    'delete_sheet': true,
    'view_versions': true,
    'update_cache': true,
    'view_tickets': true,
    'view_files': true,
    'is_superuser': false
  },
  sheet_stats: {
    'study_count': 1,
    'assay_count': 1,
    'protocol_count': 3,
    'process_count': 9,
    'source_count': 4,
    'material_count': 2,
    'sample_count': 5,
    'data_count': 5
  }
}
