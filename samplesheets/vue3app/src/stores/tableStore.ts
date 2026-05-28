import { ref } from 'vue'
import { defineStore } from 'pinia'
import { type GridApi } from 'ag-grid-community'
import {
  type SheetAssayShortcuts,
  type SheetColumnDefs,
  type SheetGridApi,
  type SheetGridOptions,
  type SheetRowData,
  type StudyEditConfig,
  type StudyDisplayConfig,
  type TableHeights
} from '@/types.ts'

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

  // return grid APIs for each grid
  function getGridApis(): Array<GridApi> {
    const ret = []
    if (gridApi.value.study)
      ret.push(gridApi.value.study)
    for (const k in gridApi.value.assays) {
      if (gridApi.value.assays[k]) {
        ret.push(gridApi.value.assays[k])
      }
    }
    return ret
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
    $reset,
    getGridApis
  }
})
