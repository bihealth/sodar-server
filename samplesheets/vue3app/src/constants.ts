/* General constants */

// Study name truncate length in page header nav dropdown
export const STUDY_NAV_DROPDOWN_LEN: number = 48
// Study name truncate length in page header nav tabs
export const STUDY_NAV_TAB_LEN: number = 32
// Default toast display interval in milliseconds
export const TOAST_INTERVAL: number = 1500

// SODAR sample sheet model
// export const DB_OBJ_CLASS_MATERIAL = 'GenericMaterial'

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

// Edit mode message strings
export const EDIT_MODE_EXIT_MSG: string = 'Exit edit mode'
export const EDIT_MODE_SAVE_MSG: string =
  ' and save current sheet version as backup'
export const EDIT_MODE_UNSAVED_MSG: string =
  'Please save or discard your unsaved table row before exiting edit mode'

// Edit mode badge strings
export const EDIT_BADGE_DEFAULT_LABEL: string = 'Edit Mode'
export const EDIT_BADGE_SAVED_LABEL: string = 'Changes Saved'
export const EDIT_BADGE_UNSAVED_LABEL: string = 'Unsaved Changes'

// Default regex for sheet editor
export const EDIT_REGEX: { [key: string]: RegExp } = {
  dataName:       /^[\w\-.]+$/,
  date:           /^\d{4}-(0[1-9]|1[012])-(0[1-9]|[12][0-9]|3[01])$/,
  double:         /^-?[0-9]+\.[0-9]+?$/,
  externalLinks:  /^([\w-]+:[\w\-_]+)(;\s*[\w-]+:[\w-_]+)*$/,
  integer:        /^(([1-9][0-9]*)|(0?))$/, // TODO: TBD: Allow negative?
  name:           /^([A-Za-z0-9-_/]*)$/
}

// Misc edit mode constants
export const EDIT_TERM_QUERY_MIN_LEN: number = 3
