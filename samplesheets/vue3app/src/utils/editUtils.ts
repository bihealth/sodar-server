// API and helpers for sample sheet editing

import {
  type ColDef,
  type Column,
  type GridApi,
  type IRowNode
} from 'ag-grid-community'

import { useAppStore } from '@/stores/appStore.ts'
import { useEditStore } from '@/stores/editStore.ts'
import { useTableStore } from '@/stores/tableStore.ts'
import { getAjaxRequestInit } from '@/utils/appUtils.ts'
import {
  type CellDefaultParams,
  type CellEditData,
  type EditRequestCell,
  type GenericResponseBody,
  // type HeaderEditRendererParams,
  type NewRowData,
  type NodeEnableParams,
  type NodeUpdateParams,
  type NotifyCb,
  type RowInsertParams,
  type RowDeleteData,
  type RowDeleteParams,
  type RowSaveCellParams,
  type RowSaveData,
  type RowSaveDataCell,
  type RowSaveDataNode,
  type RowSaveDataParams,
  type RowSaveParams,
  type SheetTableCellData,
  type SheetTableFieldHeader,
  type StudyEditConfigNodeField,
} from '@/types.ts'
import {
  AJAX_RES_OK,
  DB_OBJ_CLASS_MATERIAL,
  DB_OBJ_CLASS_PROCESS,
  EDIT_COL_TYPE_ONTOLOGY,
  EDIT_FORMAT_PROTOCOL,
  EDIT_HEADER_TYPE_NAME,
  EDIT_HEADER_TYPE_PROCESS,
  EDIT_HEADER_TYPE_PROTOCOL,
  EDIT_ITEM_TYPE_DATA,
  EDIT_ITEM_TYPE_SAMPLE,
  EDIT_ITEM_TYPE_SOURCE,
  HEADER_NAME_SAMPLE,
  NODE_ID_HEADER_TYPES,
  URL_ROW_DEL_PREFIX,
  URL_ROW_INS_PREFIX,
  VARIANT_DANGER,
  VARIANT_SUCCESS,
} from '@/constants.ts'

export function deleteRow (params: RowDeleteParams) {
  const appStore = useAppStore()
  const editStore = useEditStore()
  const tableStore = useTableStore()

  // Unsaved row: simply remove from grid
  const newRow: boolean = editStore.unsavedRow !== null &&
    editStore.unsavedRow.tableUuid === params.tableUuid &&
    editStore.unsavedRow.id === params.rowNode.id
  if (newRow) {
    params.api.applyTransaction({ remove: [params.rowNode.data] })
    editStore.unsavedRow = null
    return
  }

  // Else update row in database
  editStore.updatingRow = true
  const delUrl = URL_ROW_DEL_PREFIX + appStore.projectUuid as string

  const rowData: RowDeleteData = {
    assay: params.assayMode ? params.tableUuid : null,
    nodes: [],
    study: appStore.currentStudyUuid
  }
  const cols = params.api.getColumns()
  if (!cols) return
  let startIdx = 1
  let currentNodeUuid = null
  if (params.assayMode) startIdx = tableStore.sampleIdx
  for (let i = startIdx; i < cols.length - 1; i++) {
    const cell = params.rowNode.data[cols![i]!.getColId() as string]
    if ('uuid' in cell && cell.uuid && cell.uuid !== currentNodeUuid) {
      rowData.nodes.push({
        obj_cls: cols![i]!.getColDef().cellEditorParams.fieldHeader.obj_cls,
        uuid: cell.uuid,
      })
      currentNodeUuid = cell.uuid
    }
  }

  fetch(delUrl, getAjaxRequestInit('POST', { del_row: rowData }))
  .then(res => res.json())
  .then(res => {
    if ((res as GenericResponseBody).detail === AJAX_RES_OK) {
      editStore.editDataUpdated = true

      // Update sample list
      const sc: string = tableStore.sampleColId
      const su: string = params.rowNode.data[sc].uuid
      let sFound: boolean = false
      params.api.forEachNode(function (r) {
        if (r.data[sc].uuid === su && r.id !== params.rowNode.id) sFound = true
      })
      if (params.assayMode &&
          editStore.editContext!.samples[su]!.assays.includes(
            params.tableUuid) &&
          !sFound) {
        // Remove assay table UUID from sample list for the sample
        editStore.editContext!.samples[su]!.assays =
          editStore.editContext!.samples[su]!.assays.filter(
            v => v !== params.tableUuid)
      } else if (!params.assayMode && !sFound) {
        // Delete sample from editContext if deleted from study
        delete editStore.editContext!.samples[su]
      }

      // Update grid and row numbers
      params.api.applyTransaction({ remove: [params.rowNode.data] })
      let rowNum = 1
      params.api.forEachNode(function (r) {
        r.setDataValue('rowNum', rowNum)
        rowNum += 1
      })
      if (params.notifyCb) params.notifyCb('Row deleted', VARIANT_SUCCESS)
    } else {
      const msg = 'Row delete failed'
      console.error(
        `${msg}: ${(res as GenericResponseBody).detail}`)
      if (params.notifyCb) params.notifyCb(msg, VARIANT_DANGER)
    }
    if (params.finishCb) params.finishCb()
    editStore.updatingRow = false
  }) // TODO: Catch and handle fetch() error
}

// Enable editing for next node(s) when inserting a new row
// TODO: Refactor and simplify once fully tested
export function enableNextNodes (params: NodeEnableParams) {
  const appStore = useAppStore()
  // TODO: Add assayMode in params?
  const assayMode: boolean = params.tableUuid !== appStore.currentStudyUuid
  const cols: Array<Column> = params.api.getColumns() as Array<Column>
  const col: Column = cols![params.startIdx] as Column
  let colId: string = col.getColId()
  let colDef: ColDef = col.getColDef()

  let cellData: SheetTableCellData
  let headerType: string
  let itemType: string

  // Only enable node(s) if they are in newInit mode
  if (!params.rowNode.data[colId].newInit) return
  // Last column before edit column = nothing to do
  if (params.startIdx >= cols!.length - 1) return

  const groupId: string = col.getOriginalParent()!.getGroupId()
  const objCls: string = colDef.cellEditorParams.fieldHeader.obj_cls
  let enableNextIdx: number | null = null

  if (objCls === DB_OBJ_CLASS_MATERIAL) {
    // If the next node is a material, enable editing its name
    headerType = colDef.cellEditorParams.fieldHeader.type
    itemType = colDef.cellEditorParams.fieldHeader.item_type
    cellData = getDefaultCellData({
      api: params.api,
      colId: colId,
      newInit: true
    })
    cellData.editable = true // TODO: Set this in getDefaultCellData()?

    // If default name suffix is set, fill name, enable node and continue
    // NOTE: Returned value for name column = suffix is set in config
    if (headerType == EDIT_HEADER_TYPE_NAME &&
        ![EDIT_ITEM_TYPE_DATA, EDIT_ITEM_TYPE_SOURCE].includes(itemType) &&
        cellData.value) {
      cellData.value = getNamePrefix(
        params.rowNode, cols, params.startIdx) + cellData.value
      let createNew: boolean = true
      // Check if name already appears in column, update UUID if found
      params.api.forEachNode(function (r) {
        if (r.data[colId].value === cellData.value) {
          createNew = false
          cellData.uuid = r.data[colId].uuid
        }
      })
      cellData.newInit = false
      params.rowNode.setDataValue(colId, cellData)
      updateNode({
        api: params.api,
        assayMode: assayMode,
        column: col,
        createNew: createNew,
        nameCellData: cellData,
        rowNode: params.rowNode,
        tableUuid: params.tableUuid
      })
      return
    }
    // Else set empty value
    if (itemType == EDIT_ITEM_TYPE_DATA) {
      cellData.newInit = false // Empty name is OK for data
    }
    params.rowNode.setDataValue(colId, cellData)

    // Immediately enable next node after a data node (name can be blank)
    if (itemType == EDIT_ITEM_TYPE_DATA) {
      for (let i = params.startIdx + 1; i < cols.length - 1; i++) {
        if (cols[i]!.getOriginalParent()!.getGroupId() !== groupId) {
          enableNextIdx = i // Set next node start index and break from loop
          break
        }
        // While in current node, set default data
        const colId = cols[i]!.getColId()
        cellData = getDefaultCellData({
          api: params.api,
          colId: colId,
          newInit: false,
          forceEmpty: true
        })
        // NOTE: The following was false in vueapp, seems wrong?
        cellData.editable = true
        params.rowNode.setDataValue(colId, cellData)
      }
    }
  } else if (objCls === DB_OBJ_CLASS_PROCESS) {
    // Enable process, handle protocol and possible process name
    let i = params.startIdx
    let processActive = false
    let newInit = true
    let forceEmpty = false

    while (i < cols.length - 1 &&
        cols[i]!.getOriginalParent()!.getGroupId() === groupId) {
      colId = cols[i]!.getColId()
      colDef = cols[i]!.getColDef()
      cellData = getDefaultCellData({
        api: params.api,
        colId: colId,
        newInit: newInit,
        forceEmpty: forceEmpty
      })
      headerType = colDef.cellEditorParams.fieldHeader.type
      const fieldEditable = colDef.cellRendererParams.fieldEditable

      if (headerType === EDIT_HEADER_TYPE_PROTOCOL) {
        cellData.editable = fieldEditable
        if (cellData.uuidRef) {
          processActive = true
          newInit = false
          cellData.newInit = false
        } else forceEmpty = true
      } else if (headerType === EDIT_HEADER_TYPE_PROCESS) {
        cellData.editable = true // Process name should always be editable
        // Fill process name with default suffix if set
        const namePrefix = getNamePrefix(params.rowNode, cols, i)
        if (cellData.value && namePrefix) {
          cellData.value = namePrefix + cellData.value
          // TODO: Remove repetition
          let createNew: boolean = true
          // Update UUID if found
          params.api.forEachNode(function (r) {
            if (r.data[colId].value === cellData.value) {
              createNew = false
              cellData.uuid = r.data[colId].uuid
            }
          })
          newInit = false
          cellData.newInit = false
          processActive = true
          params.rowNode.setDataValue(colId, cellData)
          updateNode({
            api: params.api,
            assayMode: assayMode,
            column: cols[i]!,
            createNew: createNew,
            nameCellData: cellData,
            rowNode: params.rowNode,
            tableUuid: params.tableUuid
          })
          return
        } else cellData.value = '' // Reset default value if not filled
      } else {
        // Only allow editing the rest of the cells if protocol is set
        if (processActive) {
          cellData.editable = fieldEditable
        } else cellData.editable = false
      }
      params.rowNode.setDataValue(colId, cellData)
      i += 1
    }
    // If default protocol or name was filled, enable the next node(s) too
    if (processActive) enableNextIdx = i
  }
  // If we can immediately enable the next node(s), proceed
  if (enableNextIdx && enableNextIdx < cols.length - 1) {
    params.startIdx = enableNextIdx
    enableNextNodes(params)
  } else { // Else refresh cells to enable saving (HACK: see #2490)
    params.api.refreshCells(
      {columns: ['rowEdit'], rowNodes: [params.rowNode], force: true})
  }
}

// Return default or empty data for a new cell (formerly getDefaultValue()
export function getDefaultCellData (
    params: CellDefaultParams
): SheetTableCellData {
  const editStore = useEditStore()

  const forceEmpty: boolean = params.forceEmpty || false
  const newInit: boolean = params.newInit || false

  const col = params.api.getColumn(params.colId) as Column
  const colDef = col.getColDef() as ColDef
  let editConfig: StudyEditConfigNodeField | null = null
  if (colDef.cellEditorParams) {
    editConfig = colDef.cellEditorParams.editConfigField
  }

  const cellData: SheetTableCellData = {
    newInit: newInit,
    newRow: true,
    uuid: '',
    value: ''
  }

  // Default value
  if (!forceEmpty && editConfig && editConfig.default) {
    // TODO: TBD: Also/only check for colType?
    if (editConfig.format === EDIT_FORMAT_PROTOCOL) {
      cellData.value = editStore.editContext?.protocols.find(
        (e) => e.uuid === editConfig.default)?.name || ''
      if (cellData.value) cellData.uuidRef = editConfig.default as string
    } else {
      cellData.value = editConfig.default
    }
  } else if (colDef.cellRendererParams.colType === EDIT_COL_TYPE_ONTOLOGY) {
    // Special value notation if default is not found
    cellData.value = []
  }

  // Default unit
  if (editConfig && editConfig.unit_default !== undefined) {
    cellData.unit = editConfig.unit_default
  }
  return cellData
}

// Formerly findNextNodeIdx()
export function getNextNodeIdx (
    cols: Array<Column>,
    idx: number
): number | null {
  if (idx > cols.length - 1) return null
  const groupId = cols[idx]!.getOriginalParent()!.getGroupId()
  while (idx < cols.length - 1) {
    if (groupId !== cols[idx]!.getOriginalParent()!.getGroupId()) return idx
    idx += 1
  }
  return null
}

// Return cell data for row saving (formerly getCellData())
export function getRowSaveCell (params: RowSaveCellParams): RowSaveDataCell {
  const colDef = params.column.getColDef()
  const colId = params.column.getColId()
  const data = params.rowNode.data[colId] as SheetTableCellData
  const headerType = colDef.cellEditorParams.fieldHeader.type
  const itemType = colDef.cellEditorParams.fieldHeader.item_type
  const objCls = colDef.cellEditorParams.fieldHeader.obj_cls

  // If existing node, only provide the UUID
  if (NODE_ID_HEADER_TYPES.includes(headerType) &&
      (data.uuid || data.uuidRef)) {
    const ret: RowSaveDataCell = { obj_cls: objCls, value: data.value }
    if (params.assayMode && itemType == EDIT_ITEM_TYPE_SAMPLE && data.uuidRef) {
      // Sample in an assay is a special case
      ret.uuid = data.uuidRef
      return ret
    } else if (data.uuid) {
      // If name or protocol def, include value for comparison
      ret.uuid = data.uuid
      return ret
    }
  }

  // Else return full data
  // TODO: Clean up and simplify
  let ret = JSON.parse(JSON.stringify(data))
  // Delete redundant fields
  delete ret.editable
  delete ret.newInit
  delete ret.newRow
  delete ret.uuidRef
  if (!NODE_ID_HEADER_TYPES.includes(headerType)) delete ret.uuid
  ret = ret as RowSaveDataCell
  // Add former headerInfo fields
  ret['header_field'] = colId
  ret['header_name'] = colDef.cellEditorParams.fieldHeader.name
  ret['header_type'] = headerType
  if (objCls == DB_OBJ_CLASS_MATERIAL && headerType == EDIT_HEADER_TYPE_NAME) {
    ret['item_type'] = itemType
  }
  ret['obj_cls'] = objCls
  if (data.uuidRef) ret['uuid_ref'] = data.uuidRef
  return ret
}

// Return data for saving a new row (formerly getNewRowData())
export function getRowSaveData (params: RowSaveDataParams): RowSaveData {
  const appStore = useAppStore()
  const tableStore = useTableStore()

  const cols = params.api.getColumns()!
  let inSampleNode = false
  let startIdx

  const ret: RowSaveData = {
    study: appStore.currentStudyUuid,
    assay: params.assayMode ? params.tableUuid : null,
    nodes: []
  }
  const cellParams = { assayMode: params.assayMode, rowNode: params.rowNode }

  // Iterate columns to get source node or set assay start index
  if (!params.assayMode) {
    const sourceNode = { cells: [
      getRowSaveCell(Object.assign(cellParams, { column: cols[1]! }))]
    } as RowSaveDataNode
    if (!sourceNode.cells[0]!.uuid) {
      sourceNode.headers = cols[1]!.getOriginalParent()!.getColGroupDef()!
        .headerGroupComponentParams.headers
    }
    let i = 1
    if (tableStore.sourceColSpan > 1) {
      i = 2
      const sourceGroupId = cols[2]!.getOriginalParent()!.getGroupId()!
      // If the node is new, get remaining fields
      if (!sourceNode.cells![0]!.uuid) {
        while (i < cols.length - 1) {
          if (cols[i]!.getOriginalParent()!.getGroupId() !== sourceGroupId) {
            startIdx = i
            break
          }
          sourceNode.cells.push(
            getRowSaveCell(Object.assign(cellParams, { column: cols[i]! })))
          i += 1
        }
      }
    }
    ret.nodes.push(sourceNode)
    if (!startIdx) startIdx = getNextNodeIdx(cols, i)
  } else { // Set assay start index
    startIdx = tableStore.sampleIdx
    inSampleNode = true
  }

  // Return if we don't have a startIdx (shouldn't happen but just in case)
  if (!startIdx) return ret

  // Iterate through remaining columns
  let groupId: string = cols[startIdx]!.getOriginalParent()!.getGroupId()!
  let fieldIdx: number = 0 // Field index within node
  let nodeCells: Array<RowSaveDataCell> = []
  let nodeStartIdx: number = startIdx
  for (let i = startIdx; i < cols.length - 1; i++) {
    if (fieldIdx === 0) nodeStartIdx = i
    // Add cells for new nodes, only the first node for existing ones
    if (fieldIdx === 0 ||
        !(params.rowNode.data[cols[i]!.getColId()].uuid &&
        !(params.assayMode && inSampleNode))) {
      nodeCells.push(getRowSaveCell(
        Object.assign(cellParams, { column: cols[i]! })))
    }
    if (i === cols.length - 1 ||
        groupId !== cols[i + 1]!.getOriginalParent()!.getGroupId()) {
      groupId = cols[i + 1]!.getOriginalParent()!.getGroupId()
      fieldIdx = 0
      const nodeData: RowSaveDataNode = { cells: Object.assign(nodeCells) }
      if (!nodeCells[0]!.uuid) {
        nodeData.headers = cols[nodeStartIdx]!.getOriginalParent()!
          .getColGroupDef()!.headerGroupComponentParams.headers
      }
      ret.nodes.push(nodeData)
      nodeCells = []
      inSampleNode = cols[i + 1]!.getColId() === tableStore.sampleColId
    } else fieldIdx += 1
  }
  return ret
}

// Formerly handleRowInsert()
export function insertRow (params: RowInsertParams) {
  const editStore = useEditStore()
  const tableStore = useTableStore()

  const row: NewRowData = {
    rowNum: params.api.getDisplayedRowCount() + 1 }
  const cols = params.api.getColumns()
  if (!cols) return // This should not be possible, but just in case
  const emptyData: SheetTableCellData = {
    editable: null,
    newInit: true,
    newRow: true,
    uuid: '',
    value: ''
  }
  let studyEdit: boolean = true

  for (let i = 1; i < cols.length - 1; i++) {
    const d = JSON.parse(JSON.stringify(emptyData))
    const colId = cols[i]!.getColId()
    if (!params.assayMode) { // Study table
      // Initially only make first column (source ID) editable
      d.editable = studyEdit
      if (studyEdit) studyEdit = false
    } else { // Assay table
      // Enable sample name column editing
      d.editable = colId === tableStore.sampleColId
    }
    row[colId] = d
  }

  const res = params.api.applyTransaction({ add: [row] })
  editStore.unsavedRow = {
    id: res!.add[0]!.id as string,
    tableUuid: params.tableUuid,
  }
  // Scroll to inserted row
  params.api.ensureIndexVisible(res!.add[0]!.rowIndex as number)
  // Scroll to start for study or sample col for assay
  const visColId = params.assayMode ? tableStore.sampleColId : 'col1'
  params.api.ensureColumnVisible(visColId)
}

// Formerly handleRowSave()
export function saveRow (params: RowSaveParams) {
  const appStore = useAppStore()
  const editStore = useEditStore()
  const tableStore = useTableStore()

  editStore.updatingRow = true
  const url = URL_ROW_INS_PREFIX + appStore.projectUuid

  fetch(url, {
    method: 'POST',
    body: JSON.stringify({ new_row: params.saveData }),
    credentials: 'same-origin',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      'X-CSRFToken': appStore.sodarContext!.csrf_token
    }
  }).then(data => data.json())
    .then(data => {
      if (data.detail === 'ok') {
        const cols = params.api.getColumns()!

        const lastSourceGroupIdx = tableStore.sourceColSpan
        const lastSourceGroupId =
          cols[lastSourceGroupIdx]!.getOriginalParent()!.getGroupId()
        const newSample = !params.assayMode &&
          !params.rowNode.data[tableStore.sampleColId].uuid
        let nodeIdx = 0
        let sampleName
        let sampleUuid

        let startIdx = 1
        if (params.assayMode) {
          startIdx = tableStore.sampleIdx
          // Update source cells in assay table
          for (let i = 1; i < startIdx; i++) {
            params.rowNode.data[cols[i]!.getColId()]!.newRow = false
          }
        }
        let groupId = cols[startIdx]!.getOriginalParent()!.getGroupId()

        // Set cell data to match existing row
        for (let i = startIdx; i < cols.length - 1; i++) {
          const colId = cols[i]!.getColId()
          const cellData = params.rowNode.data[colId]
          cellData.editable =
            cols[i]!.getColDef().cellRendererParams.fieldEditable
          cellData.newInit = false
          cellData.newRow = false
          if (!cellData.uuid) cellData.uuid = data.node_uuids[nodeIdx]
          params.rowNode.setDataValue(colId, cellData)
          // Save sample info if new sample was added in study
          if (!params.assayMode && colId === tableStore.sampleColId) {
            sampleUuid = data.node_uuids[nodeIdx]
            sampleName = params.rowNode.data[colId].value
          }
          let nextGroupId = ''
          // Update groupId and nodeIdx
          if (i < cols.length - 2) {
            nextGroupId = cols[i + 1]!.getOriginalParent()!.getGroupId()
          }
          if (![lastSourceGroupId, groupId].includes(nextGroupId)) {
            groupId = nextGroupId
            nodeIdx += 1
          }
        }

        // NOTE: rowNum is already set unlike in original vueapp
        // Update sample list if a new sample was added in study/assay
        if (!params.assayMode && newSample && sampleUuid) {
          editStore.editContext!.samples[sampleUuid] = {
            name: sampleName, assays: []
          }
        } else if (params.assayMode) {
          sampleUuid = params.rowNode.data[tableStore.sampleColId].uuid
          if (!(params.saveData.assay! in
              editStore.editContext!.samples[sampleUuid]!.assays)) {
            editStore.editContext!.samples[
              sampleUuid]!.assays.push(params.saveData.assay!)
          }
        }

        // Finalize
        // TODO: Do we still need to call refreshCells() here? (see vueapp)
        editStore.unsavedRow = null
        editStore.editDataUpdated = true
        editStore.versionSaved = false
        if (params.notifyCb) params.notifyCb('Row inserted', VARIANT_SUCCESS)
      } else {
        const msg = 'Row insert failed: ' + data.detail
        console.error(msg)
        if (params.notifyCb) params.notifyCb(msg, VARIANT_DANGER)
      }
      if (params.finishCb) params.finishCb()
      editStore.updatingRow = false
    }) // TODO: Catch and handle error
}

// Update values of given cells in given grid
export function updateCellUIValues (
    gridApi: GridApi,
    cells: Array<CellEditData>,
    refreshCells: boolean, // TODO: Is this needed?
    revert: boolean
) {
  for (const c of cells) {
    gridApi.forEachNode(function (rowNode) {
      const d = rowNode.data[c.fieldId]
      if (d && d.uuid && d.uuid === c.uuid) {
        if (revert) {
          d.value = c.ogValue
          if (c.ogUnit !== undefined) d.unit = c.ogUnit
        }
        else {
          d.value = c.value
          if (c.unit !== undefined) d.unit = c.unit
        }
        rowNode.setDataValue(c.fieldId, d)
      }
    })
    if (refreshCells) {
      gridApi.refreshCells({ columns: [c.fieldId], force: true })
    }
  }
}

// Return name prefix for a material or a process
export function getNamePrefix (
    rowNode: IRowNode,
    cols: Array<Column>,
    currentIdx: number // Index of first cell in new node being added
): string {
  for (let i = currentIdx - 1 ; i > 0; i--) {
    const header: SheetTableFieldHeader =
      cols[i]!.getColDef().cellEditorParams.fieldHeader
    if ([EDIT_HEADER_TYPE_NAME, EDIT_HEADER_TYPE_PROCESS].includes(
        header.type as string) &&
        header.item_type !== EDIT_ITEM_TYPE_DATA) {
      return rowNode.data[cols[i]!.getColId()].value
    }
  }
  return ''
}

// Update one or multiple cells (formerly handleCellEdit())
export function updateCells (
    cells: CellEditData | Array<CellEditData>,
    verify: boolean,
    notifyCb: NotifyCb | undefined
) {
  const appStore = useAppStore()
  const editStore = useEditStore()
  const tableStore = useTableStore()

  // TODO: Add timeout / retrying
  // TODO: In the future, add edited info in a queue and save periodically
  if (!Array.isArray(cells)) cells = [cells]
  const requestCells: Array<EditRequestCell> = []
  for (const c of cells) {
    const r: EditRequestCell = {
      header_name: c.headerName,
      header_type: c.headerType,
      obj_cls: c.objCls,
      uuid: c.uuid || null,
      value: c.value
    }
    // Add optional types
    if ('itemType' in c && c.headerType == 'name') {
      // TODO: TBD: item type only set for name column cells, is this correct?
      r.item_type = c.itemType
    }
    if (c.unit) r.unit = c.unit
    if (c.uuidRef) r.uuid_ref = c.uuidRef
    requestCells.push(r)
  }
  fetch('/samplesheets/ajax/edit/cell/' + appStore.projectUuid, {
    method: 'POST',
    body: JSON.stringify({ updated_cells: requestCells, verify: verify }),
    credentials: 'same-origin',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      'X-CSRFToken': appStore.sodarContext?.csrf_token as string
    }
  }).then(data => data.json())
    .then(
      data => {
        const gridApis: Array<GridApi> = [tableStore.gridApi.study as GridApi]
        for (const k in tableStore.gridApi.assays) {
          gridApis.push(tableStore.gridApi.assays[k] as GridApi)
        }

        if (data.detail === 'ok') {
          /*
          let bodyPrefix: string
          if (cells.length > 1) bodyPrefix = cells.length.toString() + ' cells '
          else bodyPrefix = 'Cell '
          if (notifyCb) notifyCb(bodyPrefix + 'updated', VARIANT_SUCCESS)
          */
          editStore.editDataUpdated = true
          editStore.versionSaved = false
          // Update other occurrences of cell in UI
          for (const api of gridApis) {
            // TODO: Omit current table? That wasn't done in the original impl
            updateCellUIValues(api, cells, true, false)
          }
        } else if (data.detail === 'alert') {
          // Handle verification alert from server
          if (confirm(data.alert_msg)) {
            // Call update again
            updateCells(cells, false, notifyCb)
          } else { // Revert values in UI
            for (const api of gridApis) {
              updateCellUIValues(api, cells, true, true)
            }
          }
        } else {
          const msg = 'Cell update failed: ' + data.detail
          console.error(msg)
          if (notifyCb) notifyCb(msg, VARIANT_DANGER)
          // TODO: Mark invalid/unsaved field(s) in UI
        }
      }
    ).catch(function (error) {
      const msg = 'Cell update error: ' + error
      console.error(msg)
      if (notifyCb) notifyCb(msg, VARIANT_DANGER)
    })
}

// Formerly handleNodeUpdate()
// TODO: Large and complex, split into smaller functions?
export function updateNode (params: NodeUpdateParams) {
  const tableStore = useTableStore()

  // Sample node in assay
  if (params.assayMode &&
      params.column.getOriginalParent()!.getColGroupDef()!
        .headerName?.toLowerCase() === HEADER_NAME_SAMPLE) {
    const studyApi = tableStore.gridApi.study
    const studyCols = studyApi!.getColumns()

    // Get sample row from study table
    let studyCopyRow = null
    studyApi!.forEachNode(function (rowNode) {
      if (params.nameCellData &&
          rowNode.data[tableStore.sampleColId].uuid ===
          params.nameCellData.uuidRef) {
        studyCopyRow = rowNode
      }
    })

    // Fill in preceeding nodes for sample
    for (let i = 1; i < tableStore.sampleIdx; i++) {
      const copyColId = studyCols![i]!.getColId()
      const copyData = JSON.parse(
        JSON.stringify(studyCopyRow!.data[copyColId])) as SheetTableCellData
      copyData.newRow = true
      copyData.newInit = false
      copyData.editable = params.api.getColumn(
        copyColId)!.getColDef().cellRendererParams.fieldEditable
      params.rowNode.setDataValue(copyColId, copyData)
    }
  }

  // Update other cells in the same node
  const nodeCols: Array<Column> = []
  const cols = params.api.getColumns()
  let nextNodeStartIdx: number | null = null

  // Since we split the source group we have to apply some trickery
  const parent = params.column.getOriginalParent()
  let colGroupId = parent!.getGroupId()
  if (colGroupId === '1' && tableStore.sourceColSpan > 1) colGroupId = '2'

  let startIdx: number | null = null
  const nameColId = params.column.getColId()
  for (let i = 1; i < cols!.length - 1; i++) {
    if (cols![i]!.getColId() === nameColId) startIdx = i + 1
    if (startIdx && startIdx <= i) {
      const col = cols![i]!
      const newGroupId = col.getOriginalParent()!.getGroupId()
      if (newGroupId === colGroupId) {
        nodeCols.push(col)
      } else if (col.getColId() !== nameColId && newGroupId !== colGroupId) {
        nextNodeStartIdx = i
        break
      }
    }
  }

  // If the node is new, fill out other cells with default/empty values
  if (params.createNew) {
    for (let i = 0; i < nodeCols.length; i++) {
      const newColId = nodeCols[i]!.getColId()
      const defaultData = getDefaultCellData({
        api: params.api,
        colId: newColId
      })
      params.rowNode.setDataValue(newColId, defaultData)
    }
  } else if (params.nameCellData) {
    // Else set UUIDs and update cell values (only in the same table)
    let copyRowNode: IRowNode | null = null
    params.api.forEachNode(function (rowNode) {
      if (!copyRowNode &&
          rowNode.data[nameColId].value === params.nameCellData?.value) {
        copyRowNode = rowNode
      }
    })
    for (let i = 0; i < nodeCols.length; i++) {
      const copyColId = nodeCols![i]!.getColId()
      const copyData = JSON.parse(JSON.stringify(copyRowNode!.data[copyColId]))
      copyData.newInit = false
      copyData.editable = params.api.getColumn(copyColId)!
        .getColDef().cellRendererParams.fieldEditable
      params.rowNode.setDataValue(copyColId, copyData)
    }
  }

  // When updating process name column, update preceeding protocol UUID
  const headerType = params.column.getColDef().cellEditorParams.fieldHeader.type
  if (headerType == EDIT_HEADER_TYPE_PROCESS && startIdx && startIdx >= 2) {
    const prevCol = cols![startIdx - 2] // -2 because we should be at name+1
    const prevHt = prevCol!.getColDef().cellEditorParams.fieldHeader.type
    const prevGroupId = prevCol!.getOriginalParent()!.getGroupId()
    if (prevHt === EDIT_HEADER_TYPE_PROTOCOL && prevGroupId === colGroupId) {
      params.rowNode.data[
        prevCol!.getColId()]!.uuid = params.rowNode.data[nameColId].uuid
    }
  }

  // Enable next node(s) if we are initializing node for the 1st time
  if (nextNodeStartIdx) {
    enableNextNodes({
      api: params.api,
      rowNode: params.rowNode,
      startIdx: nextNodeStartIdx,
      tableUuid: params.tableUuid
    })
  } else {
    // HACK: Refresh row edit cell to trigger enableSave() in RowEditRenderer
    // TODO: Better approach (see #2490)
    params.api.refreshCells(
      {columns: ['rowEdit'], rowNodes: [params.rowNode], force: true})
  }
}
