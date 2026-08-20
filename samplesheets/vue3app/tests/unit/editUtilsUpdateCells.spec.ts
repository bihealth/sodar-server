import { beforeEach, describe, expect, test, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { type GridApi } from 'ag-grid-community'

import { updateCells } from '@/utils/editUtils.ts'
import { useAppStore } from '@/stores/appStore.ts'
import { useEditStore } from '@/stores/editStore.ts'
import { useTableStore } from '@/stores/tableStore.ts'
import { type CellEditData, type SodarContext } from '@/types.ts'
import {
  AJAX_RES_OK,
  CELL_UPDATE_FAIL_PREFIX,
  VARIANT_DANGER
} from '@/constants.ts'

import { sodarContext } from '../data/sodarContext.ts'
import { copy } from '../testUtils.ts'
import {
  ASSAY_UUID,
  PROJECT_UUID,
  TMP_UUID,
  TMP_UUID2
} from '../testConstants.ts'

// Test Data -------------------------------------------------------------------

let cell: CellEditData
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
const editCellUrl = '/samplesheets/ajax/edit/cell/' + PROJECT_UUID
let mockGridApi: GridApi

// Global Setup ----------------------------------------------------------------

const mockNotifyCb = vi.fn()

// Tests for updateCells() -----------------------------------------------------

describe('updateCells()', () => {
  function mockFetch (data: object, status: number) {
    global.fetch = vi.fn(() => Promise.resolve({
      json: () => Promise.resolve(data), status: status} as Response)
    )
  }
  function mockFetchOk () {
    mockFetch({ detail: AJAX_RES_OK }, 200)
  }
  function mockFetchAlert () {
    mockFetch({ detail: 'alert', alert_msg: 'alert message' }, 200)
  }
  function mockFetchError () {
    mockFetch({ detail: 'error' }, 500)
  }
  function exceptFetchBody (body: object) {
    const request = copy(defaultRequest) as RequestInit
    request.body = JSON.stringify(body)
    expect(fetch).toHaveBeenCalledWith(editCellUrl, request)
  }

  beforeEach(() => {
    vi.clearAllMocks()
    mockGridApi = {
      forEachNode: vi.fn(),
      refreshCells: vi.fn()
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

    updateCells(cell, true, mockNotifyCb)
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
    // Notify callback should not be called with success
    expect(mockNotifyCb).not.toHaveBeenCalled()
  })

  test('update cell with unit', async () => {
    cell.unit = 'unit' // Not a realistic example but works here
    mockFetchOk()
    updateCells(cell, true, mockNotifyCb)
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
    expect(mockNotifyCb).not.toHaveBeenCalled()
  })

  test('update cell with no uuid', async () => {
    delete cell.uuid
    mockFetchOk()
    updateCells(cell, true, mockNotifyCb)
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
    expect(mockNotifyCb).not.toHaveBeenCalled()
  })

  test('update cell with uuid_ref', async () => {
    cell.uuidRef = TMP_UUID2 // In reality uuidRef is only for protocols
    mockFetchOk()
    updateCells(cell, true, mockNotifyCb)
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
    expect(mockNotifyCb).not.toHaveBeenCalled()
  })

  test('update cell with item_type and non-name header', async () => {
    cell.headerType = 'characteristics'
    mockFetchOk()
    updateCells(cell, true, mockNotifyCb)
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
    expect(mockNotifyCb).not.toHaveBeenCalled()
  })

  test('update cell with multiple cells', async () => {
    mockFetchOk()
    expect(fetch).not.toHaveBeenCalled()
    const cell2 = copy(defaultCell) as CellEditData
    cell2.headerName = 'Age'
    cell2.headerType = 'characteristics'
    cell2.value = '42'

    updateCells([cell, cell2], true, mockNotifyCb)
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
    expect(mockNotifyCb).not.toHaveBeenCalled()
  })

  test('update cell with verification alert returned', async () => {
    global.confirm = vi.fn()
    const editStore = useEditStore()
    expect(editStore.editDataUpdated).toBe(false)
    expect(editStore.versionSaved).toBe(true)
    mockFetchAlert() // Mock alert result
    updateCells(cell, true, mockNotifyCb)
    await flushPromises()
    // Store values should remain the same
    expect(editStore.editDataUpdated).toBe(false)
    expect(editStore.versionSaved).toBe(true)
    expect(mockNotifyCb).not.toHaveBeenCalled()
  })

  test('update cell with error', async () => {
    // Suppress logging as error message is expected
    vi.spyOn(console, 'error').mockImplementation(() => undefined)
    const editStore = useEditStore()
    mockFetchError()
    updateCells(cell, true, mockNotifyCb)
    expect(fetch).toHaveBeenCalled()
    await flushPromises()
    // Edit store data should remain
    expect(editStore.editDataUpdated).toBe(false)
    expect(editStore.versionSaved).toBe(true)
    // Notify callback should be called with failure
    expect(mockNotifyCb).toHaveBeenCalledWith(
      CELL_UPDATE_FAIL_PREFIX + 'error', VARIANT_DANGER)
  })

  test('update cell with error without notify callback', async () => {
    // Suppress logging as error message is expected
    vi.spyOn(console, 'error').mockImplementation(() => undefined)
    const editStore = useEditStore()
    mockFetchError()
    updateCells(cell, true) // No callback
    expect(fetch).toHaveBeenCalled()
    await flushPromises()
    // No error should be raised even if callback is not present
    expect(editStore.editDataUpdated).toBe(false)
    expect(editStore.versionSaved).toBe(true)
  })

  // TODO: Test with verification and confirm dialog clicked
})
