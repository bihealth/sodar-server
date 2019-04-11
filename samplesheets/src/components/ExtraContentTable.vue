<template>
  <div class="card">
    <div class="card-header">
      <h4>
        {{ tableData['title'] }}
        <b-input-group
            v-if="filter"
            class="sodar-header-input-group pull-right">
          <b-form-input
              class="sodar-ss-data-filter"
              type="text"
              placeholder="Filter"
              @keyup="onFilterChange" />
        </b-input-group>
      </h4>
    </div>
    <div class="card-body p-0">
      <ag-grid-vue
        style="height: 250px;"
        class="ag-theme-bootstrap"
        :columnDefs="columnDefs"
        :rowData="rowData"
        :gridOptions="gridOptions"
        @grid-ready="onGridReady">
      </ag-grid-vue>
    </div>
  </div>
</template>

<script>
import {AgGridVue} from 'ag-grid-vue'
import ExtraTableRenderer from './renderers/ExtraTableRenderer.vue'

export default {
  name: 'ExtraContentTable',
  components: {
    AgGridVue
  },
  props: [
    'app',
    'tableData',
    'filter'
  ],
  data () {
    return {
      gridOptions: null,
      columnDefs: null,
      rowData: null
    }
  },
  methods: {
    onGridReady (params) {
      // this.gridApi = params.api
      // this.columnApi = params.columnApi
      // this.columnApi.autoSizeAllColumns()
    },
    onFilterChange (event) {
      // NOTE: Currently filtering only works on "label" type data..
      //       To make it work with links, we need to do a colMeta -style
      //       solution (see App.vue)
      this.gridOptions.api.setQuickFilter(event.target.value)
    }
  },
  beforeMount () {
    // Set up grid options
    this.gridOptions = {
      // debug: true,
      pagination: false,
      animateRows: false,
      rowSelection: 'single',
      suppressMovableColumns: true,
      suppressColumnMoveAnimation: true,
      singleClickEdit: false,
      headerHeight: 38,
      rowHeight: 38,
      suppressColumnVirtualisation: false,
      context: {
        componentParent: this
      },
      defaultColDef: {
        editable: false,
        resizable: true,
        sortable: false, // Can't sort with object values and custom renderer :(
        cellClass: [
          'sodar-ss-data-cell'
        ]
      }
    }

    // Set up column definitions
    this.columnDefs = []

    for (let i = 0; i < this.tableData['cols'].length; i++) {
      let colData = this.tableData['cols'][i]
      let col = {
        headerName: colData['name'],
        field: colData['field'],
        cellRendererFramework: ExtraTableRenderer,
        cellRendererParams: {
          'colType': colData['type']
        }
      }
      if (colData['type'] === 'label') {
        col['sortable'] = true // String as value for this one -> sorting ok
      }
      this.columnDefs.push(col)
    }

    // Set up rows
    this.rowData = []

    for (let i = 0; i < this.tableData['rows'].length; i++) {
      let row = {}
      let rowData = this.tableData['rows'][i]

      for (let j = 0; j < this.tableData['cols'].length; j++) {
        let colData = this.tableData['cols'][j]
        row[colData['field']] = rowData[j]

        if (colData['type'] === 'label') {
          row[colData['field']] = rowData[j]['label']
        } else {
          row[colData['field']] = rowData[j]
        }
      }
      this.rowData.push(row)
    }
    // NOTE: Doing this here because if within onGridReady(), content jumps
    this.$nextTick(function () {
      this.gridOptions.columnApi.autoSizeAllColumns()
      this.gridOptions.api.sizeColumnsToFit()
    })
  }
}
</script>

<style scoped>
</style>
