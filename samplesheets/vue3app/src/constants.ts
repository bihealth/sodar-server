/* General constants */

// Study name truncate length in page header nav dropdown
export const STUDY_NAV_DROPDOWN_LEN: number = 48
// Study name truncate length in page header nav tabs
export const STUDY_NAV_TAB_LEN: number = 32
// Default toast display interval in milliseconds
export const TOAST_INTERVAL: number = 1500

// Detail table fields
export const INV_META_FIELDS = [
  ['Identifier', 'identifier'],
  ['Title', 'title'],
  ['Description', 'description']
]
export const STUDY_META_FIELDS = [
  ['File Name', 'file_name'],
  ['Identifier', 'identifier'],
  ['Title', 'title'],
  ['Description', 'description']
]
export const STUDY_SODAR_FIELDS = [
  ['Display Name', 'display_name'],
  ['Plugin Name', 'plugin_name'],
  ['Plugin Title', 'plugin_title']
]
export const ASSAY_META_FIELDS = [
  ['File Name', 'file_name'],
  ['Measurement Type', 'measurement_type'],
  ['Technology Type', 'technology_type'],
  ['Technology Platform', 'technology_platform']
]
export const ASSAY_SODAR_FIELDS = [
  ['Display Name', 'display_name'],
  ['Plugin Name', 'plugin_name'],
  ['Plugin Title', 'plugin_title'],
  ['Display Row Links', 'display_row_links']
]
export const SHEET_STATS = [
  ['Studies', 'study_count'],
  ['Assays', 'assay_count'],
  ['Protocols', 'protocol_count'],
  ['Processes', 'process_count'],
  ['Sources', 'source_count'],
  ['Materials', 'material_count'],
  ['Samples', 'sample_count'],
  ['Data Files', 'data_count']
]
