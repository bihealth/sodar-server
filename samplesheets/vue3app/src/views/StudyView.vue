<script setup lang="ts">
import { nextTick, onMounted, useTemplateRef, watch } from 'vue'
import { useRoute } from 'vue-router'
import {
  type CellClassParams,
  type ColDef,
  type ColGroupDef
} from 'ag-grid-community'

import AssayShortcutCard from '@/components/AssayShortcutCard.vue'
import ColumnToggleModal from '@/components/modals/ColumnToggleModal.vue'
import DataCellRenderer from '@/components/renderers/DataCellRenderer.vue'
import IrodsButtonsRenderer from '@/components/renderers/IrodsButtonsRenderer.vue'
import IrodsDirModal from '@/components/modals/IrodsDirModal.vue'
import SheetTable from '@/components/SheetTable.vue'
import SheetTableHeader from '@/components/SheetTableHeader.vue'
import StudyShortcutModal from '@/components/modals/StudyShortcutModal.vue'
import StudyShortcutsRenderer from '@/components/renderers/StudyShortcutsRenderer.vue'
import WaitSection from '@/components/WaitSection.vue'
import {
  initGridOptions,
  compareDataCellValues,
  getDataCellFilterValue
} from '@/gridutils.ts'
import {
  type AssayIrodsPath,
  type AssayRenderTable,
  type AssayShortcuts,
  type RenderTableData,
  type StudyDisplayConfigNode,
  type StudyEditConfigNodeField,
  type StudyRenderTable,
  type SheetTableFieldHeader,
  type SheetTableOntologyRef,
  type SheetTableCellData,
  type SheetTableRowData,
  type StudyEditConfig,
  type StudyShortcut,
  type StudyShortcutCell
} from '@/types.ts'
import { type SodarContextAssay, useAppStore } from '@/stores/appstore.ts'
import { useTableStore } from '@/stores/tablestore.ts'

// Set up route
const route = useRoute()

// Set up stores
const appStore = useAppStore()
const tableStore = useTableStore()

// Set up template references
const columnToggleCompRef = useTemplateRef('columnToggleModalComponent')
const irodsDirCompRef = useTemplateRef('irodsDirModalComponent')
const studyShortcutCompRef = useTemplateRef('studyShortcutModalComponent')

// Expose components for ag-grid
defineExpose({
  DataCellRenderer,
  IrodsButtonsRenderer,
  StudyShortcutsRenderer
})

/* General helpers ---------------------------------------------------------- */

async function scrollToCurrentTable () {
  await nextTick() // Ensure DOM is rendered
  if (appStore.gridsLoaded && 'assayUuid' in route.params) {
    const anchorId = 'assay-anchor-' + route.params.assayUuid
    const anchorElem = document.getElementById(anchorId)
    if (anchorElem) anchorElem.scrollIntoView()
  } else {
    const anchorElem = document.getElementsByClassName('sodar-app-container')[0]
    if (anchorElem) anchorElem.scrollTop = 0
  }
}

/* Study building helpers --------------------------------------------------- */

// Return header group ColGroupDef for row number column
function getRowNumHeaderGroup (): ColGroupDef {
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
function getStudyShortcutHeaderGroup (table: StudyRenderTable): ColGroupDef {
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
          cellRenderer: 'StudyShortcutsRenderer',
          cellRendererParams: {
            schema: table.shortcuts?.schema,
            modalRef: studyShortcutCompRef
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
          width: 40 * Object.keys(table.shortcuts?.schema || {}).length
        }
      ]
    }
}

// Return header group ColGroupDef for assay iRODS column
function getAssayIrodsHeaderGroup (
    assayContext: SodarContextAssay
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
        cellRenderer: 'IrodsButtonsRenderer',
        cellRendererParams: {
          assayIrodsPath: assayContext.irods_path,
          irodsStatus: appStore.sodarContext!.irods_status,
          irodsBackendEnabled: appStore.sodarContext!.irods_backend_enabled,
          irodsWebdavUrl: appStore.sodarContext!.irods_webdav_url,
          modalRef: irodsDirCompRef
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
function getRowEditHeaderGroup (): ColGroupDef {
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
function getColWidth (
    colIdx: number,
    colType: string,
    maxValueLen: number,
    lastVis: number
): [number, number] {
  let minW: number = appStore.sodarContext!.min_col_width
  const maxW: number = appStore.sodarContext!.max_col_width
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
function getFieldVisibility (
    tableUuid: string,
    topIdx: number,
    assayMode: boolean,
    studySection: boolean,
    fieldHeader: SheetTableFieldHeader,
    fieldEditable: boolean,
    colValues: number | undefined
): boolean {
  let displayConfig
  if (tableStore.studyDisplayConfig) {
    let displayNode: StudyDisplayConfigNode | undefined
    if (!assayMode) {
      displayNode = tableStore.studyDisplayConfig.nodes[topIdx]
    } else {
      displayNode = tableStore.studyDisplayConfig.assays[
        tableUuid]!.nodes[topIdx]
    }
    if (displayNode) {
      for (let k = 0; k < displayNode.fields.length; k++) {
        const f = displayNode.fields[k]
        if (f!.name === fieldHeader.name) {
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
function getFieldEditConfig (
    tableUuid: string,
    assayMode: boolean,
    topIdx: number,
    fieldHeader: SheetTableFieldHeader,
): StudyEditConfigNodeField | undefined {
  let editNode = null
  const studyNodeLen = tableStore.studyEditConfig?.nodes.length
  if (!studyNodeLen) return undefined
  if (!assayMode || topIdx < studyNodeLen) {
    editNode = tableStore.studyEditConfig?.nodes[topIdx]
  } else {
    editNode = tableStore.studyEditConfig?.assays[tableUuid]?.nodes[
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
function getFieldHeaderDef (
    fieldHeader: SheetTableFieldHeader,
    fieldIdx: number,
    colAlign: string,
    colWidth: number,
    minColWidth: number,
    fieldEditable: boolean,
    fieldVisible: boolean,
): ColDef {
  const header: ColDef = {
      headerName: fieldHeader.value,
      field: 'col' + fieldIdx.toString(),
      width: colWidth,
      minWidth: minColWidth,
      hide: !fieldVisible,
      headerClass: ['sodar-ss-data-header'],
      cellRenderer: 'DataCellRenderer',
      cellRendererParams: {
        colType: fieldHeader.col_type,
        editMode: appStore.editMode,
        fieldEditable: fieldEditable, // Needed here to update cellClass
        linkLabels: appStore.sodarContext?.external_link_labels
      }, // NOTE: app omitted
      comparator: compareDataCellValues,
      context: {},
      filterValueGetter: getDataCellFilterValue
    }

    // Cell classes
    if (!appStore.editMode) {
      header.cellClass = ['sodar-ss-data-cell', 'text-' + colAlign]
    } else {
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
    }
  return header
}


/* Study building API ------------------------------------------------------- */

// Build column definitions for a study/assay grid
// TODO: Split this into multiple functions and simplify (ongoing)
function buildColDef (
    table: AssayRenderTable | StudyRenderTable,
    tableUuid: string,
    assayMode: boolean
): Array<ColGroupDef> {
  // Default columns
  const colDef: Array<ColGroupDef> = []

  // Set up row column header group
  const rowHeaderGroup = getRowNumHeaderGroup()
  // Editing: gray out row column to avoid confusion
  if (appStore.editMode) {
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
    const topHeader = table.top_header[i]
    if (!topHeader) continue // To get rid of ts errors. Better ideas?
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
    // let configFieldIdx = 0 // For config management

    // Iterate through field headers
    while (j < headerIdx + topHeader.colspan) {
      let fieldEditConfig: StudyEditConfigNodeField | null | undefined
      const fieldHeader = table.field_header[j]
      if (!fieldHeader) continue
      let fieldEditable = false
      const maxValueLen: number = fieldHeader.max_value_len
      const colType = fieldHeader.col_type || ''
      let colAlign: string = 'left'
      if (['UNIT', 'NUMERIC'].includes(colType)) colAlign = 'right'

      // Get column width
      const colWidthRes = getColWidth(
        j, colType, maxValueLen, table.col_last_vis)
      const colWidth = colWidthRes[0]
      const minColWidth = colWidthRes[1]

      // Get editFieldConfig if editing
      if (appStore.editMode && tableStore.studyEditConfig) {
        fieldEditConfig = getFieldEditConfig(
          tableUuid, assayMode, i, fieldHeader)
      }
      if (fieldEditConfig &&
          'editable' in fieldEditConfig &&
          fieldEditConfig.editable !== undefined) {
        fieldEditable = fieldEditConfig.editable
      }

      // Get field column visibility
      const fieldVisible = getFieldVisibility(
        tableUuid,
        i,
        assayMode,
        studySection,
        fieldHeader,
        fieldEditable,
        table.col_values[j])

      // Create field column header
      const header = getFieldHeaderDef(
        fieldHeader,
        j,
        colAlign,
        colWidth,
        minColWidth,
        fieldEditable,
        fieldVisible)

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
      /* TODO: Refactor and re-enable once adding edit mode support

      if (appStore.editMode) {
        // Set header renderer for fields we can manage
        if (appStore.getPerm('edit_sheet')) {
          let configAssayUuid = assayMode ? tableUuid : null
          let configNodeIdx = i
          if (assayMode) {
            const studyNodeLen = tableStore.columnDefs.study.length - 3
            if (configNodeIdx < studyNodeLen) configAssayUuid = null
            else configNodeIdx = i - studyNodeLen
          }

          header.headerComponent = 'HeaderEditRenderer'
          header.headerComponentParams = {
            app: params.app,
            modalComponent: params.app.$refs.columnConfigModal,
            colType: colType,
            fieldConfig: fieldEditConfig,
            assayUuid: configAssayUuid,
            configNodeIdx: configNodeIdx,
            configFieldIdx: configFieldIdx,
            editable: fieldEditable, // Add here to allow checking by cell
            headerType: fieldHeader.type,
            assayMode: params.assayMode, // Needed for sample col in assay
            canEditConfig: params.sodarContext.perms.edit_sheet
          }
          header.width = header.width + 20 // Fit button in header
          header.minWidth = header.minWidth + 20
        }

        // Set up field editing
        if (fieldEditConfig) {
          // Allow overriding field editability cell-by-cell
          header.editable = function (p) {
            if (p.colDef.field in p.node.data &&
                'editable' in p.node.data[p.colDef.field]) {
              return p.node.data[p.colDef.field].editable
            } else if ('headerComponentParams' in p.colDef) {
              return p.colDef.headerComponentParams.editable
            } else return false
          }

          // Set up cell editor selector
          header.cellEditorSelector = function (p) {
            let editorName = 'DataCellEditor'
            // TODO: Refactor so that default params are read from header
            const editorParams = Object.assign(p.colDef.cellEditorParams)
            const editContext = params.editContext

            // If sample name in an assay or an object ref, return selector
            // TODO: Simplify?
            if (p.colDef.headerComponentParams.assayMode &&
                p.column.originalParent.colGroupDef.headerName === 'Sample' &&
                p.colDef.headerName === 'Name' &&
                'newRow' in p.value &&
                p.value.newRow) {
              editorName = 'ObjectSelectEditor'
              editorParams.selectOptions = editContext.samples
            } else if (editorParams.headerInfo.header_type === 'protocol') {
              editorName = 'ObjectSelectEditor'
              editorParams.selectOptions = Object.assign(editContext.protocols)
            } else if (colType === 'ONTOLOGY') {
              editorName = 'OntologyEditor'
              editorParams.sodarOntologies = editContext.sodar_ontologies
            }

            return { component: editorName, params: editorParams }
          }

          // Set default cellEditorParams (may be updated in the selector)
          header.cellEditorParams = {
            app: params.app,
            // Header information to be passed for calling server
            headerInfo: {
              header_name: fieldHeader.name,
              header_type: fieldHeader.type,
              header_field: header.field, // For updating other cells
              obj_cls: fieldHeader.obj_cls
            },
            renderInfo: { align: colAlign, width: colWidth },
            editConfig: fieldEditConfig, // Editor configuration
            gridUuid: params.gridUuid, // TODO: Could get this from header params
            sampleColId: params.sampleColId
          }

          // Add item type to generic material name
          if (fieldHeader.obj_cls === 'GenericMaterial' &&
              fieldHeader.type === 'name') {
            header.cellEditorParams.headerInfo.item_type = fieldHeader.item_type
          }
        }
      }
      */
      if (j > 0) headerGroup.children.push(header)
      j++
      // configFieldIdx += 1
    }

    headerIdx = j
    colDef.push(headerGroup)
    if (topHeader.value === 'Sample') studySection = false
  }

  // Study shortcut column
  if (!appStore.editMode && !assayMode && 'shortcuts' in table) {
    colDef.push(getStudyShortcutHeaderGroup(table as StudyRenderTable))
  }
  // Assay iRODS button column
  if (!appStore.editMode && assayMode) {
    const assayContext = appStore.sodarContext?.studies[
      appStore.currentStudyUuid]?.assays[tableUuid]
    if (appStore.sodarContext!.irods_status &&
        assayContext?.display_row_links) {
      colDef.push(getAssayIrodsHeaderGroup(assayContext))
    }
  }
  // Row editing column
  // TODO: Implement as helper
  if (appStore.editMode) {
    colDef.push(getRowEditHeaderGroup())
  }
  return colDef
}

// Build row data for a study/assay grid
function buildRowData (
    table: AssayRenderTable | StudyRenderTable,
    assayMode: boolean
) {
  const rowData = []
  // Iterate through input rows
  for (let i = 0; i < table.table_data.length; i++) {
    const rowCells = table.table_data[i]
    const row: SheetTableRowData = { 'rowNum': i + 1 }
    let nodeUuid = null
    for (let j = 0; j < rowCells!.length; j++) {
      const cellData = rowCells![j] as SheetTableCellData

      // Set node UUID
      if ('uuid' in cellData && cellData.uuid) {
        nodeUuid = cellData.uuid // Get node UUID from first node cell
      } else cellData.uuid = nodeUuid as string // Set node UUID to other cells

      // Copy col_type info to each cell (comparator can't access colDef)
      cellData.colType = table.field_header[j]?.col_type as string

      // Set user friendly ontology accession URL
      if (appStore.sodarContext?.ontology_url_template &&
          !appStore.editMode &&
          cellData.colType === 'ONTOLOGY') {
        for (const term of (cellData.value as Array<SheetTableOntologyRef>)) {
          if (term.accession &&
              appStore.sodarContext?.ontology_url_skip &&
              !appStore.sodarContext.ontology_url_skip.some(
                x => term.accession.includes(x))) {
            let ontologyName = term.ontology_name
            // HACK for mislabeled HP terms
            if (ontologyName === 'HPO') ontologyName = 'HP'
            let url = appStore.sodarContext.ontology_url_template
            url = url.replace('{ontology_name}', ontologyName as string)
            url = url.replace('{accession}', encodeURIComponent(term.accession))
            term.accession = url
          }
        }
      }
      row['col' + j.toString()] = cellData
    }
    // Add study shortcut column cell
    if (!appStore.editMode &&
        !assayMode &&
        'shortcuts' in table &&
        table.shortcuts &&
        table.shortcuts.data) {
      row.shortcutLinks = (
        table.shortcuts as unknown as StudyShortcut
      ).data[i] as StudyShortcutCell
    }
    // Add iRODS column cell
    if (!appStore.editMode &&
        appStore.sodarContext?.irods_status &&
        'irods_paths' in table &&
        table.irods_paths.length > 0) {
      row.irodsLinks = table.irods_paths[i] as AssayIrodsPath
    }
    rowData.push(row)
  }
  return rowData
}


function buildStudy (data: RenderTableData) {
  // TODO: Handle render_error
  if (appStore.editMode && 'study_config' in data) {
    tableStore.studyEditConfig = data.study_config as StudyEditConfig
  }
  // TODO: Set up editContext
  tableStore.tableHeights = data.table_heights
  tableStore.studyDisplayConfig = data.display_config
  tableStore.sourceColSpan = data.tables.study.top_header[0]?.colspan || -1

  // Store sampleColId & sampleIdx
  let colSpan = 0
  for (let i = 0; i < data.tables.study.top_header.length; i++) {
    if (data.tables.study.top_header[i]?.value === 'Sample') {
      tableStore.sampleColId = 'col' + colSpan
      tableStore.sampleIdx = colSpan + 1
      break
    }
    colSpan += data.tables.study.top_header[i]?.colspan || 1
  }

  // Build study gridOptions, columnDefs and rowData
  // TODO: Setup context for gridOptions if needed
  tableStore.gridOptions.study = initGridOptions({}, appStore.editMode)
  tableStore.columnDefs.study = buildColDef(
      data.tables.study, appStore.currentStudyUuid, false
  )
  tableStore.rowData.study = buildRowData(data.tables.study, false)

  for (const assayUuid in data.tables.assays) {
    // Build assay gridOptions, columnDefs and rowData
    tableStore.gridOptions.assays[assayUuid] = initGridOptions(
      {}, appStore.editMode)
    const assayTable = data.tables.assays[assayUuid] as AssayRenderTable
    tableStore.columnDefs.assays[assayUuid] = buildColDef(
        assayTable, assayUuid, true)
    tableStore.rowData.assays[assayUuid] = buildRowData(assayTable, true)

    // Get assay shortcuts
    if ('shortcuts' in (data.tables.assays[assayUuid] as AssayRenderTable)) {
      tableStore.assayShortcuts[
        assayUuid] = (
          (data.tables.assays[assayUuid] as AssayRenderTable)
            .shortcuts as AssayShortcuts)
    }
  }
}

function getStudy (studyUuid: string, editMode: boolean) {
  // Clear existing data
  appStore.gridsBusy = true
  appStore.gridsLoaded = false
  tableStore.$reset()
  // TODO: Clear edit data once implemented
  // TODO: Set filter state

  // Retrieve study tables
  let url: string = appStore.sodarContext!.studies[studyUuid]!.table_url
  if (editMode) url += '?edit=1'
  // TODO: Add timeout / retrying / error handling
  fetch(url, { credentials: 'same-origin' })
    .then(data => data.json())
    .then(data => {
      buildStudy(data)
      appStore.gridsBusy = false
      appStore.gridsLoaded = true
      scrollToCurrentTable()
    })
}

// Update current study UUID based on route
if ('studyUuid' in route.params &&
    appStore.currentStudyUuid !== route.params.studyUuid) {
  appStore.currentStudyUuid = route.params.studyUuid!.toString()
}
// Get initial study once sodarContext is retrieved
if (appStore.sheetsAvailable && !appStore.gridsLoaded) {
  getStudy(appStore.currentStudyUuid, appStore.editMode)
} else {
  watch(() => appStore.sodarContext, (newContext) => {
    if (newContext !== null && appStore.sheetsAvailable) {
      getStudy(appStore.currentStudyUuid, appStore.editMode)
    }
  })
}
// Get new study when study UUID or edit mode are updated
watch(() =>
    [appStore.currentStudyUuid, appStore.editMode],
    ([newUuid, newEditMode]) => {
  getStudy(newUuid as string, newEditMode as boolean)
})
onMounted(() => {
  // Scroll to current table on load
  if (appStore.gridsLoaded) {
    scrollToCurrentTable()
  }
})
</script>

<template>
  <div v-if="!appStore.gridsBusy && appStore.gridsLoaded">
    <!-- Study -->
    <SheetTableHeader
        :table-uuid="appStore.currentStudyUuid"
        :assay-mode="false">
    </SheetTableHeader>
    <SheetTable
        :assay-mode="false"
        :col-toggle-modal-ref="columnToggleCompRef"
        :table-uuid="appStore.currentStudyUuid">
    </SheetTable>
    <!-- Assays -->
    <div v-for="assayUuid in
                Object.keys(appStore.sodarContext!.studies[
                  appStore.currentStudyUuid]!.assays)"
         :key="assayUuid">
      <a class="sodar-ss-anchor"
         :id="'assay-anchor-' + assayUuid.toString()"></a>
      <SheetTableHeader
          :table-uuid="assayUuid"
          :assay-mode="true">
      </SheetTableHeader>
      <AssayShortcutCard
          v-if="!appStore.editMode &&
                appStore.getPerm('view_files') &&
                appStore.sodarContext!.irods_status &&
                assayUuid in tableStore.assayShortcuts"
          :assay-uuid="assayUuid"
          :modal-ref="irodsDirCompRef">
      </AssayShortcutCard>
      <SheetTable
          :assay-mode="true"
          :col-toggle-modal-ref="columnToggleCompRef"
          :table-uuid="assayUuid">
      </SheetTable>
    </div>
  </div>
  <div v-else-if="appStore.sodarContext && !appStore.sheetsAvailable">
    <div class="alert alert-info" id="sodar-ss-alert-empty">
      No sample sheets are currently available for this project.
      <span v-if="appStore.getPerm('edit_sheet') &&
                  !appStore.sodarContext!.sheet_sync_enabled">
        To add sample sheets, please import them from an existing ISA-Tab
        investigation, create new sheets from a template or enable remote
        sheet synchonization.
      </span>
      <span v-if="appStore.getPerm('edit_sheet') &&
                  appStore.sodarContext!.sheet_sync_enabled">
        To add sample sheets, please wait for the synchonization to take
        place or trigger the synchonization manually.
      </span>
    </div>
  </div>
  <WaitSection v-else></WaitSection>
  <!-- Modals -->
  <IrodsDirModal
      id="sodar-ss-irods-dir-modal-component"
      ref="irodsDirModalComponent">
  </IrodsDirModal>
  <StudyShortcutModal
      id="sodar-ss-study-shortcut-modal-component"
      ref="studyShortcutModalComponent">
  </StudyShortcutModal>
  <ColumnToggleModal
      id="sodar-ss-column-toggle-modal-component"
      ref="columnToggleModalComponent">
  </ColumnToggleModal>
</template>

<style scoped>
</style>
