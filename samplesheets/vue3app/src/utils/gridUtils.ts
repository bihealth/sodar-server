// API and helpers for ag-grid setup

import { type TemplateRef } from 'vue'
import {
  themeQuartz,
  type CellClassParams,
  type CellEditorSelectorResult,
  type ColDef,
  type ColGroupDef,
  type GridOptions,
  type ICellEditorParams,
  type ValueGetterParams,
} from 'ag-grid-community'

import {
  type AssayIrodsPath,
  type AssayRenderTable,
  type CellEditorParamInput,
  type ColDefBuildParams,
  type DataCellRendererParams,
  type HeaderEditRendererParamInput,
  type NotifyCb,
  type SheetTableCellData,
  type SheetTableFieldHeader,
  type SheetTableOntologyRef,
  type SheetTableRowData,
  type SheetTableTopHeader,
  type SodarContext,
  type SodarContextAssay,
  type SodarContextLinkLabel,
  type StudyDisplayConfig,
  type StudyDisplayConfigNode,
  type StudyEditConfig,
  type StudyEditConfigNodeField,
  type StudyRenderTable,
  type StudyShortcut,
  type StudyShortcutCell
} from '@/types.ts'

/* Theme setup -------------------------------------------------------------- */

const sodarTheme = themeQuartz.withParams({
  browserColorScheme: 'light',
  cellHorizontalPadding: 10,
  columnBorder: true,
  fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, ' +
    '"Helvetica Neue", Arial, "Noto Sans", sans-serif',
  fontSize: 16,
  headerFontSize: 16,
  headerFontWeight: 'bold',
  headerColumnBorder: true,
  headerColumnBorderHeight: '100%',
  headerColumnResizeHandleColor: 'rgba(0, 0, 0, 0)',
  headerColumnResizeHandleHeight: '100%',
  rowHoverColor: 'rgba(0, 0, 0, 0)', // TODO: Better way to disable hover?
  wrapperBorder: { width: 0 },
  wrapperBorderRadius: 0
})

/* Grid setup helpers ------------------------------------------------------- */

// Return header group ColGroupDef for row number column
export function getRowNumHeaderGroup (): ColGroupDef {
  return {
    headerClass: ['bg-secondary', 'text-white'],
    headerName: 'Row',
    children: [
      {
        cellClass: [
          'text-right',
          'text-muted',
          'sodar-ss-data-unselectable',
          'sodar-ss-data-row-cell',
          'sodar-ss-data-rownum-cell'
        ],
        cellRenderer: null,
        editable: false,
        field: 'rowNum',
        headerClass: ['sodar-ss-data-header'], // TODO: Align right
        headerName: '#',
        maxWidth: 100,
        minWidth: 65,
        pinned: 'left',
        suppressAutoSize: true,
        suppressSizeToFit: true, // TODO: Suppress click border
        width: 65
      } as ColDef
    ]
  }
}

// Return header group ColGroupDef for study shortcuts column
export function getStudyShortcutHeaderGroup (
    table: StudyRenderTable,
    modalRef: TemplateRef
): ColGroupDef {
  return {
    headerClass: ['text-white', 'bg-secondary', 'sodar-ss-data-links-top'],
    headerName: 'Links',
    children: [
      {
        cellClass: [
          'sodar-ss-data-links-cell',
          'sodar-ss-data-unselectable',
          'sodar-ss-data-no-focus'
        ],
        cellDataType: 'object',
        cellRenderer: 'StudyShortcutsRenderer',
        cellRendererParams: {
          schema: table.shortcuts?.schema,
          modalRef: modalRef
        },
        editable: false,
        field: 'shortcutLinks',
        headerClass: ['sodar-ss-data-header', 'sodar-ss-data-links-header'],
        headerName: 'Study',
        minWidth: 80,
        pinned: 'right',
        resizable: true,
        sortable: false,
        suppressAutoSize: true,
        suppressSizeToFit: true,
        valueFormatter: params => params.value.value,
        width: 40 * Object.keys(table.shortcuts?.schema || {}).length
      }
    ]
  }
}

// Return header group ColGroupDef for assay iRODS column
export function getAssayIrodsHeaderGroup (
    sodarContext: SodarContext,
    assayContext: SodarContextAssay,
    modalRef: TemplateRef
): ColGroupDef {
  return {
    headerClass: ['text-white', 'bg-secondary', 'sodar-ss-data-links-top'],
    headerName: 'iRODS',
    children: [
      {
        cellClass: [
          'sodar-ss-data-links-cell',
          'sodar-ss-data-unselectable',
          'sodar-ss-data-no-focus'
        ],
        cellDataType: 'text',
        cellRenderer: 'IrodsButtonsRenderer',
        cellRendererParams: {
          assayIrodsPath: assayContext.irods_path,
          irodsStatus: sodarContext.irods_status,
          irodsBackendEnabled: sodarContext.irods_backend_enabled,
          irodsWebdavUrl: sodarContext.irods_webdav_url,
          modalRef: modalRef
        },
        editable: false,
        field: 'irodsLinks',
        headerClass: ['sodar-ss-data-header', 'sodar-ss-data-links-header'],
        headerName: 'Links',
        minWidth: 136,
        pinned: 'right',
        resizable: true,
        sortable: false,
        suppressAutoSize: true,
        suppressNavigable: true,
        suppressSizeToFit: true,
        width: 136
      } as ColDef
    ]
  }
}

// Return header group ColGroupDef for row edit column
// TODO: Setup cell renderer
export function getRowEditHeaderGroup (): ColGroupDef {
  return {
    headerClass: ['text-white', 'bg-secondary', 'sodar-ss-data-links-top'],
    headerName: 'Edit',
    children: [
      {
        cellClass: ['sodar-ss-data-links-cell', 'sodar-ss-data-unselectable'],
        /*
        cellRenderer: 'RowEditRenderer',
        cellRendererParams: {
          app: params.app,
          gridUuid: params.gridUuid,
          assayMode: params.assayMode,
          sampleColId: params.sampleColId,
          sampleIdx: params.sampleIdx
        },
        */
        editable: false,
        field: 'rowEdit',
        headerClass: ['sodar-ss-data-header', 'sodar-ss-data-links-header'],
        headerName: 'Row',
        minWidth: 80,
        pinned: 'right',
        resizable: true,
        sortable: false,
        suppressAutoSize: true,
        suppressSizeToFit: true,
        width: 80
      }
    ]
  }
}

// Return column width and minimum width
// TODO: Refactor args into params object
export function getColWidth (
    colIdx: number,
    colType: string,
    maxValueLen: number,
    lastVis: number,
    minColWidth: number,
    maxColWidth: number
): [number, number] {
  let minW: number = minColWidth
  const maxW: number = maxColWidth
  let calcW = maxValueLen * 10 + 25 // Default
  let colW
  // External links are a special case
  if (colType === 'EXTERNAL_LINKS') {
    minW = 150
    calcW = maxValueLen * 120
  }
  if (colIdx < lastVis) {
    colW = calcW < minW ? minW : (calcW > maxW ? maxW : calcW)
  } else { // Last visible column is a special case
    colW = Math.max(calcW, minW)
  }
  return [colW, minW]
}

// Return visibility for field column
// TODO: Refactor args into params object
export function getFieldVisibility (
    tableUuid: string,
    topIdx: number,
    assayMode: boolean,
    studySection: boolean,
    fieldHeader: SheetTableFieldHeader,
    fieldEditable: boolean,
    colValues: number | undefined,
    studyDisplayConfig: StudyDisplayConfig | null,
): boolean {
  let displayConfig
  if (studyDisplayConfig) {
    let displayNode: StudyDisplayConfigNode | undefined
    if (!assayMode) {
      displayNode = studyDisplayConfig.nodes[topIdx]
    } else {
      displayNode = studyDisplayConfig.assays[
        tableUuid]!.nodes[topIdx]
    }
    if (displayNode) {
      for (let k = 0; k < displayNode.fields.length; k++) {
        const f = displayNode.fields[k]
        if (f!.name.toLowerCase() === fieldHeader.name.toLowerCase()) {
          displayConfig = f
          break
        }
      }
    }
  }
  if (displayConfig) { // Visibility from config
    return displayConfig.visible
  } else if (assayMode && studySection && fieldHeader.value !== 'Name') {
    // Hide study data in assay
    return false
  } else { // Hide if empty and not editing
    return !!(fieldEditable || colValues)
  }
}

// Return edit configuration for field column
export function getEditConfigField (
    tableUuid: string,
    assayMode: boolean,
    topIdx: number,
    fieldHeader: SheetTableFieldHeader,
    studyEditConfig: StudyEditConfig
): StudyEditConfigNodeField | undefined {
  let editNode = null
  const studyNodeLen = studyEditConfig.nodes.length
  if (!studyNodeLen) return undefined
  if (!assayMode || topIdx < studyNodeLen) {
    editNode = studyEditConfig.nodes[topIdx]
  } else {
    editNode = studyEditConfig.assays[tableUuid]?.nodes[
      topIdx - studyNodeLen]
  }
  if (editNode) {
    for (let k = 0; k < editNode.fields.length; k++) {
      const f = editNode.fields[k]
      if (f &&
          f.name === fieldHeader.name &&
          (['Name', 'Protocol'].includes(f.name) ||
          f.type === fieldHeader.type)) {
        return f
      }
    }
  }
  return undefined
}

// Get field column header ColDef
// TODO: Refactor args into params object
export function getFieldHeader (
    fieldHeader: SheetTableFieldHeader,
    fieldIdx: number,
    colAlign: string,
    colWidth: number,
    minColWidth: number,
    fieldEditable: boolean,
    fieldVisible: boolean,
    editMode: boolean,
    externalLinkLabels: { [key: string]: string | SodarContextLinkLabel }
): ColDef {
  const header: ColDef = {
      headerName: fieldHeader.value,
      field: 'col' + fieldIdx.toString(),
      width: colWidth,
      minWidth: minColWidth,
      hide: !fieldVisible,
      headerClass: ['sodar-ss-data-header'],
      cellDataType: 'object',
      cellRenderer: 'DataCellRenderer',
      cellRendererParams: {
        colType: fieldHeader.col_type,
        editMode: editMode,
        fieldEditable: fieldEditable, // Needed here to update cellClass
        linkLabels: externalLinkLabels
      } as DataCellRendererParams,
      comparator: compareDataCellValues,
      context: {},
      filterValueGetter: getDataCellFilterValue,
      valueFormatter: params => params.value.value
    }

    // Cell classes
    if (!editMode) {
      header.cellClass = ['sodar-ss-data-cell', 'text-' + colAlign]
    } else { // Edit mode
      header.cellClass = function (p: CellClassParams): Array<string> {
        const colAlign = ['UNIT', 'NUMERIC'].includes(
          p.colDef?.cellRendererParams.colType)
          ? 'right'
          : 'left'
        const cellClass = ['sodar-ss-data-cell', 'text-' + colAlign]
        // Set extra classes if non-editable
        if (('editable' in p.value && !p.value.editable) ||
            (!('editable' in p.value) &&
            !p.colDef?.cellRendererParams.fieldEditable)) {
          if ('newInit' in p.value && p.value.newInit) {
            cellClass.push('sodar-ss-data-forbidden')
          } else cellClass.push('bg-light')
          cellClass.push('text-muted')
        }
        return cellClass
      }
      header.valueParser = params => params.newValue
    }
  return header
}

/* Grid setup edit mode helpers --------------------------------------------- */

// TODO: Refactor args into params object
export function getHeaderEditRendererParams (
    tableUuid: string,
    assayMode: boolean,
    fieldHeader: SheetTableFieldHeader,
    nodeIdx: number,
    editConfigField: StudyEditConfigNodeField,
    configFieldIdx: number,
    studyNodeLen: number,
    editable: boolean,
    colConfigModal: TemplateRef,
    notifyCb: NotifyCb | undefined,
): HeaderEditRendererParamInput {
  let configAssayUuid = assayMode ? tableUuid : null
  let configNodeIdx = nodeIdx
  if (assayMode) {
    if (configNodeIdx < studyNodeLen) configAssayUuid = null
    else configNodeIdx = nodeIdx - studyNodeLen
  }
  const ret: HeaderEditRendererParamInput = {
    assayMode: assayMode, // Needed for sample col in assay
    assayUuid: configAssayUuid,
    canEditConfig: true, // TODO: Is this redundant now?
    colType: fieldHeader.col_type || null,
    configFieldIdx: configFieldIdx,
    configNodeIdx: configNodeIdx,
    editConfigField: editConfigField,
    editable: editable, // Add here to allow checking by cell
    headerType: fieldHeader.type as string,
    modalRef: colConfigModal,
    notifyCb: notifyCb,
    objCls: fieldHeader.obj_cls,
  }
  if (fieldHeader.item_type) ret.itemType = fieldHeader.item_type
  return ret
}

// Cell editor selector
export function getCellEditor (
    params: ICellEditorParams
): CellEditorSelectorResult {
  // NOTE: no need to set additional editorParams, we can get these from
  //       editStore within the editor now
  const editorParams = params.colDef.cellEditorParams
  const hcParams = params.colDef.headerComponentParams
  let editorName = 'DataCellEditor'

  if (hcParams.assayMode &&
      params.column.getOriginalParent(
      )?.getColGroupDef()?.headerName === 'Sample' &&
      params.colDef.headerName === 'Name' &&
      'newRow' in params.value &&
      params.value.newRow) {
    // If sample name in an assay or an object ref, return object selector
    editorName = 'ObjectSelectEditor'
  } else if (editorParams.fieldHeader.type === 'protocol') {
    // If protocol, return object selector
    editorName = 'ObjectSelectEditor'
  } else if (hcParams.colType === 'ONTOLOGY') {
    // For ontology, return OntologyEditor
    editorName = 'OntologyEditor'
  }
  const ret: CellEditorSelectorResult = {
    component: editorName,
    params: editorParams
  }
  // Set popup for unit columns
  if (editorParams.editConfigField.unit) {
    ret.popup = true
    ret.popupPosition = 'over'
  }
  return ret
}

/* Grid setup --------------------------------------------------------------- */

// Initialize ag-grid gridOptions
export function initGridOptions (
  context: object,
  editMode: boolean
): GridOptions {
  return {
    animateRows: false,
    context: context,
    // debug: true,
    defaultColDef: {
      editable: false,
      resizable: true,
      sortable: !editMode
    },
    headerHeight: 38,
    pagination: false,
    rowHeight: 38,
    singleClickEdit: false,
    stopEditingWhenCellsLoseFocus: false,
    suppressColumnMoveAnimation: true,
    suppressColumnVirtualisation: false,
    suppressHeaderFocus: true,
    suppressMovableColumns: true,
    theme: sodarTheme,
  }
}

// Build column definitions for a study/assay grid
export function buildColDef (
    table: AssayRenderTable | StudyRenderTable,
    tableUuid: string,
    assayMode: boolean,
    params: ColDefBuildParams,
): Array<ColGroupDef> {
  // Default columns
  const colDef: Array<ColGroupDef> = []

  // Set up row column header group
  const rowHeaderGroup = getRowNumHeaderGroup()
  // Editing: gray out row column to avoid confusion
  if (params.editMode) {
    const col = rowHeaderGroup.children[0] as ColDef
    if (col.cellClass?.constructor == Array) {
      col.cellClass?.push('bg-light')
    }
  }
  colDef.push(rowHeaderGroup)

  // Set up header
  const topHeaderLength = table.top_header.length
  let headerIdx = 0
  let j = headerIdx
  let studySection = true

  // Iterate through top header
  for (let i = 0; i < topHeaderLength; i++) {
    const topHeader = table.top_header[i] as SheetTableTopHeader
    // Set up header group
    let headerGroup: ColGroupDef = {
      headerName: topHeader?.value,
      headerClass: ['text-white', 'bg-' + topHeader.colour],
      children: []
    }
    /*
    if (appStore.editMode) {
      // TODO: cellRendererParams not in ColGroupDef, has this been removed?
      headerGroup.cellRendererParams = { headers: topHeader.headers }
    }
    */
    let configFieldIdx = 0 // For config management

    // Iterate through field headers
    while (j < headerIdx + topHeader.colspan) {
      let editConfigField: StudyEditConfigNodeField | null | undefined
      const fieldHeader = table.field_header[j]
      if (!fieldHeader) continue
      let fieldEditable = false
      const maxValueLen: number = fieldHeader.max_value_len
      const colType = fieldHeader.col_type || ''
      let colAlign: string = 'left'
      if (['UNIT', 'NUMERIC'].includes(colType)) colAlign = 'right'

      // Get column width
      const colWidthRes = getColWidth(
        j,
        colType,
        maxValueLen,
        table.col_last_vis,
        params.sodarContext.min_col_width,
        params.sodarContext.max_col_width)
      const colWidth = colWidthRes[0]
      const minColWidth = colWidthRes[1]

      // Get editFieldConfig if editing
      if (params.editMode && params.studyEditConfig) {
        editConfigField = getEditConfigField(
          tableUuid, assayMode, i, fieldHeader, params.studyEditConfig)
      }
      if (editConfigField &&
          'editable' in editConfigField &&
          editConfigField.editable !== undefined) {
        fieldEditable = editConfigField.editable
      }
      // if (params.editMode) fieldEditable = true // DEBUG

      // Get field column visibility
      const fieldVisible = getFieldVisibility(
        tableUuid,
        i,
        assayMode,
        studySection,
        fieldHeader,
        fieldEditable,
        table.col_values[j],
        params.studyDisplayConfig)

      // Create field column header
      const header = getFieldHeader(
        fieldHeader,
        j,
        colAlign,
        colWidth,
        minColWidth,
        fieldEditable,
        fieldVisible,
        params.editMode,
        params.sodarContext.external_link_labels as {
          [key: string]: string | SodarContextLinkLabel })

      // Make source name column pinned, disable hover
      // HACK: also create new header group to avoid name duplication
      if (j === 0) {
        header.pinned = 'left'
        header.cellRendererParams.enableHover = false
        headerGroup.children.push(header)
        colDef.push(headerGroup)
        headerGroup = {
          headerName: '',
          headerClass: ['bg-' + topHeader.colour],
          children: []
        }
      }

      // Update header for edit mode
      if (params.editMode) {
        // Set header renderer for fields we can manage
        // TODO: This perm check should be redundant now?
        if (params.sodarContext.perms.edit_sheet) {
          header.headerComponent = 'HeaderEditRenderer'
          header.headerComponentParams = getHeaderEditRendererParams(
            tableUuid,
            assayMode,
            fieldHeader,
            i,
            editConfigField as StudyEditConfigNodeField,
            configFieldIdx,
            params.studyNodeLen,
            fieldEditable,
            params.colConfigModal as TemplateRef,
            params.notifyCb
          )
          header.width = header.width! + 20 // Fit button in header
          header.minWidth = header.minWidth! + 20
        }

        // Set up field editing
        if (editConfigField) {
          // Allow overriding field editability cell-by-cell
          header.editable = function (p) {
            const field = p.colDef.field as string
            if (field in p.node.data &&
                'editable' in p.node.data[field]) {
              return p.node.data[field].editable
            } else if ('headerComponentParams' in p.colDef) {
              return p.colDef.headerComponentParams.editable
            } else return false
          }
          // Set up cell editor selector
          header.cellEditorSelector = getCellEditor
          // Set default cellEditorParams (may be updated in the selector)
          header.cellEditorParams = {
            assayMode: assayMode,
            colAlign: colAlign,
            colWidth: colWidth,
            editConfigField: editConfigField,
            fieldHeader: fieldHeader,
            fieldId: header.field,
            notifyCb: params.notifyCb,
            ontologyEditModal: params.ontologyEditModal,
            sampleColId: params.sampleColId,
            tableUuid: tableUuid
          } as CellEditorParamInput
        }
      }
      if (j > 0) headerGroup.children.push(header)
      j++
      configFieldIdx += 1
    }

    headerIdx = j
    colDef.push(headerGroup)
    if (topHeader.value === 'Sample') studySection = false
  }

  // Study shortcut column
  if (!params.editMode && !assayMode && 'shortcuts' in table) {
    colDef.push(getStudyShortcutHeaderGroup(
        table as StudyRenderTable, params.studyShortcutModal))
  }
  // Assay iRODS button column
  if (!params.editMode && assayMode) {
    const assayContext = params.sodarContext.studies[
      params.studyUuid]?.assays[tableUuid]
    if (params.sodarContext.irods_status &&
        assayContext?.display_row_links) {
      colDef.push(getAssayIrodsHeaderGroup(
        params.sodarContext, assayContext, params.irodsDirModal))
    }
  }
  // Row editing column
  if (params.editMode) {
    colDef.push(getRowEditHeaderGroup())
  }
  return colDef
}

// Build row data for a study/assay grid
export function buildRowData (
    table: AssayRenderTable | StudyRenderTable,
    assayMode: boolean,
    editMode: boolean,
    sodarContext: SodarContext
) {
  const rowData = []
  // Iterate through input rows
  for (let i = 0; i < table.table_data.length; i++) {
    const rowCells = table.table_data[i]
    const row: SheetTableRowData = { 'rowNum': i + 1 }
    let nodeUuid = null
    for (let j = 0; j < rowCells!.length; j++) {
      // HACK: Reformat protocol UUID reference
      const cellInput = rowCells![j]
      let uuidRef: string = ''
      if (editMode && cellInput && 'uuid_ref' in cellInput) {
        uuidRef = cellInput.uuid_ref as string
        delete cellInput.uuid_ref
      }
      const cellData = rowCells![j] as SheetTableCellData
      if (uuidRef) cellData.uuidRef = uuidRef

      // Set node UUID
      if ('uuid' in cellData && cellData.uuid) {
        nodeUuid = cellData.uuid // Get node UUID from first node cell
      } else cellData.uuid = nodeUuid as string // Set node UUID to other cells

      // Set user friendly ontology accession URL
      if (sodarContext.ontology_url_template &&
          !editMode &&
          table.field_header[j]?.col_type === 'ONTOLOGY') {
        for (const term of (cellData.value as Array<SheetTableOntologyRef>)) {
          if (term.accession &&
              sodarContext.ontology_url_skip &&
              !sodarContext.ontology_url_skip.some(
                x => term.accession.includes(x))) {
            let ontologyName = term.ontology_name
            // HACK for mislabeled HP terms
            if (ontologyName === 'HPO') ontologyName = 'HP'
            let url = sodarContext.ontology_url_template
            url = url.replace('{ontology_name}', ontologyName as string)
            url = url.replace('{accession}', encodeURIComponent(term.accession))
            term.accession = url
          }
        }
      }
      row['col' + j.toString()] = cellData
    }
    // Add study shortcut column cell
    if (!editMode &&
        !assayMode &&
        'shortcuts' in table &&
        table.shortcuts &&
        table.shortcuts.data) {
      row.shortcutLinks = (
        table.shortcuts as unknown as StudyShortcut
      ).data[i] as StudyShortcutCell
    }
    // Add iRODS column cell
    if (!editMode &&
        sodarContext.irods_status &&
        'irods_paths' in table &&
        table.irods_paths.length > 0) {
      row.irodsLinks = table.irods_paths[i] as AssayIrodsPath
    }
    rowData.push(row)
  }
  return rowData
}

/* Cell data handling ------------------------------------------------------- */

// Get flat value for comparator
export function getFlatValue (
  value: Array<never> | number | object | string
): number | object | string {
  if (Array.isArray(value) && value.length > 0) {
    if (typeof value[0] === 'object' && 'name' in value[0]) {
      return value.map(d => d.name).join(';')
    } else return value.join(';')
  }
  return value
}

// Compare data cell values
export function compareDataCellValues (
  dataA: SheetTableCellData,
  dataB: SheetTableCellData
): number {
  const valueA = getFlatValue(dataA.value) as string
  const valueB = getFlatValue(dataB.value) as string
  const floatA = parseFloat(valueA)
  const floatB = parseFloat(valueB)
  if (!isNaN(floatA) && !isNaN(floatB)) return floatA - floatB
  return valueA.localeCompare(valueB)
}

// Custom filter value for data cells (fix for #686)
export function getDataCellFilterValue (
  params: ValueGetterParams
): number | object | string {
  return getFlatValue(params.data[params.column.getColId() as string].value)
}
