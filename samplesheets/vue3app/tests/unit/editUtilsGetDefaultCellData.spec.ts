import { beforeEach, describe, expect, test, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { type GridApi } from 'ag-grid-community'

import { getDefaultCellData } from '@/utils/editUtils.ts'
import { useEditStore } from '@/stores/editStore.ts'
import {
  type CellDefaultParams,
  type SheetTableCellData,
  type StudyEditConfigNodeField,
} from '@/types.ts'
import {
  EDIT_COL_TYPE_NAME,
  EDIT_COL_TYPE_ONTOLOGY,
  EDIT_COL_TYPE_PROTOCOL,
  EDIT_FORMAT_PROTOCOL,
  EDIT_FORMAT_STRING,
  EDIT_HEADER_TYPE_NAME,
} from '@/constants.ts'

import { TMP_UUID, TMP_UUID2 } from '../testConstants.ts'

// Test Data -------------------------------------------------------------------

let cellData: SheetTableCellData
let editConfig: StudyEditConfigNodeField
const sourceColId = 'col1'

// Tests for getDefaultCellData() ----------------------------------------------

describe('getDefaultCellData()', () => {
  function getMockGridApi (
      colType: string,
      editConfig: StudyEditConfigNodeField | null
  ): object {
    return {
      getColumn: () => {
        return {
          getColDef: () => {
            return {
              cellEditorParams: { editConfigField: editConfig },
              cellRendererParams: { colType: colType } } } } } }
  }

  function getDefaultParams (
      colType: string,
      editConfig: StudyEditConfigNodeField | null
  ): CellDefaultParams {
    return {
      api: getMockGridApi(colType, editConfig) as GridApi,
      colId: sourceColId,
    }
  }

  beforeEach(() => {
    vi.clearAllMocks()
    setActivePinia(createPinia())
    const editStore = useEditStore()
    editStore.editContext = {
      protocols: [
        { name: 'Protocol1', uuid: TMP_UUID },
        { name: 'Protocol2', uuid: TMP_UUID2 }
      ],
      samples: {},
      sodar_ontologies: {}
    }
    editConfig = {
      default: 'default',
      editable: true,
      format: EDIT_FORMAT_STRING,
      name: 'Name',
      regex: '',
      type: EDIT_HEADER_TYPE_NAME
    }
    cellData = {
      newInit: false,
      newRow: true,
      uuid: '',
      value: 'default'
    }
  })

  test('get data', async () => {
    const params = getDefaultParams(EDIT_COL_TYPE_NAME, editConfig)
    const res = getDefaultCellData(params)
    expect(res).toEqual(cellData)
  })

  test('get data without default value in config', async () => {
    editConfig.default = ''
    const params = getDefaultParams(EDIT_COL_TYPE_NAME, editConfig)
    const res = getDefaultCellData(params)
    cellData.value = ''
    expect(res).toEqual(cellData)
  })

  test('get data with forceEmpty=true', async () => {
    const params = getDefaultParams(EDIT_COL_TYPE_NAME, editConfig)
    params.forceEmpty = true
    const res = getDefaultCellData(params)
    cellData.value = ''
    expect(res).toEqual(cellData)
  })

  test('get data without editConfig', async () => {
    const params = getDefaultParams(EDIT_COL_TYPE_NAME, null)
    const res = getDefaultCellData(params)
    cellData.value = ''
    expect(res).toEqual(cellData)
  })

  test('get data with ontology column type', async () => {
    editConfig.default = ''
    const params = getDefaultParams(EDIT_COL_TYPE_ONTOLOGY, editConfig)
    const res = getDefaultCellData(params)
    cellData.value = []
    expect(res).toEqual(cellData)
  })

  test('get data with protocol format and default', async () => {
    editConfig.default = TMP_UUID2
    editConfig.format = EDIT_FORMAT_PROTOCOL
    // NOTE: Both format and col type actually not needed here..
    const params = getDefaultParams(EDIT_COL_TYPE_PROTOCOL, editConfig)
    const res = getDefaultCellData(params)
    cellData.value = 'Protocol2'
    cellData.uuidRef = TMP_UUID2
    expect(res).toEqual(cellData)
  })

  test('get data with protocol not in context', async () => {
    // NOTE: Not sure if we can end up here unless something goes very wrong..
    const editStore = useEditStore()
    editStore.editContext!.protocols = []
    editConfig.default = TMP_UUID2
    editConfig.format = EDIT_FORMAT_PROTOCOL
    const params = getDefaultParams(EDIT_COL_TYPE_PROTOCOL, editConfig)
    const res = getDefaultCellData(params)
    // Value and uuidRef should be empty
    cellData.value = ''
    expect(res).toEqual(cellData)
  })

  test('get data with unit_default', async () => {
    // NOTE: We don't actually check for unit colType
    editConfig.unit_default = 'unit'
    // NOTE: Both format and col type actually not needed here..
    const params = getDefaultParams(EDIT_COL_TYPE_NAME, editConfig)
    const res = getDefaultCellData(params)
    cellData.unit = 'unit'
    expect(res).toEqual(cellData)
  })
})
