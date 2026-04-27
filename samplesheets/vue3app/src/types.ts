/*
Types and interfaces for the Sample Sheets Vue3 app.

NOTE: Some store-specific types are declared in store files.
*/
import { type TemplateRef } from 'vue'
import { type BaseColorVariant } from 'bootstrap-vue-next'
import {
  type ColDef,
  type ICellEditorParams,
  type IRowNode
} from 'ag-grid-community'
import {
  type SodarContext,
  type SodarContextLinkLabel
} from '@/stores/appStore.ts'

/* Types -------------------------------------------------------------------- */

export type SheetTableCellDataValue = string |
  Array<string> |
  Array<SheetTableOntologyRef>

/* General render table interfaces ------------------------------------------ */

// Render table top header
export interface SheetTableTopHeader {
  value: string,
  colour: string,
  colspan: number,
  headers?: Array<string>
}
// Render table field header
export interface SheetTableFieldHeader {
  value: string,
  name: string,
  obj_cls: string,
  item_type: string | null,
  col_type: string | null,
  type?: string, // Only there if in edit mode
  max_value_len: number
}
// Render table ontology reference
export interface SheetTableOntologyRef {
  name: string,
  accession: string,
  ontology_name: string | null
}

// Render table cell data
export interface SheetTableCellData {
  // colType: string, // NOTE: Removed in the Vue3 app (see #2446)
  editable?: boolean | null, // For overriding editing for specific field
  link?: string | null, // For the special case of LINK_FILE
  newInit?: boolean, // Only for editing
  newRow?: boolean, // Only for editing
  tooltip?: string, // Only used for file link?
  unit?: string,
  uuid?: string,
  uuidRef?: string,
  value: SheetTableCellDataValue,
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
  top_header: Array<SheetTableTopHeader>,
  field_header: Array<SheetTableFieldHeader>,
  table_data: Array<Array<SheetTableCellData>>,
  col_values: Array<number>,
  col_last_vis: number
}

/* Study render table ------------------------------------------------------- */

// Study shortcut query
export interface StudyShortcutQuery {
  key: string,
  value: string
}
// Study shortcut cell
export interface StudyShortcutCell {
  igv: { url: string, enabled: boolean },
  files: {
    query: StudyShortcutQuery,
    enabled: boolean
  }
}
// Study shortcut
export interface StudyShortcutSchema {
  [key: string]: {
    type: string,
    icon: string,
    title: string
  }
}
export interface StudyShortcut {
  schema: StudyShortcutSchema,
  data: Array<StudyShortcutCell>
}
export interface StudyShortcuts {
  [key: string]: StudyShortcut
}
// Study render table
// TODO: TBD: Include edit fields as optional or extend type?
export interface StudyRenderTable extends SheetRenderTable {
  shortcuts?: StudyShortcuts,
}

/* Assay render table ------------------------------------------------------- */

// Assay iRODS path
export interface AssayIrodsPath {
  enabled: boolean
  path: string,
}
// Assay shortcut extra link
export interface AssayShortcutExtraLink {
  class: string
  enabled: boolean,
  icon: string,
  id: string,
  title: string
  url: string
}
// Assay shortcut
export interface AssayShortcut {
  assay_plugin?: boolean
  enabled: boolean,
  extra_links?: Array<AssayShortcutExtraLink>,
  icon?: string,
  id: string,
  label: string,
  path: string,
  title?: string,
}
export interface AssayShortcuts {
  [key: string]: AssayShortcut
}
// Assay render table
// TODO: TBD: Include edit fields as optional or extend type?
export interface AssayRenderTable extends SheetRenderTable {
  irods_paths: Array<AssayIrodsPath>,
  shortcuts: AssayShortcuts
}

/* Display configuration ---------------------------------------------------- */

// Display configuration node
export interface StudyDisplayConfigNode {
  fields: [{ name: string, visible: boolean }], header: string
}
// Display configuration
export interface StudyDisplayConfig {
  nodes: [StudyDisplayConfigNode],
  assays: { [key: string]: { nodes: [StudyDisplayConfigNode] } }
}

/* Edit configuration ------------------------------------------------------- */

// Edit configuration node field
export interface StudyEditConfigNodeField {
  allow_list?: boolean,
  default?: string | number | boolean,
  editable?: boolean
  format?: string,
  name: string,
  ontologies?: Array<string>,
  options?: Array<string | number>,
  range?: [string, string], // TODO: How do we parse this?
  regex?: string,
  type: string,
  unit?: Array<string>,
  unit_default?: string,
}
// Edit configuration node
export interface StudyEditConfigNode {
  fields: [StudyEditConfigNodeField],
  header: string
}
// Edit configuration
export interface StudyEditConfig {
  nodes: [StudyEditConfigNode],
  assays: { [key: string]: { nodes: [StudyEditConfigNode] } }
}

/* Edit context ------------------------------------------------------------- */

// Edit context ontology
export interface StudyEditContextOntology {
  file: string,
  title: string,
  ontology_id: string,
  description: string,
  data_version: string,
  term_url: string,
  sodar_uuid: string
}
// Edit context sample definition
export interface StudyEditContextSample {
  name: string,
  assays: Array<string>
}
// Edit context protocol definition
export interface StudyEditContextProtocol {
  uuid: string,
  name: string
}
// Edit context
export interface StudyEditContext {
  samples: { [key: string]: StudyEditContextSample }
  sodar_ontologies: { [key: string]: StudyEditContextOntology }
  protocols: Array<StudyEditContextProtocol>
}

/* Render table data structure ---------------------------------------------- */

// Render table response data
export interface RenderTableData {
  study: { display_name: string },
  tables: {
    study: StudyRenderTable,
    assays: { [key: string]: AssayRenderTable }
  },
  table_heights: {
    study: number,
    assays: { [key: string]: number }
  }
  display_config: StudyDisplayConfig,
  study_config?: StudyEditConfig,
  edit_context?: StudyEditContext
}

/* Grid building ------------------------------------------------------------ */

export interface ColDefBuildParams {
  editContext?: StudyEditContext,
  editMode: boolean,
  irodsDirModal: TemplateRef,
  notifyCb?: NotifyCb,
  ontologyEditModal?: TemplateRef,
  sampleColId: string,
  sodarContext: SodarContext,
  studyEditConfig: StudyEditConfig | null,
  studyDisplayConfig: StudyDisplayConfig | null,
  studyNodeLen: number,
  studyShortcutModal: TemplateRef,
  studyUuid: string,
}

export interface DataCellRendererParams {
  colDef?: ColDef,
  colType: string,
  editMode: boolean,
  enableHover?: boolean,
  fieldEditable?: boolean,
  linkLabels: { [key: string]: string | SodarContextLinkLabel },
  node?: IRowNode,
  value?: SheetTableCellData,
}

export interface IrodsButtonsRendererParams {
  assayIrodsPath: string,
  irodsBackendEnabled: boolean,
  irodsStatus: boolean,
  irodsWebdavUrl: string,
  modalRef: TemplateRef,
  value: AssayIrodsPath | null
}

export interface StudyShortcutsRendererParams {
  modalRef: TemplateRef,
  schema: StudyShortcutSchema,
  value: StudyShortcutCell
}

/* SODAR ajax view data ----------------------------------------------------- */

export interface IrodsDirFile {
  displayPath?: string,
  irods_request_status: string | null,
  irods_request_user: string | null,
  modify_time: string,
  name: string,
  path: string,
  size: number,
  type: string,
  visibleInList?: boolean
}

export interface IrodsDirResponseBody {
  detail?: string,
  irods_data?: Array<IrodsDirFile>
}

export interface ParserWarning {
  message: string,
  category: string
}

export interface ParserWarningResponseBody {
  warnings: {
    all_ok: boolean, // Not actually used
    critical_count: number, // Not actually used
    assays: { [key: string]: Array<ParserWarning> },
    investigation: { [key: string]: Array<ParserWarning> },
    limit_reached: boolean
    studies: { [key: string]: Array<ParserWarning> },
    use_file_names: boolean // Not actually used
  }
}

export interface StudyShortcutResponseExtraLink {
  label: string,
  icon: string,
  url: string
}

export interface StudyShortcutResponseFile {
  label: string,
  url: string,
  title: string | null,
  extra_links: Array<StudyShortcutResponseExtraLink>
}

export interface StudyShortcutResponseCategory {
  files: Array<StudyShortcutResponseFile>,
  omit_info?: string,
  title: string
}

export interface StudyShortcutResponseData {
  [key: string]: StudyShortcutResponseCategory
}

export interface StudyShortcutResponseBody {
  data?: StudyShortcutResponseData,
  error?: string,
  title: string
}

export interface OntologyTermResponseRef extends SheetTableOntologyRef {
  term_id: string,
  is_obsolete: boolean
}

export interface OntologyTermResponseBody {
  detail?: string,
  detail_type?: string,
  terms?: Array<OntologyTermResponseRef>,
}

export interface GenericResponseBody {
  detail: string
}

/* Edit mode data ----------------------------------------------------------- */

export interface EditUnsavedRow {
  tableUuid: string,
  id: string
}

export interface HeaderEditRendererParams {
  assayMode: boolean,
  assayUuid: string,
  canEditConfig: boolean
  colType: string,
  configFieldIdx: number,
  configNodeIdx: number,
  editConfigField: StudyEditConfigNodeField,
  editable: boolean,
  headerType: string,
  // modalComponent: TemplateRef,
}

// CellEditorParams we input to ag-grid
// NOTE: Editors can access stores
export interface CellEditorParamInput {
  assayMode: boolean,
  colAlign: string,
  colWidth: number,
  editConfigField: StudyEditConfigNodeField,
  fieldHeader: SheetTableFieldHeader,
  fieldId: string | undefined, // Formerly headerField
  notifyCb?: NotifyCb,
  ontologyEditModal?: TemplateRef,
  sampleColId: string,
  tableUuid: string,
}

// Full cell editor params with ag-grid additions passed to editors
export interface GridCellEditorParams extends
  ICellEditorParams, CellEditorParamInput {}

// Override of SheetTableOntologyRef for OntologyEditModal
export interface EditOntologyRef extends SheetTableOntologyRef {
  editing?: boolean,
  obsolete?: boolean,
  unknown?: boolean,
}

// Override of SheetTableCellData for OntologyEditModal
export interface OntologyTermCellData extends SheetTableCellData {
  value: Array<EditOntologyRef>
}

// Edit data from cell
export interface CellEditData {
  fieldId: string,
  headerName: string,
  headerType: string,
  itemType?: string,
  objCls: string,
  ogUnit?: string,
  ogValue: SheetTableCellDataValue | null,
  unit?: string,
  uuid?: string,
  uuidRef?: string,
  value: SheetTableCellDataValue,
}

// Edit data for server Ajax request
export interface EditRequestCell {
  header_name: string,
  header_type: string,
  item_type?: string,
  obj_cls: string,
  unit?: string,
  uuid: string | null,
  uuid_ref?: string | null,
  value: SheetTableCellDataValue,
}

/* Function callbacks ------------------------------------------------------- */

export interface NotifyCb {
  (
    body: string,
    variant: keyof BaseColorVariant,
    interval: number | undefined | null
  ): void
}
