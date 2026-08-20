import { beforeEach, describe, expect, test, vi } from 'vitest'
import { type ColDef } from 'ag-grid-community'

import { getRowSaveCell } from '@/utils/editUtils.ts'
import {
  type RowSaveCellParams,
  type SheetTableCellData,
  type SheetTableFieldHeader
} from '@/types.ts'
import {
  DB_OBJ_CLASS_MATERIAL,
  DB_OBJ_CLASS_PROCESS,
  EDIT_HEADER_TYPE_CHAR,
  EDIT_HEADER_TYPE_NAME,
  EDIT_HEADER_TYPE_PROTOCOL,
  EDIT_ITEM_TYPE_SAMPLE,
  EDIT_ITEM_TYPE_SOURCE,
} from '@/constants.ts'

import { copy } from '../testUtils.ts'
import { TMP_UUID } from '../testConstants.ts'

// Test Data -------------------------------------------------------------------

const defaultHeaderName = 'Name'
const defaultCellData: SheetTableCellData = {
  editable: true,
  newInit: false,
  newRow: true,
  uuid: '',
  value: '0814'
}
const defaultFieldHeader = {
  name: defaultHeaderName,
  item_type: EDIT_ITEM_TYPE_SOURCE,
  obj_cls: DB_OBJ_CLASS_MATERIAL,
  type: EDIT_HEADER_TYPE_NAME,
}
const defaultColId = 'col1'
const protocolName = 'Sample collection'

let cellData: SheetTableCellData
let colDef: ColDef
let colId: string
let fieldHeader: SheetTableFieldHeader

// Tests for getRowSaveCell() --------------------------------------------------

describe('getRowSaveCell()', () => {
  function getParams (): RowSaveCellParams {
    colDef = { cellEditorParams: { fieldHeader: fieldHeader } }
    const ret = {
      assayMode: false,
      column: {
        getColId: () => { return colId },
        getColDef: () => { return colDef }
      },
      rowNode: { data: { [colId]: cellData } },
    }
    return ret as RowSaveCellParams
  }

  beforeEach(() => {
    vi.resetAllMocks()
    cellData = copy(defaultCellData) as SheetTableCellData
    colId = defaultColId
    fieldHeader = copy(defaultFieldHeader) as SheetTableFieldHeader
  })

  test('get new source name cell', async () => {
    expect(getRowSaveCell(getParams())).toEqual({
      header_field: defaultColId,
      header_name: defaultHeaderName,
      header_type: EDIT_HEADER_TYPE_NAME,
      item_type: EDIT_ITEM_TYPE_SOURCE,
      obj_cls: DB_OBJ_CLASS_MATERIAL,
      uuid: '',
      value: '0814'
    })
  })

  test('get existing source name cell', async () => {
    cellData.uuid = TMP_UUID
    // Header info should be missing
    expect(getRowSaveCell(getParams())).toEqual({
      obj_cls: DB_OBJ_CLASS_MATERIAL,
      uuid: TMP_UUID,
      value: '0814'
    })
  })

  test('get new sample name cell in study', async () => {
    cellData.value = '0814-N1'
    fieldHeader.item_type = EDIT_ITEM_TYPE_SAMPLE
    expect(getRowSaveCell(getParams())).toEqual({
      header_field: defaultColId,
      header_name: defaultHeaderName,
      header_type: EDIT_HEADER_TYPE_NAME,
      item_type: EDIT_ITEM_TYPE_SAMPLE,
      obj_cls: DB_OBJ_CLASS_MATERIAL,
      uuid: '',
      value: '0814-N1'
    })
  })

  test('get existing sample name cell in assay', async () => {
    cellData.value = '0814-N1'
    cellData.uuidRef = TMP_UUID
    fieldHeader.item_type = EDIT_ITEM_TYPE_SAMPLE
    const params = getParams()
    params.assayMode = true
    // Header info should be missing, uuidRef should be assigned to UUID
    expect(getRowSaveCell(params)).toEqual({
      obj_cls: DB_OBJ_CLASS_MATERIAL,
      uuid: TMP_UUID,
      value: '0814-N1'
    })
  })

  test('get characteristics cell', async () => {
    cellData.value = 'xyz'
    fieldHeader.type = EDIT_HEADER_TYPE_CHAR
    fieldHeader.item_type = null
    expect(getRowSaveCell(getParams())).toEqual({
      header_field: defaultColId,
      header_name: defaultHeaderName,
      header_type: EDIT_HEADER_TYPE_CHAR,
      obj_cls: DB_OBJ_CLASS_MATERIAL,
      value: 'xyz'
    })
  })

  test('get characteristics cell with unit', async () => {
    cellData.unit = 'day'
    cellData.value = '1'
    fieldHeader.type = EDIT_HEADER_TYPE_CHAR
    fieldHeader.item_type = null
    expect(getRowSaveCell(getParams())).toEqual({
      header_field: defaultColId,
      header_name: defaultHeaderName,
      header_type: EDIT_HEADER_TYPE_CHAR,
      obj_cls: DB_OBJ_CLASS_MATERIAL,
      unit: 'day',
      value: '1'
    })
  })

  test('get protocol cell', async () => {
    cellData.uuidRef = TMP_UUID
    cellData.value = protocolName
    fieldHeader.type = EDIT_HEADER_TYPE_PROTOCOL
    fieldHeader.item_type = null
    fieldHeader.obj_cls = DB_OBJ_CLASS_PROCESS
    expect(getRowSaveCell(getParams())).toEqual({
      header_field: defaultColId,
      header_name: defaultHeaderName,
      header_type: EDIT_HEADER_TYPE_PROTOCOL,
      obj_cls: DB_OBJ_CLASS_PROCESS,
      uuid: '',
      uuid_ref: TMP_UUID,
      value: protocolName
    })
  })
})
