import { beforeEach, describe, expect, test, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { type ColDef, type GridApi, type IRowNode } from 'ag-grid-community'

import { deleteRow } from '@/utils/editUtils.ts'
import { useAppStore } from '@/stores/appStore.ts'
import { useEditStore } from '@/stores/editStore.ts'
import { useTableStore } from '@/stores/tableStore.ts'
import { type RowDeleteParams, type StudyEditContext } from '@/types.ts'
import {
  AJAX_RES_OK,
  DB_OBJ_CLASS_MATERIAL,
  URL_ROW_DEL_PREFIX
} from '@/constants.ts'

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
let mockColDef: ColDef
let rowDelParams: RowDeleteParams

const rowDelUrl = URL_ROW_DEL_PREFIX + PROJECT_UUID
const sourceColId = 'col1'
const sourceUuid = TMP_UUID
const sampleColId = 'col7'
const sampleUuid = TMP_UUID2

// Global Setup ----------------------------------------------------------------

function mockForEachNode (nodes: Array<object>) {
  mockGridApi.forEachNode = vi.fn((callback) => {
    nodes.forEach(node => callback(node))
  })
}

// Tests -----------------------------------------------------------------------

describe('editUtils deleteRow()', () => {
  function getMockCol (columnId: string): object {
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
          getMockCol('col0'),
          getMockCol(sourceColId),
          getMockCol(sampleColId),
          getMockCol('col999'),
        ]
      }
    }
  }

  function getMockRowNode (): object {
    return {
      data: {
        rowNum: 1,
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
    mockColDef = {
      cellEditorParams: { fieldHeader: { obj_cls: DB_OBJ_CLASS_MATERIAL } }
    } as ColDef
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
          rowNum: 2,
          [sourceColId]: { value: '0815', uuid: crypto.randomUUID() },
          [sampleColId]: { value: '0815-N1', uuid: crypto.randomUUID() }
        },
        setDataValue: setDataValue
      },
      {
        data: {
          rowNum: 3,
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
          rowNum: 2,
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
  // TODO: Test notifyCb calls
})
