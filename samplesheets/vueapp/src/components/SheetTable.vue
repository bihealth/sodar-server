<template>
  <div :class="cardClass">
    <div class="card-header">
      <h4>{{ gridName }} Data
        <b-input-group class="sodar-header-input-group pull-right">
          <b-input-group-prepend>
            <b-button
                variant="secondary"
                v-b-tooltip.hover
                :title="'Toggle ' + gridName + ' Column Visibility'"
                class="sodar-ss-column-toggle-btn"
                @click="onColumnToggle()">
              <i class="fa fa-eye"></i>
            </b-button>
            <b-button
                variant="secondary"
                v-b-tooltip.hover
                title="Download table as Excel file (Note: not ISAtab compatible)"
                class="sodar-ss-excel-export-btn"
                :href="excelExportUrl">
              <i class="fa fa-file-excel-o"></i>
            </b-button>
          </b-input-group-prepend>
          <b-form-input
              class="sodar-ss-data-filter"
              type="text"
              placeholder="Filter"
              :id="'sodar-ss-data-filter-' + gridIdSuffix"
              @keyup="onFilterChange" />
        </b-input-group>
        <b-button
            v-if="app.editMode"
            variant="primary"
            class="sodar-header-button sodar-ss-row-insert-btn mr-2 pull-right"
            :disabled="app.unsavedRow !== null"
            @click="app.handleRowInsert(gridUuid, assayMode)">
          <i class="fa fa-plus"></i> Insert Row
        </b-button>
      </h4>
    </div>
    <div class="card-body p-0">
      <ag-grid-drag-select
          :app="app"
          :uuid="gridUuid">
        <ag-grid-vue
            class="ag-theme-bootstrap"
            :id="'sodar-ss-grid-' + gridIdSuffix"
            :ref="gridRef"
            :style="gridStyle"
            :column-defs="columnDefs"
            :row-data="rowData"
            :grid-options="gridOptions"
            :framework-components="app.frameworkComponents">
        </ag-grid-vue>
      </ag-grid-drag-select>
    </div>
  </div>
</template>

<script>
import { AgGridVue } from 'ag-grid-vue'
import AgGridDragSelect from '@/components/AgGridDragSelect.vue'

export default {
  name: 'SheetTable',
  components: {
    AgGridVue,
    AgGridDragSelect
  },
  props: [
    'app',
    'assayMode',
    'columnDefs',
    'gridOptions',
    'gridUuid',
    'rowData'
  ],
  data () {
    return {
      cardClass: null,
      gridName: null,
      excelExportUrl: null,
      gridIdSuffix: null,
      gridReady: false,
      gridRef: null,
      gridStyle: null
    }
  },
  methods: {
    /* Event Handling ------------------------------------------------------- */
    onFilterChange (event) {
      this.gridOptions.api.setQuickFilter(event.currentTarget.value)
    },
    onColumnToggle () {
      this.app.$refs.columnToggleModalRef.showModal(
        this.gridUuid, this.assayMode)
    }
  },
  beforeMount () {
    this.cardClass = 'card sodar-ss-data-card sodar-ss-data-card-'
    this.gridStyle = 'height: ' + this.app.sodarContext.table_height + 'px;'
    if (!this.assayMode) {
      this.cardClass += 'study'
      this.gridName = 'Study'
      this.excelExportUrl = 'export/excel/study/' + this.gridUuid
      this.gridIdSuffix = 'study'
      this.gridRef = 'studyGrid'
    } else {
      this.cardClass += 'assay'
      this.gridName = 'Assay'
      this.excelExportUrl = 'export/excel/assay/' + this.gridUuid
      this.gridIdSuffix = 'assay-' + this.gridUuid
      this.gridRef = 'assayGrid' + this.gridUuid
    }
  }
}
</script>

<style scoped>
</style>
