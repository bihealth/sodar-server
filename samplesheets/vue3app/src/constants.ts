/* General constants */

// URLs
export const URL_ROW_DEL_PREFIX = '/samplesheets/ajax/edit/row/delete/'
export const URL_ROW_INS_PREFIX = '/samplesheets/ajax/edit/row/insert/'

// Standard Ajax data
export const AJAX_RES_OK = 'ok'

// Study name truncate length in page header nav dropdown
export const STUDY_NAV_DROPDOWN_LEN = 48
// Study name truncate length in page header nav tabs
export const STUDY_NAV_TAB_LEN = 32
// Default toast display interval in milliseconds
export const TOAST_INTERVAL = 1500

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
export const HEADER_NAME_SAMPLE = 'sample'
export const CELL_EMPTY_VAL = '-'

// Edit mode message strings
export const EDIT_MODE_EXIT_MSG = 'Exit edit mode'
export const EDIT_MODE_SAVE_MSG =
  ' and save current sheet version as backup'
export const EDIT_MODE_UNSAVED_MSG =
  'Please save or discard your unsaved table row before exiting edit mode'

// Edit mode badge strings
export const EDIT_BADGE_DEFAULT_LABEL = 'Edit Mode'
export const EDIT_BADGE_SAVED_LABEL = 'Changes Saved'
export const EDIT_BADGE_UNSAVED_LABEL = 'Unsaved Changes'

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
export const EDIT_HEADER_TYPE_PROCESS = 'process_name'
export const EDIT_HEADER_TYPE_PROTOCOL = 'protocol'
// Common lists of header types
export const NODE_ID_HEADER_TYPES = [
  EDIT_HEADER_TYPE_NAME,
  EDIT_HEADER_TYPE_PROCESS,
  EDIT_HEADER_TYPE_PROTOCOL
]

// Default regex for sheet editor
export const EDIT_REGEX: { [key: string]: RegExp } = {
  dataName:       /^[\w\-.]+$/,
  date:           /^\d{4}-(0[1-9]|1[012])-(0[1-9]|[12][0-9]|3[01])$/,
  double:         /^-?[0-9]+\.[0-9]+?$/,
  externalLinks:  /^([\w-]+:[\w\-_]+)(;\s*[\w-]+:[\w-_]+)*$/,
  integer:        /^(([1-9][0-9]*)|(0?))$/, // TODO: TBD: Allow negative?
  name:           /^([A-Za-z0-9-_/]*)$/
}

// Edit mode text labels
export const CELL_NODE_NAME_NEW = 'Enter name of new or existing node'
export const CELL_NODE_NAME_RENAME = 'Rename node'
export const NODE_RENAME_MSG = 'A node with the same name already exists in ' +
  'this column. Renaming will replace all values in the fields of the ' +
  'material or process. Proceed?'
export const ROW_DEL_MSG_ALL = 'Deleting all rows of a table is currently ' +
  'not supported'
export const ROW_DEL_MSG_ASSAY = 'Assay rows containing the sample must be ' +
  'first deleted'
export const ROW_DEL_MSG_CANCEL = 'Cancel row insertion'
export const ROW_DEL_MSG_CONFIRM = 'Delete row? This can not be undone.'
export const ROW_DEL_MSG_CONFIRM_CANCEL = 'Cancel row insert?'
export const ROW_DEL_MSG_CONFIRM_IRODS = ' Note that if related sample data ' +
  'exists in iRODS, it may become unreachable.'
export const ROW_DEL_MSG_OK = 'Delete row'
export const ROW_DEL_MSG_UNSAVED = 'New row needs to be saved or cancelled'
export const ROW_INS_MSG_DISABLED = 'Please save or discard your unsaved row ' +
  'before inserting a new one'
export const ROW_SAVE_MSG_IDENTICAL = 'Identical row exists, unable to save'

// Misc edit mode constants
export const EDIT_TERM_QUERY_MIN_LEN = 3

// Ontology constants
export const OBO_ID_HP = 'HP'
export const OBO_ID_OMIM = 'OMIM'
export const OBO_ID_ORDO = 'ORDO'
export const OBO_HEADER_HP = 'hpo terms'
export const OBO_HEADER_OMIM = 'omim disease'
export const OBO_HEADER_ORDO = 'orphanet disease'
