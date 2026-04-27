import { beforeEach, describe, expect, test, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { type GridApi } from 'ag-grid-community'

import { updateCellUIValues, updateCells } from '@/utils/editUtils.ts'
import { useAppStore, type SodarContext } from '@/stores/appStore.ts'
import { useEditStore } from '@/stores/editStore.ts'
import { useTableStore } from '@/stores/tableStore.ts'
import { type CellEditData } from '@/types.ts'

import { sodarContext } from '../data/sodarContext.ts'
import { copy } from '../testUtils.ts'
import {
  ASSAY_UUID,
  PROJECT_UUID,
  TMP_UUID,
  TMP_UUID2
} from '../testConstants.ts'

// TODO: Add into types, use generic alternative instead?
interface PostRequestBody {
  body: string,
  credentials: string,
  headers: object,
  method: string
}

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
const defaultRequest: PostRequestBody = {
  body: '', // To be filled out
  credentials: 'same-origin',
  headers: {
    'Accept': 'application/json',
    'Content-Type': 'application/json',
    'X-CSRFToken': sodarContext.csrf_token,
    },
  method: 'POST',
}
const editCellUrl = '/samplesheets/ajax/edit/cell/' + PROJECT_UUID

let mockGridApi: GridApi

describe('updateCells()', () => {
  function mockFetch (data: object) {
    global.fetch = vi.fn(() => Promise.resolve({
      json: () => Promise.resolve(data), status: 200} as Response)
    )
  }
  function mockFetchOk () {
    mockFetch({ detail: 'ok' })
  }
  function mockFetchAlert () {
    mockFetch({ detail: 'alert', alert_msg: 'alert message' })
  }
  function exceptFetchBody (body: object) {
    const request = copy(defaultRequest) as PostRequestBody
    request.body = JSON.stringify(body)
    expect(fetch).toHaveBeenCalledWith(editCellUrl, request)
  }

  beforeEach(() => {
    vi.clearAllMocks()
    mockGridApi = {
      forEachNode: vi.fn(),  refreshCells: vi.fn()
    } as unknown as GridApi

    // Set stores
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

describe('updateCellUIValues()', () => {
  function mockForEachNode (nodes: Array<object>) {
    mockGridApi.forEachNode = vi.fn((callback) => {
      nodes.forEach(node => callback(node))
    })
  }

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
