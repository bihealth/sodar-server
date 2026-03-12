<script setup lang="ts">
import { ref } from 'vue'
import { BButton, BFormInput, BInputGroup } from 'bootstrap-vue-next'
import { AgGridVue } from 'ag-grid-vue3'
import {
  type GridApi,
  type GridOptions,
  type GridReadyEvent
} from 'ag-grid-community'
import { useTableStore } from '@/stores/tableStore.ts'

const tableStore = useTableStore()
const props = defineProps(['assayMode', 'colToggleModalRef', 'tableUuid'])

const filterVal = ref<string>('')
const tableHeight = ref<number>(400)

let cardClass: string = 'card sodar-ss-data-card sodar-ss-data-card-'
let tableType: string
let excelExportUrl: string = 'export/excel/'
let gridIdSuffix: string
let gridId: string = 'sodar-ss-table-grid-'
let gridApi: GridApi
let gridOptions: GridOptions
let colDefs
let rowData

if (!props.assayMode) {
  // Setup study
  gridOptions = tableStore.gridOptions.study as GridOptions
  colDefs = tableStore.columnDefs.study
  rowData = tableStore.rowData.study
  tableType = 'study'
  gridIdSuffix = tableType
  tableHeight.value = tableStore.tableHeights?.study as number
  gridId += tableType
} else {
  // Setup assay
  gridOptions = tableStore.gridOptions.assays[props.tableUuid] as GridOptions
  colDefs = tableStore.columnDefs.assays[props.tableUuid]
  rowData = tableStore.rowData.assays[props.tableUuid]
  tableType = 'assay'
  gridIdSuffix = tableType + '-' + props.tableUuid
  tableHeight.value = tableStore.tableHeights?.assays[props.tableUuid] as number
  gridId += tableType + '-' + props.tableUuid
}

excelExportUrl += tableType + '/' + props.tableUuid
cardClass += tableType
const tableTitle: string = tableType[0]!.toUpperCase() + tableType.slice(1)

// Handle grid ready event to store grid API
function onGridReady (params: GridReadyEvent) {
  if (!props.assayMode) tableStore.gridApi.study = params.api
  else tableStore.gridApi.assays[props.tableUuid] = params.api
  gridApi = params.api
}

// Update table filter
function onFilterUpdate () {
  gridApi.setGridOption('quickFilterText', filterVal.value)
}
</script>

<template>
  <div :class="cardClass">
    <div class="card-header">
      <div class="row">
        <div class="col p-0 sodar-ss-data-card-title">
          <h4>{{ tableTitle }} Table</h4>
        </div>
        <div class="col p-0">
          <BInputGroup
              class="sodar-header-input-group ml-auto">
            <BButton
                class="sodar-ss-table-header-btn sodar-ss-column-toggle-btn"
                variant="secondary"
                :title="'Toggle ' + tableType + ' column visibility'"
                @click="props.colToggleModalRef.show(
                          props.tableUuid, props.assayMode)">
              <i class="iconify" data-icon="mdi:eye"></i>
            </BButton>
            <BButton
                class="sodar-ss-table-header-btn sodar-ss-excel-export-btn"
                variant="secondary"
                :href="excelExportUrl"
                title="Download table as Excel file (Note: not ISA-Tab
                       compatible)">
              <i class="iconify" data-icon="mdi:file-excel-outline"></i>
            </BButton>
            <BFormInput
                class="sodar-ss-data-filter"
                type="text"
                placeholder="Filter"
                :id="'sodar-ss-data-filter-' + gridIdSuffix"
                v-model="filterVal"
                @keyup="onFilterUpdate">
            </BFormInput>
          </BInputGroup>
        </div>
      </div>
    </div>
    <div class="card-body p-0">
      <AgGridVue
          v-if="colDefs && rowData"
          :id="gridId"
          :grid-options="gridOptions"
          :column-defs="colDefs"
          :row-data="rowData"
          :style="'height: ' + tableHeight + 'px;'"
          @grid-ready="onGridReady">
      </AgGridVue>
    </div>
  </div>
</template>

<style scoped>
div.sodar-ss-data-card-title {
  width: 300px;
}
/* Rounding CSS fails by default, possibly due to BS4 conflict? */
.sodar-ss-table-header-btn {
  padding-left: 10px;
  padding-right: 10px;
  border-top-right-radius: 0 !important;
  border-bottom-right-radius: 0 !important;
}
.sodar-ss-excel-export-btn {
  border-top-left-radius: 0 !important;
  border-bottom-left-radius: 0 !important;
}
</style>
