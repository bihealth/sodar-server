// Types and interfaces for the Sample Sheets Vue3 app

import { type TemplateRef } from 'vue'
import { type BaseColorVariant } from 'bootstrap-vue-next'
import {
  type ColDef,
  type ColGroupDef,
  type Column,
  type GridApi,
  type GridOptions,
  type ICellEditorParams,
  type ICellRendererParams,
  type IRowNode
} from 'ag-grid-community'

/* Types -------------------------------------------------------------------- */

export type SheetTableCellDataValue = string |
  Array<string> |
  Array<SheetTableOntologyRef>

/* SODAR Context ------------------------------------------------------------ */

export interface SodarContextLinkLabel {
  label: string
  url: string | null
}

export interface SodarContextInvestigation {
  comments: { [key: string]: string } | null
  description: string
  identifier: string
  title: string
}

export interface SodarContextAssay {
  comments: { [key: string]: string } | null
  display_name: string
  display_row_links: boolean
  file_name: string
  irods_path: string
  measurement_type: string
  name: string
  plugin_name: string | null
  plugin_title: string | null
  technology_type: string
  technology_platform: string
}

export interface SodarContextStudy {
  assays: { [key: string]: SodarContextAssay }
  comments: { [key: string]: string } | null
  description: string
  display_name: string
  file_name: string
  identifier: string
  irods_path: string
  plugin_name: string | null
  plugin_title: string | null
  table_url: string
  title: string
}

export interface SodarContextAlert {
  html: string
  level: string
}

export interface SodarContext {
  alerts: Array<SodarContextAlert>
  allow_editing: boolean
  configuration: string | null // TODO: Verify type
  csrf_token: string
  external_link_labels?: { [key: string]: string | SodarContextLinkLabel }
  inv_file_name: string | null
  investigation: SodarContextInvestigation | object
  irods_backend_enabled: boolean
  irods_path?: string
  irods_status: boolean | null
  irods_webdav_enabled: boolean
  irods_webdav_url: string
  max_col_width: number
  min_col_width: number
  ontology_url_skip?: Array<string>
  ontology_url_template?: string
  parser_version: string
  parser_warnings: boolean
  perms: { [key: string]: boolean }
  project_uuid: string
  sheet_stats: { [key: string]: number }
  sheet_sync_enabled: boolean
  site_read_only: boolean
  studies: { [key: string]: SodarContextStudy }
  user_uuid: string
}

/* Common render table interfaces ------------------------------------------- */

// Render table top header
export interface SheetTableTopHeader {
  colour: string
  colspan: number
  headers?: Array<string>
  value: string
}

// Render table field header
export interface SheetTableFieldHeader {
  col_type: string | null
  item_type: string | null
  max_value_len: number
  name: string
  obj_cls: string
  type?: string // Only there if in edit mode
  value: string
}

// Render table ontology reference
export interface SheetTableOntologyRef {
  accession: string
  name: string
  ontology_name: string | null
}

// Render table cell data
export interface SheetTableCellData {
  // colType: string // NOTE: Removed in the Vue3 app (see #2446)
  editable?: boolean | null // For overriding editing for specific field
  link?: string | null // For the special case of LINK_FILE
  newInit?: boolean // Only for editing
  newRow?: boolean // Only for editing
  tooltip?: string // Only used for file link?
  unit?: string
  uuid?: string
  uuidRef?: string
  value: SheetTableCellDataValue
}

// Render table row
export interface SheetTableRowData {
  [key: string]: number |
    AssayIrodsPath |
    StudyShortcutCell |
    SheetTableCellData
}

// Generic sheet render table
export interface SheetRenderTable {
  col_last_vis: number
  col_values: Array<number>
  field_header: Array<SheetTableFieldHeader>
  table_data: Array<Array<SheetTableCellData>>
  top_header: Array<SheetTableTopHeader>
}

/* Study render table ------------------------------------------------------- */

// Study shortcut query
export interface StudyShortcutQuery {
  key: string
  value: string
}

// Study shortcut cell
export interface StudyShortcutCell {
  files: {
    query: StudyShortcutQuery
    enabled: boolean
  }
  igv: { url: string, enabled: boolean }
}

// Study shortcut
export interface StudyShortcutSchema {
  [key: string]: {
    icon: string
    title: string
    type: string
  }
}

export interface StudyShortcut {
  data: Array<StudyShortcutCell>
  schema: StudyShortcutSchema
}

export interface StudyShortcuts {
  [key: string]: StudyShortcut
}

// Study render table
// TODO: TBD: Include edit fields as optional or extend type?
export interface StudyRenderTable extends SheetRenderTable {
  shortcuts?: StudyShortcuts
}

/* Assay render table ------------------------------------------------------- */

// Assay iRODS path
export interface AssayIrodsPath {
  enabled: boolean
  path: string
}

// Assay shortcut extra link
export interface AssayShortcutExtraLink {
  class: string
  enabled: boolean
  icon: string
  id: string
  title: string
  url: string
}

// Assay shortcut
export interface AssayShortcut {
  assay_plugin?: boolean
  enabled: boolean
  extra_links?: Array<AssayShortcutExtraLink>
  icon?: string
  id: string
  label: string
  path: string
  title?: string
}

export interface AssayShortcuts {
  [key: string]: AssayShortcut
}

// Assay render table
// TODO: TBD: Include edit fields as optional or extend type?
export interface AssayRenderTable extends SheetRenderTable {
  irods_paths: Array<AssayIrodsPath>
  shortcuts: AssayShortcuts
}

/* Display configuration ---------------------------------------------------- */

// Display configuration node
export interface StudyDisplayConfigNode {
  fields: [{ name: string, visible: boolean }], header: string
}
// Display configuration
export interface StudyDisplayConfig {
  assays: { [key: string]: { nodes: [StudyDisplayConfigNode] } }
  nodes: [StudyDisplayConfigNode]
}

/* Edit configuration ------------------------------------------------------- */

// Edit configuration node field
export interface StudyEditConfigNodeField {
  allow_list?: boolean
  default?: SheetTableCellDataValue
  editable?: boolean
  format?: string
  name: string
  ontologies?: Array<string>
  options?: Array<string | number>
  range?: [string, string]
  regex?: string
  type: string
  unit?: Array<string>
  unit_default?: string
}

// Edit configuration node
export interface StudyEditConfigNode {
  fields: [StudyEditConfigNodeField]
  header: string
}

// Edit configuration
export interface StudyEditConfig {
  assays: { [key: string]: { nodes: [StudyEditConfigNode] } }
  nodes: [StudyEditConfigNode]
}

/* Edit context ------------------------------------------------------------- */

// Edit context ontology
export interface StudyEditContextOntology {
  data_version: string
  description: string
  file: string
  ontology_id: string
  sodar_uuid: string
  term_url: string
  title: string
}

// Edit context sample definition
export interface StudyEditContextSample {
  assays: Array<string>
  name: string
}

// Edit context protocol definition
export interface StudyEditContextProtocol {
  name: string
  uuid: string
}

// Edit context
export interface StudyEditContext {
  protocols: Array<StudyEditContextProtocol>
  samples: { [key: string]: StudyEditContextSample }
  sodar_ontologies: { [key: string]: StudyEditContextOntology }
}

/* Render table data structure ---------------------------------------------- */

// Render table response data
export interface RenderTableData {
  display_config: StudyDisplayConfig
  edit_context?: StudyEditContext
  study: { display_name: string }
  study_config?: StudyEditConfig
  table_heights: {
    study: number
    assays: { [key: string]: number }
  }
  tables: {
    study: StudyRenderTable
    assays: { [key: string]: AssayRenderTable }
  }
}

/* Table Store -------------------------------------------------------------- */

export interface SheetAssayShortcuts {
  [key: string]: AssayShortcuts
}

export interface SheetColumnDefs {
  assays: { [key: string]: Array<ColGroupDef> }
  study: Array<ColGroupDef>

}

export interface SheetGridApi {
  assays: { [key: string]: GridApi | null }
  study: GridApi | null
}

export interface SheetGridOptions {
  assays: { [key: string]: GridOptions }
  study: GridOptions
}

export interface SheetRowData {
  assays: { [key: string]: Array<SheetTableRowData> }
  study: Array<SheetTableRowData>
}

export interface TableHeights {
  assays: { [key: string]: number }
  study: number | null
}

/* Grid building ------------------------------------------------------------ */

export interface ColDefBuildParams {
  colConfigModal?: TemplateRef
  editContext?: StudyEditContext
  editMode: boolean
  irodsDirModal: TemplateRef
  notifyCb?: NotifyCb
  ontologyEditModal?: TemplateRef
  sampleColId: string
  sodarContext: SodarContext
  studyDisplayConfig: StudyDisplayConfig | null
  studyEditConfig: StudyEditConfig | null
  studyNodeLen: number
  studyShortcutModal: TemplateRef
  studyUuid: string
}

export interface DataCellRendererParams {
  colDef?: ColDef
  colType: string
  editMode: boolean
  enableHover?: boolean
  fieldEditable?: boolean
  linkLabels: { [key: string]: string | SodarContextLinkLabel }
  node?: IRowNode
  value?: SheetTableCellData
}

export interface IrodsButtonsRendererParams {
  assayIrodsPath: string
  irodsBackendEnabled: boolean
  irodsStatus: boolean
  irodsWebdavUrl: string
  modalRef: TemplateRef
  notifyCb?: NotifyCb
  value: AssayIrodsPath | null
}

export interface StudyShortcutsRendererParams {
  modalRef: TemplateRef
  schema: StudyShortcutSchema
  value: StudyShortcutCell
}

/* SODAR ajax view data ----------------------------------------------------- */

export interface IrodsDirFile {
  displayPath?: string
  irods_request_status: string | null
  irods_request_user: string | null
  modify_time: string
  name: string
  path: string
  size: number
  type: string
  visibleInList?: boolean
}

export interface IrodsDirResponseBody {
  detail?: string
  irods_data?: Array<IrodsDirFile>
}

export interface ParserWarning {
  category: string
  message: string
}

export interface ParserWarningResponseBody {
  warnings: {
    all_ok: boolean // Not actually used
    assays: { [key: string]: Array<ParserWarning> }
    critical_count: number // Not actually used
    investigation: { [key: string]: Array<ParserWarning> }
    limit_reached: boolean
    studies: { [key: string]: Array<ParserWarning> }
    use_file_names: boolean // Not actually used
  }
}

export interface StudyShortcutResponseExtraLink {
  icon: string
  label: string
  url: string
}

export interface StudyShortcutResponseFile {
  extra_links: Array<StudyShortcutResponseExtraLink>
  label: string
  title: string | null
  url: string
}

export interface StudyShortcutResponseCategory {
  files: Array<StudyShortcutResponseFile>
  omit_info?: string
  title: string
}

export interface StudyShortcutResponseData {
  [key: string]: StudyShortcutResponseCategory
}

export interface StudyShortcutResponseBody {
  data?: StudyShortcutResponseData
  error?: string
  title: string
}

export interface OntologyTermResponseRef extends SheetTableOntologyRef {
  is_obsolete: boolean
  term_id: string
}

export interface OntologyTermResponseBody {
  detail?: string
  detail_type?: string
  terms?: Array<OntologyTermResponseRef>
}

export interface GenericResponseBody {
  detail: string
}

/* Edit mode data ----------------------------------------------------------- */

export interface EditUnsavedRow {
  id: string
  tableUuid: string
}

// Header edit renderer params we input to ag-Grid
// TODO: Ensure all critical fields are present
export interface HeaderEditRendererParamInput {
  assayMode: boolean
  assayUuid: string | null
  canEditConfig: boolean
  colType: string | null
  configFieldIdx: number
  configNodeIdx: number
  editConfigField: StudyEditConfigNodeField
  editable: boolean
  headerType: string // TODO: Isn't this dupe for editConfigField.type?
  itemType?: string
  modalRef: TemplateRef
  notifyCb?: NotifyCb
  objCls: string
}

// Full header edit renderer params with ag-grid additions
export interface HeaderEditRendererParams extends
  ICellRendererParams, HeaderEditRendererParamInput {}

// CellEditorParams we input to ag-grid
// NOTE: Editors can access stores
export interface CellEditorParamInput {
  assayMode: boolean
  colAlign: string
  colWidth: number
  editConfigField: StudyEditConfigNodeField
  fieldHeader: SheetTableFieldHeader
  fieldId: string | undefined // Formerly headerField
  notifyCb?: NotifyCb
  ontologyEditModal?: TemplateRef
  sampleColId: string
  tableUuid: string
}

// Full cell editor params with ag-grid additions passed to editors
export interface GridCellEditorParams extends
  ICellEditorParams, CellEditorParamInput {}

// Override of SheetTableOntologyRef for OntologyEditModal
export interface EditOntologyRef extends SheetTableOntologyRef {
  editing?: boolean
  obsolete?: boolean
  unknown?: boolean
}

// Override of SheetTableCellData for OntologyEditModal
export interface OntologyTermCellData extends SheetTableCellData {
  value: Array<EditOntologyRef>
}

// Edit data from cell
export interface CellEditData {
  fieldId: string
  headerName: string
  headerType: string
  itemType?: string
  objCls: string
  ogUnit?: string
  ogValue: SheetTableCellDataValue | null
  unit?: string
  uuid?: string
  uuidRef?: string
  value: SheetTableCellDataValue
}

// Edit data for server cell edit Ajax request
export interface EditRequestCell {
  header_name: string
  header_type: string
  item_type?: string
  obj_cls: string
  unit?: string
  uuid: string | null
  uuid_ref?: string | null
  value: SheetTableCellDataValue
}

// Field for server edit config update Ajax request
export interface EditConfigRequestField {
  action: string
  assay: string | null
  config: StudyEditConfigNodeField
  field_idx: number
  node_idx: number
  study: string
}

export interface EditConfigRequestBody {
  fields: Array<EditConfigRequestField>
}

// Row edit renderer params we input to ag-grid
export interface RowEditRendererParamInput {
  assayMode: boolean
  notifyCb?: NotifyCb
  tableUuid: string
}

// Full row edit renderer params with ag-grid additions
export interface RowEditRendererParams extends
  ICellRendererParams, RowEditRendererParamInput {}

export interface RowDeleteDataNode {
  obj_cls: string
  uuid: string
}

export interface RowDeleteData {
  assay: string | null
  nodes: Array<RowDeleteDataNode>
  study: string
}

export interface RowDeleteParams {
  api: GridApi
  assayMode: boolean
  finishCb?: RowEditFinishCb
  notifyCb?: NotifyCb
  rowNode: IRowNode
  tableUuid: string
}

export interface RowInsertParams {
  api: GridApi
  assayMode: boolean
  notifyCb?: NotifyCb
  tableUuid: string
}

export interface NewRowData {
  [key: string]: SheetTableCellData | string | number
}

export interface CellDefaultParams {
  api: GridApi
  colId: string
  forceEmpty?: boolean
  newInit?: boolean
}

export interface NodeEnableParams {
  api: GridApi
  rowNode: IRowNode
  startIdx: number
  tableUuid: string
}

export interface NodeUpdateParams {
  api: GridApi
  assayMode: boolean
  column: Column
  createNew: boolean
  nameCellData: SheetTableCellData | null
  rowNode: IRowNode
  tableUuid: string
}

// Params for getRowSaveCell()
export interface RowSaveCellParams {
  assayMode: boolean
  column: Column
  rowNode: IRowNode
}

// Params for getRowSaveData()
export interface RowSaveDataParams {
  api: GridApi
  assayMode: boolean
  rowNode: IRowNode
  tableUuid: string
}

// Cell returned by getRowSaveCell()
export interface RowSaveDataCell {
  header_field?: string
  header_name?: string
  header_type?: string
  item_type?: string | null
  obj_cls: string
  uuid?: string
  uuid_ref?: string
  value?: SheetTableCellDataValue
}

// Node returned in getRowSaveData() return data
export interface RowSaveDataNode {
  headers?: Array<string>
  cells: Array<RowSaveDataCell>
}

// Data returned by getRowSaveData()
export interface RowSaveData {
  assay: string | null
  nodes: Array<RowSaveDataNode>
  study: string
}

export interface RowSaveParams {
  api: GridApi
  assayMode: boolean
  finishCb?: RowEditFinishCb
  notifyCb?: NotifyCb
  rowNode: IRowNode
  saveData: RowSaveData
}

/* Function callbacks ------------------------------------------------------- */

export interface RowEditFinishCb {
  (): void
}

export interface NotifyCb {
  (
    body: string,
    variant: keyof BaseColorVariant,
    interval?: number
  ): void
}
