import { beforeEach, describe, expect, test, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import {
  type Column,
  type GridApi,
  type IRowNode
} from 'ag-grid-community'

import { useAppStore } from '@/stores/appStore.ts'
import { useEditStore } from '@/stores/editStore.ts'
import { useTableStore } from '@/stores/tableStore.ts'
import { URL_ROW_INS_PREFIX } from '@/constants.ts'

import { saveRow } from '@/utils/editUtils.ts'
import {
  type RowSaveData,
  type RowSaveParams,
  type SodarContext,
  type StudyEditContext,
} from '@/types.ts'
import {
  DB_OBJ_CLASS_MATERIAL,
  DB_OBJ_CLASS_PROCESS,
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
  PROJECT_UUID,
  STUDY_UUID,
  TMP_UUID,
  TMP_UUID2,
  TMP_UUID3
} from '../testConstants.ts'

// Test data -------------------------------------------------------------------

interface TestCell {
  colId: string,
  groupId: string,
  data?: object
}

const emptyCellData = {
  editable: true,
  newInit: false,
  newRow: true,
  uuid: '',
  value: ''
}
const cdSource = { value: '0814' }
const cdProtocol = { uuidRef: TMP_UUID2, value: 'sample collection' }
const cdSample = { value: '0814-N1' }
const cdSourceAssay = Object.assign(copy(cdSource), { uuid: TMP_UUID })
const cdSampleAssay = Object.assign(copy(cdSample), { uuid: TMP_UUID3 })

const defaultStudyColInput: Array<TestCell> = [
  { colId: 'col0', groupId: '1', data: cdSource },
  { colId: 'col1', groupId: '2', data: cdProtocol },
  { colId: 'col2', groupId: '3', data: cdSample }
]
const defaultStudyRow: RowSaveData = {
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
      headers: []
    },
    {
      cells: [{
        header_field: 'col1',
        header_name: 'Protocol',
        header_type: EDIT_HEADER_TYPE_PROTOCOL,
        obj_cls: DB_OBJ_CLASS_PROCESS,
        uuid: '',
        uuid_ref: TMP_UUID2,
        value: 'sample collection'
      }],
      headers: []
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
      headers: []
    }
  ],
  study: STUDY_UUID
}
const defaultAssayColInput: Array<TestCell> = [
  { colId: 'col0', groupId: '1', data: cdSourceAssay },
  { colId: 'col1', groupId: '2', data: cdProtocol },
  { colId: 'col2', groupId: '3', data: cdSampleAssay },
  { colId: 'col3', groupId: '4', data: { uuidRef: TMP_UUID2, value: 'prot2' }},
  { colId: 'col4', groupId: '4', data: { value: 'proc' }},
  { colId: 'col5', groupId: '5' },
]
const defaultAssayRow: RowSaveData = {
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
          uuid_ref: crypto.randomUUID(),
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
      headers: []
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
      headers: []
    }
  ],
  study: STUDY_UUID
}

let cols: Array<Column> = []
let rowNode: IRowNode = { data: {} } as IRowNode
let nodeUuids: Array<string> = []
let saveData: RowSaveData

const url = URL_ROW_INS_PREFIX + PROJECT_UUID

// Tests for saveRow() ---------------------------------------------------------

describe('saveRow()', () => {
  function setGridData (cells: Array<TestCell>, assayMode: boolean) {
    const tableStore = useTableStore()
    const uuidStartIdx = !assayMode ? 0 : tableStore.sampleIdx
    cols = []
    rowNode = { data: {}, setDataValue: vi.fn() } as unknown as IRowNode
    nodeUuids = []
    let idx = 0

    cols.push({} as Column) // Dummy rowNum column
    for (const c of cells) {
      // NOTE: For assays we only return node UUIDs from sample onwards
      if (idx >= uuidStartIdx) {
        if (c.data && 'uuid' in c.data) {
          nodeUuids.push(c.data.uuid as string)
        } else nodeUuids.push(crypto.randomUUID())
      }
      rowNode.data[c.colId] = Object.assign(copy(emptyCellData), c.data)

      cols.push({
        getColDef: () => {
          return { cellRendererParams: { fieldEditable: true }}
        },
        getColId: () => { return c.colId },
        getOriginalParent: () => {
          return { getGroupId: () => { return c.groupId } } } } as Column)
      idx += 1
    }
    cols.push({
      getColId: () => { return 'col999' },
      getOriginalParent: () => {
        return { getGroupId: () => { return 'rowEdit' } }
      }
    } as Column) // Dummy rowEdit column
  }

  function getParams (): RowSaveParams {
    return {
      api: {
        getColumns: () => { return cols }
      } as unknown as GridApi,
      assayMode: false,
      finishCb: vi.fn(),
      rowNode: rowNode,
      saveData: saveData
    }
  }

  beforeEach(() => {
    vi.clearAllMocks()
    global.fetch = vi.fn(() => Promise.resolve({
      json: () => Promise.resolve(
        { detail: 'ok', node_uuids: nodeUuids }
      ), status: 200} as Response))

    setActivePinia(createPinia())
    const appStore = useAppStore()
    appStore.projectUuid = PROJECT_UUID
    appStore.sodarContext = { csrf_token: 'DummyToken' } as SodarContext
    const editStore = useEditStore()
    editStore.editContext = { samples: {} } as unknown as StudyEditContext
    editStore.updatingRow = false
    editStore.versionSaved = true
    const tableStore = useTableStore()
    tableStore.sampleColId = 'col2'
    tableStore.sampleIdx = 3
    tableStore.sourceColSpan = 1

    saveData = copy(defaultStudyRow) as RowSaveData
    setGridData(defaultStudyColInput, false)
  })

  test('save study row', async () => {
    const editStore = useEditStore()
    expect(editStore.editDataUpdated).toBe(false)
    expect(fetch).not.toHaveBeenCalled()
    const params = getParams()

    saveRow(params)
    await flushPromises()

    expect(fetch).toHaveBeenCalledWith(url, expect.objectContaining(
      { body: JSON.stringify({ new_row: saveData }) }))
    expect(rowNode.setDataValue).toHaveBeenCalledTimes(3)

    expect(rowNode.setDataValue).toHaveBeenCalledWith('col0', {
      editable: true,
      newInit: false,
      newRow: false,
      uuid: nodeUuids[0],
      value: '0814'
    })
    expect(rowNode.setDataValue).toHaveBeenCalledWith('col1', {
      editable: true,
      newInit: false,
      newRow: false,
      uuid: nodeUuids[1],
      uuidRef: TMP_UUID2,
      value: 'sample collection'
    })
    expect(rowNode.setDataValue).toHaveBeenCalledWith('col2', {
      editable: true,
      newInit: false,
      newRow: false,
      uuid: nodeUuids[2],
      value: '0814-N1'
    })
    expect(params.finishCb).toHaveBeenCalled()

    expect(editStore.editDataUpdated).toBe(true)
    expect(editStore.editContext!.samples).toEqual(
      { [nodeUuids[2] as string]: { assays: [], name: '0814-N1' } })
    expect(editStore.unsavedRow).toBe(null)
    expect(editStore.updatingRow).toBe(false)
    expect(editStore.versionSaved).toBe(false)
  })

  test('save assay row', async () => {
    const editStore = useEditStore()
    editStore.editContext!.samples![TMP_UUID3] = { assays: [], name: '0814-N1' }

    setGridData(defaultAssayColInput, true)
    saveData = copy(defaultAssayRow) as RowSaveData
    const params = getParams()
    params.assayMode = true

    saveRow(params)
    await flushPromises()

    expect(fetch).toHaveBeenCalledWith(url, expect.objectContaining(
      { body: JSON.stringify({ new_row: saveData }) }))
    expect(rowNode.setDataValue).toHaveBeenCalledTimes(4)
    expect(rowNode.setDataValue).toHaveBeenCalledWith('col2', {
      editable: true,
      newInit: false,
      newRow: false,
      uuid: TMP_UUID3,
      value: '0814-N1'
    })
    expect(rowNode.setDataValue).toHaveBeenCalledWith('col3', {
      editable: true,
      newInit: false,
      newRow: false,
      uuid: nodeUuids[1], // NOTE: Only UUIDs from sample onwards here
      uuidRef: TMP_UUID2,
      value: 'prot2'
    })
    expect(rowNode.setDataValue).toHaveBeenCalledWith('col4', {
      editable: true,
      newInit: false,
      newRow: false,
      uuid: nodeUuids[1],
      value: 'proc'
    })
    expect(rowNode.setDataValue).toHaveBeenCalledWith('col5', {
      editable: true,
      newInit: false,
      newRow: false,
      uuid: nodeUuids[2],
      value: ''
    })
    expect(params.finishCb).toHaveBeenCalled()

    // Assay UUID should be added in editContext for sample
    expect(
      editStore.editContext!.samples![TMP_UUID3].assays).toEqual([ASSAY_UUID])
  })

  test('save assay row with sample used in another assay', async () => {
    const editStore = useEditStore()
    // NOTE: The assay doesn't exist but that doesn't matter here
    const otherAssayUuid = crypto.randomUUID()
    editStore.editContext!.samples![TMP_UUID3] = {
      assays: [otherAssayUuid], name: '0814-N1'
    }

    setGridData(defaultAssayColInput, true)
    saveData = copy(defaultAssayRow) as RowSaveData
    const params = getParams()
    params.assayMode = true

    saveRow(params)
    await flushPromises()

    expect(fetch).toHaveBeenCalledWith(url, expect.objectContaining(
      { body: JSON.stringify({ new_row: saveData }) }))
    expect(rowNode.setDataValue).toHaveBeenCalledTimes(4)
    expect(params.finishCb).toHaveBeenCalled()

    // Both UUIDs should be included
    expect(
      editStore.editContext!.samples![TMP_UUID3].assays).toEqual(
        [otherAssayUuid, ASSAY_UUID])
  })

  test('handle failed save', async () => {
    const editStore = useEditStore()

    global.fetch = vi.fn(() => Promise.resolve({
        json: () => Promise.resolve({ detail: 'error' }
      ), status: 500} as Response))
    // Suppress logging as error message is expected
    vi.spyOn(console, 'error').mockImplementation(() => undefined)

    expect(fetch).not.toHaveBeenCalled()
    const params = getParams()
    saveRow(params)
    await flushPromises()

    expect(fetch).toHaveBeenCalledWith(url, expect.objectContaining(
      { body: JSON.stringify({ new_row: saveData }) }))
    expect(rowNode.setDataValue).not.toHaveBeenCalled()
    expect(params.finishCb).toHaveBeenCalled()
    expect(editStore.editDataUpdated).toBe(false)
    expect(editStore.unsavedRow).toBe(null)
    expect(editStore.updatingRow).toBe(false)
    expect(editStore.versionSaved).toBe(true)
  })
})
