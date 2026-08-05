import { beforeEach, describe, expect, test, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { type GridApi } from 'ag-grid-community'

import { insertRow } from '@/utils/editUtils.ts'
import { useEditStore } from '@/stores/editStore.ts'
import { useTableStore } from '@/stores/tableStore.ts'
import { type RowInsertParams } from '@/types.ts'

import { ASSAY_UUID, STUDY_UUID } from '../testConstants.ts'

// Test data -------------------------------------------------------------------

let mockGridApi: GridApi
let rowInsParams: RowInsertParams
const sourceColId = 'col1'
const sampleColId = 'col7'

// Tests for insertRow() -------------------------------------------------------

describe('insertRow()', () => {
  function getMockCol (columnId: string): object {
    return { getColId: () => { return columnId } }
  }

  function getMockGridApi (): object {
    return {
      applyTransaction: vi.fn().mockReturnValue(
        { add: [ { id: '2', rowIndex: 2 } ]}),
      ensureColumnVisible: vi.fn(),
      ensureIndexVisible: vi.fn(),
      getColumns: () => {
        // NOTE: Dummy 1st and last columns needed to emulate real table
        return [
          getMockCol('col0'),
          getMockCol(sourceColId),
          getMockCol(sampleColId),
          getMockCol('col999'),
        ]
      },
      getDisplayedRowCount: () => { return 1 }
    }
  }

  function getRowInsertParams (): RowInsertParams {
    return {
      api: mockGridApi,
      assayMode: false,
      tableUuid: STUDY_UUID
    }
  }

  beforeEach(() => {
    vi.clearAllMocks()

    setActivePinia(createPinia())
    const editStore = useEditStore()
    editStore.unsavedRow = null
    const tableStore = useTableStore()
    tableStore.sampleColId = sampleColId

    // Set up default data and mocks
    mockGridApi = getMockGridApi() as unknown as GridApi
    rowInsParams = getRowInsertParams()
  })

  test('insert study row', async () => {
    const editStore = useEditStore()
    expect(editStore.unsavedRow).toBe(null)
    expect(mockGridApi.applyTransaction).not.toHaveBeenCalled()
    expect(mockGridApi.ensureIndexVisible).not.toHaveBeenCalled()
    expect(mockGridApi.ensureColumnVisible).not.toHaveBeenCalled()
    insertRow(rowInsParams)
    expect(editStore.unsavedRow).toEqual({
      id: '2',
      tableUuid: STUDY_UUID
    })
    const trans = [{
      rowNum: 2,
      [sourceColId]: {
        editable: true, // Study = only first column should be editable
        newInit: true,
        newRow: true,
        uuid: '',
        value: '',
      },
      [sampleColId]: {
        editable: false,
        newInit: true,
        newRow: true,
        uuid: '',
        value: '',
      }
    }]
    expect(mockGridApi.applyTransaction).toHaveBeenCalledWith({ add: trans })
    expect(mockGridApi.ensureIndexVisible).toHaveBeenCalledWith(2)
    expect(mockGridApi.ensureColumnVisible).toHaveBeenCalledWith('col1')
  })

  test('insert assay row', async () => {
    const editStore = useEditStore()
    rowInsParams.assayMode = true
    rowInsParams.tableUuid = ASSAY_UUID
    insertRow(rowInsParams)
    expect(editStore.unsavedRow).toEqual({
      id: '2',
      tableUuid: ASSAY_UUID
    })
    const trans = [{
      rowNum: 2,
      [sourceColId]: {
        editable: false,
        newInit: true,
        newRow: true,
        uuid: '',
        value: '',
      },
      [sampleColId]: {
        editable: true, // Assay = only sample column should be editable
        newInit: true,
        newRow: true,
        uuid: '',
        value: '',
      }
    }]
    expect(mockGridApi.applyTransaction).toHaveBeenCalledWith({ add: trans })
    expect(mockGridApi.ensureIndexVisible).toHaveBeenCalledWith(2)
    // Table should be scrolled to sample name column
    expect(mockGridApi.ensureColumnVisible).toHaveBeenCalledWith(sampleColId)
  })
})
