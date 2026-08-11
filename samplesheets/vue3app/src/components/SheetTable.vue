<script setup lang="ts">
import { ref } from 'vue'
import { BButton, BFormInput, BInputGroup } from 'bootstrap-vue-next'
import { AgGridVue } from 'ag-grid-vue3'
import {
  type GridApi,
  type GridOptions,
  type GridReadyEvent
} from 'ag-grid-community'

import { useAppStore } from '@/stores/appStore.ts'
import { useEditStore } from '@/stores/editStore.ts'
import { useTableStore } from '@/stores/tableStore.ts'
import { insertRow } from '@/utils/editUtils.ts'
import { ROW_INS_MSG_DISABLED } from '@/constants.ts'

// External --------------------------------------------------------------------

const appStore = useAppStore()
const editStore = useEditStore()
const tableStore = useTableStore()
const props = defineProps([
  'assayMode',
  'colToggleModalRef',
  'notifyCb',
  'tableUuid',
])

// Refs ------------------------------------------------------------------------

const filterVal = ref<string>('')
const tableHeight = ref<number>(400)

// Internal --------------------------------------------------------------------

let cardClass: string = 'card sodar-ss-data-card sodar-ss-data-card-'
let tableType: string
let excelExportUrl: string = 'export/excel/'
let gridIdSuffix: string
let gridId: string = 'sodar-ss-table-grid-'
let gridApi: GridApi
let gridOptions: GridOptions
let colDefs
let rowData

// Data setup ------------------------------------------------------------------

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

// Helpers ---------------------------------------------------------------------

function getControlColClass () {
  return appStore.editMode ? 'col-sm-4' : 'col-sm-3'
}

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

function onRowInsert () {
  // TODO: Provide notifyCb
  insertRow({
    api: gridApi,
    assayMode: props.assayMode,
    tableUuid: props.tableUuid,
  })
}
</script>

<template>
  <div :class="cardClass">
    <div class="card-header">
      <div class="row">
        <div class="col p-0 sodar-ss-data-card-title">
          <h4>{{ tableTitle }} Table</h4>
        </div>
        <div :class="'col p-0 ' + getControlColClass()">
          <BInputGroup
              class="sodar-ss-header-input-group mr-0 ml-auto">
            <BButton
                v-if="appStore.editMode"
                variant="primary"
                class="sodar-ss-row-insert-btn mr-2 pull-right"
                :title="editStore.unsavedRow ? ROW_INS_MSG_DISABLED : ''"
                :disabled="editStore.unsavedRow !== null"
                @click="onRowInsert()">
              <i class="iconify" data-icon="mdi:plus-thick"></i> Insert Row
            </BButton>
            <BButton
                class="sodar-ss-table-header-btn sodar-ss-column-toggle-btn"
                variant="secondary"
                :title="'Toggle ' + tableType + ' column visibility'"
                @click="colToggleModalRef.show(
                        tableUuid, assayMode, notifyCb)">
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
/* NOTE: Not using SODAR Core sodar-header-input-group */
.sodar-ss-header-input-group {
  white-space: nowrap;
  padding-right: 0;
}
.sodar-ss-header-input-group button,
.sodar-ss-header-input-group a {
  height: 30px;
  padding-top: 3px;
}

.sodar-ss-header-input-group input {
  height: 30px;
}
</style>
