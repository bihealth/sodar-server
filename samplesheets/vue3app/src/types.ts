/*
Types and interfaces for the Sample Sheets Vue3 app.

NOTE: Some store-specific types are declared in store files.
*/

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
  colType: string,
  editable: boolean | null, // Only for editing
  newInit?: boolean, // Only for editing
  newRow?: boolean, // Only for editing
  unit?: string,
  uuid?: string,
  uuid_ref?: string,
  value: string | Array<string> | Array<SheetTableOntologyRef>,
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
  path: string,
  enabled: boolean
}
// Assay shortcut
export interface AssayShortcut {
  id: string,
  label: string,
  path: string,
  enabled: boolean,
  icon?: string,
  title?: string,
  assay_plugin?: boolean
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
  name: string,
  type: string,
  format?: string,
  allow_list?: boolean,
  ontologies?: Array<string>,
  default?: string | number | boolean,
  editable?: boolean
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
  sodar_ontologies: { [key: string]: StudyEditContextOntology }
  samples: { [key: string]: StudyEditContextSample }
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
