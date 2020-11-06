<template>
  <b-modal id="sodar-ss-vue-col-toggle-modal" ref="columnToggleModal"
           no-fade hide-footer
           size="md"
           @hidden="onModalHide">

    <template slot="modal-header">
      <h5 class="modal-title text-nowrap mr-5">{{ title }}</h5>
      <b-input-group class="sodar-header-input-group">
        <b-input-group-prepend v-if="app.sodarContext.perms.edit_sheet">
          <b-button
              variant="secondary"
              class="sodar-list-btn px-2"
              title="Save as default display configuration for all users"
              @click="hideModal(true)"
              v-b-tooltip.hover.bottom>
            <i class="fa fa-save"></i>
          </b-button>
        </b-input-group-prepend>
        <b-input
            id="sodar-ss-vue-col-filter"
            size="sm"
            placeholder="Filter"
            @keyup="onFilterChange">
        </b-input>
      </b-input-group>
      <button
          type="button"
          class="close"
          @click="hideModal(false)">
        ×
      </button>
    </template>

    <div v-if="columnList"
         id="sodar-ss-vue-col-toggle-modal-content">
      <table v-for="(topHeader, topIdx) in columnList"
             :key="topIdx"
             class="table sodar-card-table sodar-ss-vue-toggle-table">
        <tr class="sodar-ss-vue-toggle-header">
          <th :class="getTopHeaderClasses(topHeader)">
            {{ topHeader.headerName }}
          </th>
          <th :class="getTopHeaderClasses(topHeader)">
            <b-checkbox indeterminate plain
                v-if="topHeader.children.length > 0 && !filterActive"
                :checked="false"
                @change="onGroupChange($event, topHeader, topIdx)">
            </b-checkbox>
          </th>
        </tr>
        <tr v-for="(header, headerIdx) in topHeader.children"
            v-show="header.visibleInList"
            :key="headerIdx"
            class="sodar-ss-vue-toggle-row">
          <td>
            {{ header.headerName }}
            <span v-if="app.editMode && header.cellRendererParams.fieldEditable"
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
                @change="onColumnChange($event, header, topIdx, headerIdx)">
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
      filterActive: false,
      columnsChanged: false,
      setDefault: false
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

    onColumnChange (event, header, topIdx, headerIdx) {
      this.columnApi.setColumnVisible(header.field, event)
      // Update user display config
      headerIdx += 1 // The first field is always skipped
      this.displayConfig.nodes[topIdx].fields[headerIdx].visible = event
      this.columnsChanged = true
    },

    onGroupChange (event, topHeader, topIdx) {
      for (let i = 0; i < topHeader.children.length; i++) {
        this.columnApi.setColumnVisible(topHeader.children[i].field, event)
      }
      // Update user display config
      const fieldLength = this.displayConfig.nodes[topIdx].fields.length
      for (let i = 1; i < fieldLength; i++) {
        this.displayConfig.nodes[topIdx].fields[i].visible = event
      }
      this.columnsChanged = true
    },

    onModalHide () {
      // Update user display config in app
      if (!this.assayMode) {
        this.app.studyDisplayConfig = this.displayConfig
      } else {
        this.app.studyDisplayConfig.assays[this.uuid] = this.displayConfig
      }

      // Save changes to user display config on the server
      if (this.columnsChanged || this.setDefault) {
        fetch('/samplesheets/ajax/display/update/' + this.app.currentStudyUuid, {
          method: 'POST',
          body: JSON.stringify({
            study_config: this.app.studyDisplayConfig,
            set_default: this.setDefault
          }),
          credentials: 'same-origin',
          headers: {
            Accept: 'application/json',
            'Content-Type': 'application/json',
            'X-CSRFToken': this.app.sodarContext.csrf_token
          }
        }).then(data => data.json())
          .then(
            data => {
              if (data.detail === 'ok') {
                this.app.showNotification('Display Saved', 'success', 1000)
              }
            }
          ).catch(function (error) {
            console.log('Error saving display config: ' + error.message)
          })
      }
    },

    showModal (uuid, assayMode) {
      // Reset data
      this.columnDefs = null
      this.columnList = []
      this.columnValues = null
      this.filterActive = false
      this.columnsChanged = false
      this.setDefault = false

      // Get data
      this.uuid = uuid
      this.assayMode = assayMode
      this.gridOptions = this.app.getGridOptionsByUuid(this.uuid)
      this.columnApi = this.gridOptions.columnApi
      this.columnDefs = this.gridOptions.columnDefs
      const rowData = this.gridOptions.rowData

      // Top column group length for iteration
      const lastColName = this.columnDefs[this.columnDefs.length - 1].headerName.toLowerCase()
      const rightColumn = ['irods', 'links', 'edit'].includes(lastColName)
      let topColLen = this.columnDefs.length
      if (rightColumn) topColLen -= 1

      if (!assayMode) {
        this.title = 'Toggle Study Columns'
        this.displayConfig = Object.assign({}, this.app.studyDisplayConfig)
      } else {
        this.title = 'Toggle Assay Columns'
        this.displayConfig = Object.assign({}, this.app.studyDisplayConfig.assays[uuid])
      }

      // Store current column data state
      this.columnValues = {}
      for (let i = 1; i < topColLen; i++) {
        for (let j = 0; j < this.columnDefs[i].children.length; j++) {
          this.columnValues[this.columnDefs[i].children[j].field] = false
        }
      }
      for (const key in this.columnValues) {
        for (let i = 0; i < rowData.length - 1; i++) {
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

      // Iterate through the rest of the columns
      for (let i = firstTopIdx; i < topColLen; i++) {
        this.columnList.push(getListGroup(this.columnDefs[i], 1))
      }

      // Show element
      this.$refs.columnToggleModal.show()
    },

    hideModal (setDefault) {
      if (setDefault) this.setDefault = true
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