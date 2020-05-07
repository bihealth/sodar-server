<template>
  <b-modal id="sodar-ss-vue-col-toggle-modal" ref="columnToggleModal"
           no-fade hide-footer
           size="md">

    <template slot="modal-header">
      <h5 class="modal-title text-nowrap mr-5">{{ title }}</h5>
      <b-input
          id="sodar-ss-vue-col-filter"
          size="sm"
          placeholder="Filter"
          @keyup="onFilterChange">
      </b-input>
      <button
          type="button"
          class="close"
          @click="hideModal">
        ×
      </button>
    </template>

    <div v-if="columnList"
         id="sodar-ss-vue-col-toggle-modal-content">
      <table v-for="(topHeader, index) in columnList"
             :key="index"
             v-show="index < columnList.length - 1 ||
                     topHeader.children.length > 0"
             class="table sodar-card-table sodar-ss-vue-toggle-table">
        <tr class="sodar-ss-vue-toggle-header">
          <th :class="getTopHeaderClasses(topHeader)">
            {{ topHeader.headerName }}
          </th>
          <th :class="getTopHeaderClasses(topHeader)">
            <b-checkbox indeterminate plain
                v-if="topHeader.children.length > 0 && !filterActive"
                :checked="false"
                @change="onGroupChange($event, topHeader)">
            </b-checkbox>
          </th>
        </tr>
        <tr v-for="(header, index) in topHeader.children"
            v-show="header.visibleInList"
            :key="index"
            class="sodar-ss-vue-toggle-row">
          <td>
            {{ header.headerName }}
            <span v-if="app.editMode && header.editable"
                class="text-muted font-italic pull-right">
              Editable
            </span>
            <span v-else-if="!columnDataExists(header)"
                class="text-muted font-italic pull-right">
              No data
            </span>
          </td>
          <td>
            <b-checkbox plain
                :checked="getColumnVisibility(header)"
                @change="onColumnChange($event, header)">
            </b-checkbox>
          </td>
        </tr>
      </table>
    </div>
  </b-modal>
</template>

<script>
export default {
  name: 'ColumnToggleModal',
  props: [
    'app'
  ],
  data () {
    return {
      uuid: null,
      assayMode: null,
      title: null,
      gridOptions: null,
      columnApi: null,
      columnDefs: null,
      columnList: null,
      columnValues: null,
      filterActive: false
    }
  },
  methods: {
    getTitle () {
      if (this.assayMode) {
        return 'Toggle Assay Columns'
      } else {
        return 'Toggle Study Columns'
      }
    },

    columnDataExists (header) {
      return this.columnValues[header.field]
    },

    getTopHeaderClasses (topHeader) {
      return topHeader.headerClass.join(' ')
    },

    getColumnVisibility (header) {
      return this.columnApi.getColumn(header.field).visible
    },

    onFilterChange (event) {
      const inputVal = event.currentTarget.value.toLowerCase()

      if (inputVal.length === 0) {
        this.filterActive = false
      } else {
        this.filterActive = true
      }

      for (let i = 0; i < this.columnList.length; i++) {
        for (let j = 0; j < this.columnList[i].children.length; j++) {
          if (inputVal.length === 0 ||
              this.columnList[i].children[j].headerName.toLowerCase().includes(inputVal)) {
            this.$set(this.columnList[i].children[j], 'visibleInList', true)
          } else {
            this.$set(this.columnList[i].children[j], 'visibleInList', false)
          }
        }
      }

      this.$forceUpdate()
    },
    onColumnChange (event, header) {
      this.columnApi.setColumnVisible(header.field, event)
    },

    onGroupChange (event, topHeader) {
      for (let i = 0; i < topHeader.children.length; i++) {
        this.columnApi.setColumnVisible(topHeader.children[i].field, event)
      }
    },

    showModal (uuid, assayMode) {
      // Reset data
      this.columnDefs = null
      this.columnList = []
      this.columnValues = null
      this.filterActive = false

      // Get data
      this.uuid = uuid
      this.assayMode = assayMode
      this.gridOptions = this.app.getGridOptionsByUuid(this.uuid)
      this.columnApi = this.gridOptions.columnApi
      this.columnDefs = this.gridOptions.columnDefs
      const rowData = this.gridOptions.rowData

      if (!assayMode) {
        this.title = 'Toggle Study Columns'
      } else {
        this.title = 'Toggle Assay Columns'
      }

      // Store current column data state
      this.columnValues = {}
      for (let i = 1; i < this.columnDefs.length; i++) {
        for (let j = 0; j < this.columnDefs[i].children.length; j++) {
          this.columnValues[this.columnDefs[i].children[j].field] = false
        }
      }
      for (const key in this.columnValues) {
        for (let i = 0; i < rowData.length; i++) {
          if (rowData[i][key].value) {
            this.columnValues[key] = true
            break
          }
        }
      }

      function getListGroup (colDef, firstColIdx, headerName, headerClass) {
        const headerGroup = {
          headerName: headerName || colDef.headerName,
          headerClass: headerClass || colDef.headerClass,
          children: []
        }

        for (let i = firstColIdx; i < colDef.children.length; i++) {
          const child = colDef.children[i]
          child.visibleInList = true
          headerGroup.children.push(child)
        }

        return headerGroup
      }

      // First build source column separately
      // This is needed because we have to split the top header group
      this.columnList.push(
        getListGroup(
          this.columnDefs[2],
          0, // First column index is 0 for the second source header group
          this.columnDefs[1].headerName,
          this.columnDefs[1].headerClass
        )
      )

      const firstTopIdx = 3 // First top header index for modification
      const lastColName = this.columnDefs[this.columnDefs.length - 1].headerName.toLowerCase()
      let lastColIdx = this.columnDefs.length // Last column index to include in list

      if (['irods', 'links'].includes(lastColName)) {
        lastColIdx -= 1
      }

      // Iterate through the rest of the columns
      for (let i = firstTopIdx; i < lastColIdx; i++) {
        this.columnList.push(getListGroup(this.columnDefs[i], 1))
      }

      // Show element
      this.$refs.columnToggleModal.show()
    },

    hideModal () {
      this.$refs.columnToggleModal.hide()
    }
  }
}
</script>

<style scoped>

table.sodar-ss-vue-toggle-table tr th,
table.sodar-ss-vue-toggle-table tr td {
  height: 38px;
  line-height: 24px;
  padding-top: 0;
  padding-bottom: 0;
  vertical-align: middle;
}

table.sodar-ss-vue-toggle-table tr th {
  border-top: 0 !important;
  border-bottom: 1px solid #ffffff !important;
}

table.sodar-ss-vue-toggle-table tr:first-child td {
  border-top: 0;
}

tr.sodar-ss-vue-toggle-header th:first-child,
tr.sodar-ss-vue-toggle-row td:first-child {
  width: 100%;
}

input#sodar-ss-vue-col-filter {
  max-width: 200px;
}

</style>
