/* General constants */

// Views
export const VIEW_PARSER_WARNING = 'ParserWarning'
export const VIEW_STUDY = 'Study'
export const VIEW_OVERVIEW = 'Overview'

// Selectors
export const SEL_APP_CONTAINER = 'div#sodar-app-container'
export const SEL_APP_CONTENT = 'div#sodar-app-content'
export const SEL_CONTENT_LEFT = 'div#sodar-content-left'

// Requests
export const REQ_GET = 'GET'
export const REQ_POST = 'POST'

// URLs
export const URL_CELL_EDIT_PREFIX = '/samplesheets/ajax/edit/cell/'
export const URL_DATA_REQUEST_CREATE_PREFIX =
  '/samplesheets/ajax/irods/request/create/'
export const URL_DATA_REQUEST_DELETE_PREFIX =
  '/samplesheets/ajax/irods/request/delete/'
export const URL_DISPLAY_CONFIG_PREFIX = '/samplesheets/ajax/display/update/'
export const URL_EDIT_FINISH_PREFIX = '/samplesheets/ajax/edit/finish/'
export const URL_IRODS_LIST_PREFIX = '/samplesheets/ajax/irods/objects/'
export const URL_IRODS_STATS_PREFIX = '/irodsbackend/ajax/stats/'
export const URL_PARSER_WARNING_PREFIX = '/samplesheets/ajax/warnings/'
export const URL_ROW_DEL_PREFIX = '/samplesheets/ajax/edit/row/delete/'
export const URL_ROW_INS_PREFIX = '/samplesheets/ajax/edit/row/insert/'
export const URL_STUDY_LINKS_PREFIX = '/samplesheets/ajax/study/links/'
export const URL_VERSION_SAVE_PREFIX = '/samplesheets/ajax/version/save/'

// Color variants
export const VARIANT_DANGER = 'danger'
export const VARIANT_INFO = 'info'
export const VARIANT_SUCCESS = 'success'

// Standard Ajax data
export const AJAX_RES_OK = 'ok'

// Study name truncate length in page header nav dropdown
export const STUDY_NAV_DROPDOWN_LEN = 48
// Study name truncate length in page header nav tabs
export const STUDY_NAV_TAB_LEN = 32
// Default toast display intervals in milliseconds
export const TOAST_INTERVAL_DEFAULT = 1500
export const TOAST_INTERVAL_DANGER = 2500

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

// Browse mode text labels
export const COPY_MSG_SUFFIX = ' copied into clipboard'
export const IRODS_PATH_COPY_MSG = 'iRODS path copied into clipboard'

// Edit mode text labels
export const CELL_NODE_NAME_NEW = 'Enter name of new or existing node'
export const CELL_NODE_NAME_RENAME = 'Rename node'
export const CELL_UPDATE_ERR_PREFIX = 'Cell update error: '
export const CELL_UPDATE_FAIL_PREFIX = 'Cell update failed: '
export const EDIT_MSG_FINISH = 'Finished editing'
export const EDIT_MSG_SAVE = 'Sheet version saved'
export const EDIT_MSG_SAVE_ERR_PREFIX = 'Error saving version: '
export const EDIT_MSG_SAVE_FAIL_PREFIX = 'Saving version failed: '
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
