// API and helpers for sample sheet editing

import { type GridApi } from 'ag-grid-community'

import { useAppStore } from '@/stores/appStore.ts'
import { useEditStore } from '@/stores/editStore.ts'
import { useTableStore } from '@/stores/tableStore.ts'
import { getAjaxRequestInit } from '@/utils/appUtils.ts'
import {
  type CellEditData,
  type EditRequestCell,
  type GenericResponseBody,
  type NotifyCb,
  type RowDeleteData,
  type RowDeleteParams,
} from '@/types.ts'
import {
  AJAX_RES_OK,
  URL_ROW_DEL_PREFIX
} from '@/constants.ts'

// TODO: Sort functions alphabetically

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

// Update one or multiple cells (formerly handleCellEdit())
export function updateCells (
    cells: CellEditData | Array<CellEditData>,
    verify: boolean,
    notifyCb: NotifyCb | undefined
) {
  // const { create } = useToast()
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
          if (notifyCb) notifyCb(bodyPrefix + 'updated', 'success', 0)
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
          if (notifyCb) notifyCb(msg, 'danger', 0)
          // TODO: Mark invalid/unsaved field(s) in UI
        }
      }
    ).catch(function (error) {
      const msg = 'Cell update error: ' + error
      console.error(msg)
      if (notifyCb) notifyCb(msg, 'danger', 0)
    })
}

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
      if (params.notifyCb) params.notifyCb('Row deleted', 'success', 0)
    } else {
      const msg = 'Row delete failed'
      console.error(
        `${msg}: ${(res as GenericResponseBody).detail}`)
      if (params.notifyCb) params.notifyCb(msg, 'danger', 0)
    }
    if (params.finishCb) params.finishCb()
    editStore.updatingRow = false
  }) // TODO: Catch and handle fetch() error
}
