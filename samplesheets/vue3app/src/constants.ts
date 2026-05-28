/* General constants */

// Study name truncate length in page header nav dropdown
export const STUDY_NAV_DROPDOWN_LEN: number = 48
// Study name truncate length in page header nav tabs
export const STUDY_NAV_TAB_LEN: number = 32
// Default toast display interval in milliseconds
export const TOAST_INTERVAL: number = 1500

// SODAR sample sheet model
export const DB_OBJ_CLASS_MATERIAL = 'GenericMaterial'
export const DB_OBJ_CLASS_PROCESS = 'Process'

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

// Table rendering
export const CELL_EMPTY_VAL: string = '-'

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

// Edit config actions
export const EDIT_CONFIG_ACTION_UPDATE = 'update'
// Edit config column types
export const EDIT_COL_TYPE_CONTACT = 'CONTACT'
export const EDIT_COL_TYPE_DATE = 'DATE'
export const EDIT_COL_TYPE_EXT_LINKS = 'EXTERNAL_LINKS'
export const EDIT_COL_TYPE_LINK = 'LINK_FILE'
export const EDIT_COL_TYPE_NAME = 'NAME'
export const EDIT_COL_TYPE_NUMERIC = 'NUMERIC'
export const EDIT_COL_TYPE_ONTOLOGY = 'ONTOLOGY'
export const EDIT_COL_TYPE_PROTOCOL = 'PROTOCOL'
export const EDIT_COL_TYPE_UNIT = 'UNIT'
// Edit config formats
export const EDIT_FORMAT_DATE = 'date'
export const EDIT_FORMAT_DOUBLE = 'double'
export const EDIT_FORMAT_EXT = 'external_links'
export const EDIT_FORMAT_INTEGER = 'integer'
export const EDIT_FORMAT_ONTOLOGY = 'ontology'
export const EDIT_FORMAT_PROTOCOL = 'protocol'
export const EDIT_FORMAT_SELECT = 'select'
export const EDIT_FORMAT_STRING = 'string'
// Edit config item types
export const EDIT_ITEM_TYPE_DATA = 'DATA'
export const EDIT_ITEM_TYPE_MATERIAL = 'MATERIAL'
export const EDIT_ITEM_TYPE_SAMPLE = 'SAMPLE'
export const EDIT_ITEM_TYPE_SOURCE = 'SOURCE'
// Edit config header types
export const EDIT_HEADER_TYPE_CHAR = 'characteristics'
export const EDIT_HEADER_TYPE_EXTRACT_LABEL = 'extract_label'
export const EDIT_HEADER_TYPE_NAME = 'name'
export const EDIT_HEADER_TYPE_PERFORM_DATE = 'perform_date'
export const EDIT_HEADER_TYPE_PERFORMER = 'performer'
export const EDIT_HEADER_TYPE_PROTOCOL = 'protocol'

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

// Ontology constants
export const OBO_ID_HP = 'HP'
export const OBO_ID_OMIM = 'OMIM'
export const OBO_ID_ORDO = 'ORDO'
export const OBO_HEADER_HP = 'hpo terms'
export const OBO_HEADER_OMIM = 'omim disease'
export const OBO_HEADER_ORDO = 'orphanet disease'
