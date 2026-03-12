import { ref } from 'vue'
import { defineStore } from 'pinia'
import {
  type ColGroupDef,
  type GridApi,
  type GridOptions
} from 'ag-grid-community'
import {
  type AssayShortcuts,
  type StudyEditConfig,
  type StudyDisplayConfig, type SheetTableRowData
} from '@/types.ts'

export interface SheetAssayShortcuts {
  [key: string]: AssayShortcuts
}
export interface SheetColumnDefs {
  study: Array<ColGroupDef>,
  assays: { [key: string]: Array<ColGroupDef> }
}
export interface SheetGridApi {
  study: GridApi | null,
  assays: { [key: string]: GridApi | null }
}
export interface SheetGridOptions {
  study: GridOptions,
  assays: { [key: string]: GridOptions }
}
export interface SheetRowData {
  study: Array<SheetTableRowData>,
  assays: { [key: string]: Array<SheetTableRowData> }
}
export interface TableHeights {
  study: number | null,
  assays: { [key: string]: number }
}

export const useTableStore = defineStore('table', () => {
    // Variables
    // TODO: Remove repetition for default values
    const assayShortcuts = ref<SheetAssayShortcuts>({})
    const columnDefs = ref<SheetColumnDefs>({ study: [], assays: {} })
    const gridApi = ref<SheetGridApi>({ study: null, assays: {} })
    const gridOptions = ref<SheetGridOptions>({ study: {}, assays: {} })
    const renderError = ref<string | null>(null)
    const rowData = ref<SheetRowData>({ study: [], assays: {} })
    const sampleColId = ref<string>('')
    const sampleIdx = ref<number>(-1)
    const sourceColSpan = ref<number>(-1)
    const studyDisplayConfig = ref<StudyDisplayConfig | null>(null)
    const studyEditConfig = ref<StudyEditConfig | null>(null)
    const tableHeights = ref<TableHeights | null>(null)

    // Functions
    function $reset () {
      assayShortcuts.value = {}
      columnDefs.value  = { study: [], assays: {} }
      gridApi.value = { study: null, assays: {} }
      gridOptions.value = { study: {}, assays: {} }
      renderError.value = null
      rowData.value = { study: [], assays: {} }
      sampleColId.value = ''
      sampleIdx.value = -1
      sourceColSpan.value = -1
      studyDisplayConfig.value = null
      studyEditConfig.value = null
      tableHeights.value = null
    }

    return {
        // Variables
        assayShortcuts,
        columnDefs,
        gridApi,
        gridOptions,
        renderError,
        rowData,
        sampleColId,
        sampleIdx,
        sourceColSpan,
        studyDisplayConfig,
        studyEditConfig,
        tableHeights,
        // Functions
        $reset
    }
})
