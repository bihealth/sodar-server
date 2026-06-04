import { beforeEach, describe, expect, test, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { type GridApi, type IRowNode } from 'ag-grid-community'

import {
  deleteRow,
  updateCellUIValues,
  updateCells
} from '@/utils/editUtils.ts'
import { useAppStore } from '@/stores/appStore.ts'
import { useEditStore } from '@/stores/editStore.ts'
import { useTableStore } from '@/stores/tableStore.ts'
import {
  type CellEditData,
  type RowDeleteParams,
  type SodarContext,
  type StudyEditContext
} from '@/types.ts'
import {
  AJAX_RES_OK,
  DB_OBJ_CLASS_MATERIAL,
  URL_ROW_DEL_PREFIX
} from '@/constants.ts'

import { sodarContext } from '../data/sodarContext.ts'
import studyTablesEdit from '../data/studyTablesEdit.json'
import { copy } from '../testUtils.ts'
import {
  ASSAY_UUID,
  PROJECT_UUID,
  STUDY_UUID,
  TMP_UUID,
  TMP_UUID2
} from '../testConstants.ts'

// Test data -------------------------------------------------------------------

let mockGridApi: GridApi
let mockRowNode: IRowNode

const defaultCell: CellEditData = {
  fieldId: 'col0',
  headerName: 'Name',
  headerType: 'name',
  itemType: 'SOURCE',
  objCls: 'GenericMaterial',
  ogValue: '0814',
  uuid: TMP_UUID,
  value: '0814-update'
}
let cell: CellEditData
const defaultRequest: RequestInit = {
  body: '', // To be filled out
  credentials: 'same-origin',
  headers: {
    'Accept': 'application/json',
    'Content-Type': 'application/json',
    'X-CSRFToken': sodarContext.csrf_token,
    },
  method: 'POST',
}

const mockColDef = {
  cellEditorParams: {
    fieldHeader: {
      obj_cls: DB_OBJ_CLASS_MATERIAL
    }
  }
}

let rowDelParams: RowDeleteParams
const editCellUrl = '/samplesheets/ajax/edit/cell/' + PROJECT_UUID
const rowDelUrl = URL_ROW_DEL_PREFIX + PROJECT_UUID
const sourceColId = 'col1'
const sourceUuid = TMP_UUID
const sampleColId = 'col7'
const sampleUuid = TMP_UUID2

// Helpers ---------------------------------------------------------------------

function mockForEachNode (nodes: Array<object>) {
  mockGridApi.forEachNode = vi.fn((callback) => {
    nodes.forEach(node => callback(node))
  })
}

// Tests for updateCells() -----------------------------------------------------

describe('updateCells()', () => {
  function mockFetch (data: object) {
    global.fetch = vi.fn(() => Promise.resolve({
      json: () => Promise.resolve(data), status: 200} as Response)
    )
  }
  function mockFetchOk () {
    mockFetch({ detail: AJAX_RES_OK })
  }
  function mockFetchAlert () {
    mockFetch({ detail: 'alert', alert_msg: 'alert message' })
  }
  function exceptFetchBody (body: object) {
    const request = copy(defaultRequest) as RequestInit
    request.body = JSON.stringify(body)
    expect(fetch).toHaveBeenCalledWith(editCellUrl, request)
  }

  beforeEach(() => {
    vi.clearAllMocks()
    mockGridApi = {
      forEachNode: vi.fn(), refreshCells: vi.fn()
    } as unknown as GridApi

    // Set up stores
    setActivePinia(createPinia())
    const appStore = useAppStore()
    appStore.projectUuid = PROJECT_UUID
    appStore.sodarContext = copy(sodarContext) as SodarContext

    const editStore = useEditStore()
    editStore.editDataUpdated = false
    editStore.versionSaved = true

    const tableStore = useTableStore()
    tableStore.gridApi.study = mockGridApi as unknown as GridApi
    tableStore.gridApi.assays[ASSAY_UUID] = mockGridApi as unknown as GridApi

    // Set data
    cell = copy(defaultCell) as CellEditData
  })

  test('update cell with default values', async () => {
    const editStore = useEditStore()
    expect(editStore.editDataUpdated).toBe(false)
    expect(editStore.versionSaved).toBe(true)
    mockFetchOk()
    expect(fetch).not.toHaveBeenCalled()

    updateCells(cell, true, undefined)
    const body = {
      updated_cells: [{
        header_name: 'Name',
        header_type: 'name',
        obj_cls: 'GenericMaterial',
        uuid: TMP_UUID,
        value: '0814-update',
        item_type: 'SOURCE'
      }],
      verify: true
    }
    exceptFetchBody(body)
    await flushPromises() // Needed to check store state
    expect(editStore.editDataUpdated).toBe(true)
    expect(editStore.versionSaved).toBe(false)
  })

  test('update cell with unit', async () => {
    cell.unit = 'unit' // Not a realistic example but works here
    mockFetchOk()
    updateCells(cell, true, undefined)
    const body = {
      updated_cells: [{
        header_name: 'Name',
        header_type: 'name',
        obj_cls: 'GenericMaterial',
        uuid: TMP_UUID,
        value: '0814-update',
        item_type: 'SOURCE',
        unit: 'unit', // Field added
      }],
      verify: true
    }
    exceptFetchBody(body)
  })

  test('update cell with no uuid', async () => {
    delete cell.uuid
    mockFetchOk()
    updateCells(cell, true, undefined)
    const body = {
      updated_cells: [{
        header_name: 'Name',
        header_type: 'name',
        obj_cls: 'GenericMaterial',
        uuid: null, // Field should be present but null
        value: '0814-update',
        item_type: 'SOURCE',
      }],
      verify: true
    }
    exceptFetchBody(body)
  })

  test('update cell with uuid_ref', async () => {
    cell.uuidRef = TMP_UUID2 // In reality uuidRef is only for protocols
    mockFetchOk()
    updateCells(cell, true, undefined)
    const body = {
      updated_cells: [{
        header_name: 'Name',
        header_type: 'name',
        obj_cls: 'GenericMaterial',
        uuid: TMP_UUID,
        value: '0814-update',
        item_type: 'SOURCE',
        uuid_ref: TMP_UUID2, // Field added
      }],
      verify: true
    }
    exceptFetchBody(body)
  })

  test('update cell with item_type and non-name header', async () => {
    cell.headerType = 'characteristics'
    mockFetchOk()
    updateCells(cell, true, undefined)
    const body = {
      updated_cells: [{
        header_name: 'Name',
        header_type: 'characteristics', // Should be updated
        obj_cls: 'GenericMaterial',
        uuid: TMP_UUID,
        value: '0814-update', // No item_type should be present
      }],
      verify: true
    }
    exceptFetchBody(body)
  })

  test('update cell with multiple cells', async () => {
    mockFetchOk()
    expect(fetch).not.toHaveBeenCalled()
    const cell2 = copy(defaultCell) as CellEditData
    cell2.headerName = 'Age'
    cell2.headerType = 'characteristics'
    cell2.value = '42'

    updateCells([cell, cell2], true, undefined)
    const body = {
      updated_cells: [{
        header_name: 'Name',
        header_type: 'name',
        obj_cls: 'GenericMaterial',
        uuid: TMP_UUID,
        value: '0814-update',
        item_type: 'SOURCE'
      },
      {
        header_name: 'Age',
        header_type: 'characteristics',
        obj_cls: 'GenericMaterial',
        uuid: TMP_UUID,
        value: '42',
      }],
      verify: true
    }
    exceptFetchBody(body)
  })

  test('update cell with verification alert returned', async () => {
    global.confirm = vi.fn()
    const editStore = useEditStore()
    expect(editStore.editDataUpdated).toBe(false)
    expect(editStore.versionSaved).toBe(true)
    mockFetchAlert() // Mock alert result
    updateCells(cell, true, undefined)
    await flushPromises()
    // Store values should remain the same
    expect(editStore.editDataUpdated).toBe(false)
    expect(editStore.versionSaved).toBe(true)
  })

  // TODO: Test with verification and confirm dialog clicked
  // TODO: Test with mocked updateCellUIValues once enabled
  // TODO: Test updateCellUIValues revert once enabled
})

// Tests for updateCellUIValues() ----------------------------------------------

describe('updateCellUIValues()', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGridApi = {
      forEachNode: vi.fn(), refreshCells: vi.fn()
    } as unknown as GridApi
  })

  test('update UI value of single cell', async () => {
    const mockNodes = [
      {
        data: {
          'col0': { value: '0814', uuid: TMP_UUID },
          'col1': { value: 'x', uuid: TMP_UUID }
        },
        setDataValue: vi.fn()
      },
      {
        data: {
          'col0': { value: '0815', uuid: TMP_UUID2 },
          'col1': { value: 'y', uuid: TMP_UUID2 }
        },
        setDataValue: vi.fn()
      }
    ]
    mockForEachNode(mockNodes)
    const cells = [copy(defaultCell) as CellEditData]

    expect(mockGridApi.forEachNode).not.toHaveBeenCalled()
    expect(mockGridApi.refreshCells).not.toHaveBeenCalled()

    updateCellUIValues(mockGridApi, cells, true, false)
    expect(mockGridApi.forEachNode).toHaveBeenCalled()
    expect(mockNodes[0]?.data['col0'].value).toBe('0814-update')
    // Other row node values should be unchanged
    expect(mockNodes[0]?.data['col1'].value).toBe('x')
    expect(mockNodes[1]?.data['col0'].value).toBe('0815')
    expect(mockNodes[1]?.data['col1'].value).toBe('y')
    // No unit should be added
    expect(mockNodes[0]?.data['col0'].hasOwnProperty('unit')).toBe(false)
    expect(mockGridApi.refreshCells).toHaveBeenCalled()
  })

  test('revert UI value', async () => {
    const mockNodes = [{
      data: { 'col0': { value: '0814', uuid: TMP_UUID } }, setDataValue: vi.fn()
    }]
    mockForEachNode(mockNodes)
    const cells = [copy(defaultCell) as CellEditData]

    expect(mockGridApi.forEachNode).not.toHaveBeenCalled()
    expect(mockGridApi.refreshCells).not.toHaveBeenCalled()

    updateCellUIValues(mockGridApi, cells, true, true) // revert=true
    expect(mockGridApi.forEachNode).toHaveBeenCalled()
    expect(mockNodes[0]?.data['col0'].value).toBe('0814')
    expect(mockNodes[0]?.data['col0'].hasOwnProperty('unit')).toBe(false)
  })

  test('update UI unit', async () => {
    const mockNodes = [{
      data: {
        'col0': { value: '0814', unit: 'day', uuid: TMP_UUID } },
        setDataValue: vi.fn()
    }]
    mockForEachNode(mockNodes)
    const cells = [copy(defaultCell) as CellEditData]
    cells[0]!.unit = 'year'
    cells[0]!.ogUnit = 'day'
    updateCellUIValues(mockGridApi, cells, true, false)
    expect(mockNodes[0]?.data['col0'].value).toBe('0814-update')
    expect(mockNodes[0]?.data['col0'].unit).toBe('year')
  })

  test('revert UI unit', async () => {
    const mockNodes = [{
      data: {
        'col0': { value: '0814', unit: 'day', uuid: TMP_UUID } },
        setDataValue: vi.fn()
    }]
    mockForEachNode(mockNodes)
    const cells = [copy(defaultCell) as CellEditData]
    cells[0]!.unit = 'year'
    cells[0]!.ogUnit = 'day'
    updateCellUIValues(mockGridApi, cells, true, true) // revert=true
    expect(mockNodes[0]?.data['col0'].value).toBe('0814')
    expect(mockNodes[0]?.data['col0'].unit).toBe('day')
  })
})

// Tests for deleteRow() -------------------------------------------------------

describe('deleteRow()', () => {
  function getMockColumn (columnId: string): object {
    return {
      getColId: () => { return columnId },
      getColDef: () => { return mockColDef }
    }
  }

  function getMockGridApi (): object {
    return {
      applyTransaction: vi.fn(),
      forEachNode: vi.fn(),
      getColumns: () => {
        // NOTE: Dummy 1st and last columns needed to emulate real table
        return [
          getMockColumn('col0'),
          getMockColumn(sourceColId),
          getMockColumn(sampleColId),
          getMockColumn('col999'),
        ]
      }
    }
  }

  function getMockRowNode (): object {
    return {
      data: {
        'rowNum': 1,
        'col0': { value: 'col0' },
        [sourceColId]: { value: '0814', uuid: sourceUuid },
        [sampleColId]: { value: '0814-N1', uuid: sampleUuid },
        'col999': { value: 'xxx' }
      },
      id: '0'
    }
  }

  function getRowDelParams (): RowDeleteParams {
    return {
      api: mockGridApi,
      assayMode: false,
      finishCb: vi.fn(),
      rowNode: mockRowNode,
      tableUuid: STUDY_UUID
    }
  }

  function mockFetch (data: object) {
    global.fetch = vi.fn(() => Promise.resolve({
      json: () => Promise.resolve(data), status: 200} as Response)
    )
  }

  function mockFetchOk () {
    mockFetch({ detail: AJAX_RES_OK })
  }

  beforeEach(() => {
    vi.clearAllMocks()

    // Set up stores
    setActivePinia(createPinia())
    const appStore = useAppStore()
    appStore.currentStudyUuid = STUDY_UUID
    appStore.projectUuid = PROJECT_UUID

    const editStore = useEditStore()
    editStore.editContext = copy(
      studyTablesEdit.edit_context) as StudyEditContext
    editStore.editContext.samples = {
      [sampleUuid]: { name: '0814-N1', assays: [] } }
    editStore.editDataUpdated = false
    editStore.unsavedRow = null
    editStore.updatingRow = false

    const tableStore = useTableStore()
    tableStore.sampleColId = sampleColId
    tableStore.sampleIdx = 2

    // Set up default data and mocks
    mockGridApi = getMockGridApi() as unknown as GridApi
    mockRowNode = getMockRowNode() as unknown as IRowNode
    rowDelParams = getRowDelParams()
    mockFetchOk()
  })

  test('delete row', async () => {
    const editStore = useEditStore()
    expect(Object.keys(editStore.editContext!.samples)).toContain(sampleUuid)
    expect(mockGridApi.applyTransaction).not.toHaveBeenCalled()
    expect(fetch).not.toHaveBeenCalled()
    expect(rowDelParams.finishCb).not.toHaveBeenCalled()

    deleteRow(rowDelParams)
    await flushPromises()

    // Sample should be removed from context
    expect(Object.keys(
      editStore.editContext!.samples)).not.toContain(sampleUuid)
    expect(mockGridApi.applyTransaction).toHaveBeenCalledWith(
      { remove: [mockRowNode.data] })
    const resBody = {
      del_row: {
        assay: null,
        nodes: [
          { obj_cls: DB_OBJ_CLASS_MATERIAL, uuid: sourceUuid },
          { obj_cls: DB_OBJ_CLASS_MATERIAL, uuid: sampleUuid }
        ],
        study: STUDY_UUID
      }
    }
    expect(fetch).toHaveBeenCalledWith(
      rowDelUrl, expect.objectContaining({ body: JSON.stringify(resBody) }))
    expect(rowDelParams.finishCb).toHaveBeenCalled()
  })

  test('update row numbers on row delete', async () => {
    const setDataValue = vi.fn()
    const setDataValue2 = vi.fn()
    const mockNodes = [
      {
        data: {
          'rowNum': 2,
          [sourceColId]: { value: '0815', uuid: crypto.randomUUID() },
          [sampleColId]: { value: '0815-N1', uuid: crypto.randomUUID() }
        },
        setDataValue: setDataValue
      },
      {
        data: {
          'rowNum': 3,
          [sourceColId]: { value: '0816', uuid: crypto.randomUUID() },
          [sampleColId]: { value: '0816-N1', uuid: crypto.randomUUID() }
        },
        setDataValue: setDataValue2
      }
    ]
    mockForEachNode(mockNodes)
    expect(setDataValue).not.toHaveBeenCalled()
    expect(setDataValue2).not.toHaveBeenCalled()

    deleteRow(rowDelParams)
    await flushPromises()

    expect(setDataValue).toHaveBeenCalledWith('rowNum', 1)
    expect(setDataValue2).toHaveBeenCalledWith('rowNum', 2)
  })

  test('delete row with study and sample found on another row', async () => {
    const editStore = useEditStore()
    const mockNodes = [
      {
        data: {
          'rowNum': 2,
          [sourceColId]: { value: '0814', uuid: crypto.randomUUID() },
          [sampleColId]: { value: '0814-N1', uuid: sampleUuid } // Same sample
        },
        id: '1', // Different ID than row to be deleted
        setDataValue: vi.fn()
      }
    ]
    mockForEachNode(mockNodes)

    deleteRow(rowDelParams)
    await flushPromises()

    // Sample should not be removed from context
    expect(Object.keys(editStore.editContext!.samples)).toContain(sampleUuid)
    expect(mockGridApi.applyTransaction).toHaveBeenCalled()
    expect(fetch).toHaveBeenCalled()
    expect(rowDelParams.finishCb).toHaveBeenCalled()
  })

  test('delete row with assay', async () => {
    const editStore = useEditStore()
    // Set assay mode
    rowDelParams.assayMode = true
    rowDelParams.tableUuid = ASSAY_UUID
    expect(Object.keys(editStore.editContext!.samples)).toContain(sampleUuid)

    deleteRow(rowDelParams)
    await flushPromises()

    // Sample should remain in context
    expect(Object.keys(
      editStore.editContext!.samples)).toContain(sampleUuid)
    expect(mockGridApi.applyTransaction).toHaveBeenCalledWith(
      { remove: [mockRowNode.data] })
    // Deletion should only happen from sample onwards
    const resBody = {
      del_row: {
        assay: ASSAY_UUID, // Assay should be included
        nodes: [{ obj_cls: DB_OBJ_CLASS_MATERIAL, uuid: sampleUuid }],
        study: STUDY_UUID
      }
    }
    expect(fetch).toHaveBeenCalledWith(
      rowDelUrl, expect.objectContaining({ body: JSON.stringify(resBody) }))
    expect(rowDelParams.finishCb).toHaveBeenCalled()
  })

  test('delete row with assay and sample used in current assay', async () => {
    const editStore = useEditStore()
    // Add other samples to context
    editStore.editContext!.samples[sampleUuid]!.assays = [
      ASSAY_UUID, crypto.randomUUID()]
    rowDelParams.assayMode = true
    rowDelParams.tableUuid = ASSAY_UUID

    expect(editStore.editContext!.samples[sampleUuid]!.assays.length).toBe(2)
    expect(editStore.editContext!.samples[sampleUuid]!.assays).toContain(
      ASSAY_UUID)

    deleteRow(rowDelParams)
    await flushPromises()

    // Assay table should be removed from sample in context
    expect(editStore.editContext!.samples[sampleUuid]!.assays.length).toBe(1)
    expect(editStore.editContext!.samples[sampleUuid]!.assays).not.toContain(
      ASSAY_UUID)
    expect(mockGridApi.applyTransaction).toHaveBeenCalled()
    expect(fetch).toHaveBeenCalled()
    expect(rowDelParams.finishCb).toHaveBeenCalled()
  })

  test('handle unsuccessful response', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => undefined)
    mockFetch({ detail: 'Error' })
    deleteRow(rowDelParams)
    await flushPromises()
    // Grid should not have been updated
    expect(mockGridApi.applyTransaction).not.toHaveBeenCalled()
    expect(fetch).toHaveBeenCalled()
    expect(rowDelParams.finishCb).toHaveBeenCalled()
  })

  // TODO: Test with extra nodes to ensure they get added to ajax request
})
