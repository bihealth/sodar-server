import { beforeEach, describe, expect, test, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { type Column, type GridApi, type IRowNode } from 'ag-grid-community'

import { useAppStore } from '@/stores/appStore.ts'
import { useTableStore } from '@/stores/tableStore.ts'
import { getRowSaveData } from '@/utils/editUtils.ts'
import {
  type RowSaveData,
  type RowSaveDataParams,
  type SheetTableFieldHeader
} from '@/types.ts'
import {
  DB_OBJ_CLASS_MATERIAL,
  DB_OBJ_CLASS_PROCESS,
  EDIT_HEADER_TYPE_CHAR,
  EDIT_HEADER_TYPE_NAME,
  EDIT_HEADER_TYPE_PROCESS,
  EDIT_HEADER_TYPE_PROTOCOL,
  EDIT_ITEM_TYPE_DATA,
  EDIT_ITEM_TYPE_SAMPLE,
  EDIT_ITEM_TYPE_SOURCE,
} from '@/constants.ts'

import { copy } from '../testUtils.ts'
import {
  ASSAY_UUID,
  STUDY_UUID,
  TMP_UUID,
  TMP_UUID2,
  TMP_UUID3
} from '../testConstants.ts'

// Test Data -------------------------------------------------------------------

interface TestCell {
  colId: string,
  groupId: string,
  fieldHeader: SheetTableFieldHeader,
  data?: object
}

const headers = ['Dummy'] // NOTE: We only need dummy headers here
const emptyCellData = {
  editable: true,
  newInit: false,
  newRow: true,
  uuid: '',
  value: ''
}
const fhSource = {
  name: 'Name',
  item_type: EDIT_ITEM_TYPE_SOURCE,
  obj_cls: DB_OBJ_CLASS_MATERIAL,
  type: EDIT_HEADER_TYPE_NAME,
}
const fhChar = {
  name: 'Characteristic',
  obj_cls: DB_OBJ_CLASS_MATERIAL,
  type: EDIT_HEADER_TYPE_CHAR,
}
const fhProtocol = {
  name: 'Protocol',
  obj_cls: DB_OBJ_CLASS_PROCESS,
  type: EDIT_HEADER_TYPE_PROTOCOL,
}
const fhSample = {
  name: 'Name',
  item_type: EDIT_ITEM_TYPE_SAMPLE,
  obj_cls: DB_OBJ_CLASS_MATERIAL,
  type: EDIT_HEADER_TYPE_NAME,
}
const fhProcess = {
  name: 'Data Transformation Name',
  obj_cls: DB_OBJ_CLASS_PROCESS,
  type: EDIT_HEADER_TYPE_PROCESS,
}
const fhData = {
  name: 'Name',
  item_type: EDIT_ITEM_TYPE_DATA,
  obj_cls: DB_OBJ_CLASS_MATERIAL,
  type: EDIT_HEADER_TYPE_NAME,
}
const cdSource = { value: '0814' }
const cdProtocol = { uuidRef: TMP_UUID, value: 'sample collection' }
const cdSample = { value: '0814-N1' }

let cols: Array<Column>
let rowNode: IRowNode

// Tests for getRowSaveData() --------------------------------------------------

describe('getRowSaveData()', () => {
  // Add cells and corresponding columns
  function setGridData (cells: Array<TestCell>) {
    cols.push({} as Column) // Dummy rowNum column
    for (const c of cells) {
      rowNode.data[c.colId] = Object.assign(copy(emptyCellData), c.data)

      cols.push({
        getColDef: () => {
          return { cellEditorParams: { fieldHeader: c.fieldHeader }}
        },
        getColId: () => { return c.colId },
        getOriginalParent: () => {
          return {
            getColGroupDef: () => {
              return { headerGroupComponentParams: { headers: headers } }
            },
            getGroupId: () => { return c.groupId }
          } } } as Column)
    }
    cols.push({
      getColId: () => { return 'col999' },
      getOriginalParent: () => {
        return { getGroupId: () => { return 'rowEdit' } }
      }
    } as Column) // Dummy rowEdit column
  }

  function getCell (
      colId: string,
      groupId: string,
      fieldHeader: object,
      data?: object): TestCell {
    return {
      colId: colId,
      groupId: groupId,
      fieldHeader: fieldHeader as SheetTableFieldHeader,
      data: data
    }
  }

  function getParams (): RowSaveDataParams {
    return {
      api: { getColumns: () => { return cols } } as GridApi,
      assayMode: false,
      rowNode: rowNode,
      tableUuid: STUDY_UUID
    }
  }

  beforeEach(() => {
    vi.resetAllMocks()
    setActivePinia(createPinia())
    const appStore = useAppStore()
    appStore.currentStudyUuid = STUDY_UUID
    const tableStore = useTableStore()
    tableStore.sampleColId = 'col2'
    tableStore.sourceColSpan = 1
    tableStore.sampleIdx = 3 // NOTE: Must count rowNum here

    cols = []
    rowNode = { data: {} } as IRowNode
  })

  test('get study row', async () => {
    setGridData([
      getCell('col0', '1', fhSource, cdSource),
      getCell('col1', '2', fhProtocol, cdProtocol),
      getCell('col2', '3', fhSample, cdSample),
    ])
    expect(getRowSaveData(getParams())).toEqual({
      assay: null,
      nodes: [
        {
          cells: [{
            header_field: 'col0',
            header_name: 'Name',
            header_type: EDIT_HEADER_TYPE_NAME,
            item_type: EDIT_ITEM_TYPE_SOURCE,
            obj_cls: DB_OBJ_CLASS_MATERIAL,
            uuid: '',
            value: '0814'
          }],
          headers: headers
        },
        {
          cells: [{
            header_field: 'col1',
            header_name: 'Protocol',
            header_type: EDIT_HEADER_TYPE_PROTOCOL,
            obj_cls: DB_OBJ_CLASS_PROCESS,
            uuid: '',
            uuid_ref: TMP_UUID,
            value: 'sample collection'
          }],
          headers: headers
        },
        {
          cells: [{
            header_field: 'col2',
            header_name: 'Name',
            header_type: EDIT_HEADER_TYPE_NAME,
            item_type: EDIT_ITEM_TYPE_SAMPLE,
            obj_cls: DB_OBJ_CLASS_MATERIAL,
            uuid: '',
            value: '0814-N1'
          }],
          headers: headers
        }
      ],
      study: STUDY_UUID
    })
  })

  test('get study row with source colspan > 1', async () => {
    const tableStore = useTableStore()
    tableStore.sampleColId = 'col3'
    tableStore.sourceColSpan = 2
    tableStore.sampleIdx = 4

    setGridData([
      getCell('col0', '1', fhSource, cdSource),
      getCell('col1', '1', fhChar), // Also under source
      getCell('col2', '2', fhProtocol, cdProtocol),
      getCell('col3', '3', fhSample, cdSample),
    ])
    const res = getRowSaveData(getParams()) as RowSaveData
    expect(res.nodes.length).toBe(3) // Should still be 3 nodes
    expect(res.nodes[0]!.cells.length).toBe(2) // 2 cells in source node
    expect(res.nodes[0]!.cells[1]).toEqual({
      header_field: 'col1',
      header_name: 'Characteristic',
      header_type: EDIT_HEADER_TYPE_CHAR,
      obj_cls: DB_OBJ_CLASS_MATERIAL,
      value: ''
    })
  })

  test('get assay row', async () => {
    setGridData([
      getCell('col0', '1', fhSource, cdSource),
      getCell('col1', '2', fhProtocol, cdProtocol),
      getCell(
        'col2', '3', fhSample,
        Object.assign(copy(cdSample), { uuid: TMP_UUID3 })),
      getCell('col3', '4', fhProtocol, { uuidRef: TMP_UUID2, value: 'prot2' }),
      getCell('col4', '4', fhProcess, { value: 'proc' }), // Same node as before
      getCell('col5', '5', fhData),
    ])
    const params = getParams()
    params.assayMode = true
    params.tableUuid = ASSAY_UUID
    // Only assay nodes from sample onwards should be present
    expect(getRowSaveData(params)).toEqual({
      assay: ASSAY_UUID,
      nodes: [
        {
          cells: [{
            obj_cls: DB_OBJ_CLASS_MATERIAL,
            uuid: TMP_UUID3, // No header info because we have UUID
            value: '0814-N1'
          }] // No headers because we have UUID
        },
        {
          cells: [
            {
              header_field: 'col3',
              header_name: 'Protocol',
              header_type: EDIT_HEADER_TYPE_PROTOCOL,
              obj_cls: DB_OBJ_CLASS_PROCESS,
              uuid: '',
              uuid_ref: TMP_UUID2,
              value: 'prot2'
            },
            {
              header_field: 'col4',
              header_name: 'Data Transformation Name',
              header_type: EDIT_HEADER_TYPE_PROCESS,
              obj_cls: DB_OBJ_CLASS_PROCESS,
              uuid: '',
              value: 'proc'
            }
          ],
          headers: headers
        },
        {
          cells: [{
            header_field: 'col5',
            header_name: 'Name',
            header_type: EDIT_HEADER_TYPE_NAME,
            item_type: EDIT_ITEM_TYPE_DATA,
            obj_cls: DB_OBJ_CLASS_MATERIAL,
            uuid: '',
            value: ''
          }],
          headers: headers
        }
      ],
      study: STUDY_UUID
    })
  })

  test('get study row with existing source and colspan > 1', async () => {
    const tableStore = useTableStore()
    tableStore.sampleColId = 'col3'
    tableStore.sourceColSpan = 2
    tableStore.sampleIdx = 4

    setGridData([
      getCell(
        'col0', '1', fhSource, Object.assign(cdSource, { uuid: TMP_UUID3 })),
      getCell('col1', '1', fhChar), // Also under source
      getCell('col2', '2', fhProtocol, cdProtocol),
      getCell('col3', '3', fhSample, cdSample),
    ])
    const res = getRowSaveData(getParams()) as RowSaveData
    expect(res.nodes.length).toBe(3) // Should still be 3 nodes
    expect(res.nodes[0]!.cells.length).toBe(1) // Only name cell in source node
    expect(res.nodes[0]!.cells[0]).toEqual({
      obj_cls: DB_OBJ_CLASS_MATERIAL,
      uuid: TMP_UUID3, // No header info because we have UUID
      value: '0814'
    })
  })
})
