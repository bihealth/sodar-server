<template>
  <span class="text-nowrap">
    <b-button
        variant="danger"
        class="sodar-list-btn sodar-ss-vue-row-btn mr-1"
        :title="getDeleteTitle()"
        :disabled="!enableDelete()"
        @click="onDelete()"
        v-b-tooltip.hover.d300>
      <i class="fa fa-times"></i>
    </b-button>
    <b-button
        v-if="isNewRow()"
        variant="success"
        class="sodar-list-btn sodar-ss-vue-row-btn"
        title="Save row"
        :disabled="!enableSave()"
        @click="onSave()"
        v-b-tooltip.hover.d300>
      <i :class="getSaveClass()"></i>
    </b-button>
 </span>
</template>

<script>
import Vue from 'vue'

export default Vue.extend(
  {
    data () {
      return {
        app: null,
        gridUuid: null,
        assayMode: null,
        gridOptions: null,
        rowNode: null,
        sampleColId: null
      }
    },
    methods: {
      /*
      // Saving this until we have row ordering and will add new rows here
      onInsert () {
        this.$root.$emit('bv::hide::tooltip') // HACK: Force hiding
        this.app.handleRowInsert(this.gridOptions, this.assayMode)
      },
      */
      onSave () {
        // HACK: Force hiding the tooltip
        // TODO: This does not always work, fix?
        this.$root.$emit('bv::hide::tooltip')
        this.app.handleRowSave(
          this.gridOptions, this.rowNode, this.getNewRowData(), this.assayMode)
      },
      onDelete () {
        if (confirm('Cancel row insert?')) {
          this.app.handleRowDelete(this.gridOptions, this.rowNode, this.assayMode)
        }
      },
      isNewRow () {
        return this.app.unsavedRow &&
          this.app.unsavedRow.gridUuid === this.gridUuid &&
          this.app.unsavedRow.id === this.rowNode.id
      },
      enableSave () {
        const cols = this.gridOptions.columnApi.getAllColumns()

        // NOTE: This assumes we have to fill all nodes in a column
        for (let i = 1; i < cols.length - 1; i++) {
          if (!this.rowNode.data[cols[i].colId] ||
              this.rowNode.data[cols[i].colId].newInit) {
            // console.log('Fail at ' + cols[i].colId + '; newInit=' + this.rowNode.data[cols[i].colId].newInit) // DEBUG
            return false
          }
        }
        return true

        // NOTE: This allows saving incomplete rows (not yet implemented)
        // return !this.rowNode.data[cols[1].colId].newInit && !this.app.savingRow
      },
      getSaveClass () {
        if (this.app.savingRow) {
          return 'fa fa-spin fa-circle-o-notch'
        }
        return 'fa fa-check'
      },
      enableDelete () {
        return this.isNewRow() && !this.app.savingRow
      },
      getDeleteTitle () {
        if (this.isNewRow()) {
          return 'Cancel row insertion'
        }
        return 'Delete row'
      },
      getCellData (col) {
        // If referencing an existing node, only provide the UUID
        // console.dir(col) // DEBUG
        let headerInfo = null
        let objCls = null

        // TODO: Can this still go missing?
        if (col.colDef.cellEditorParams &&
            'headerInfo' in col.colDef.cellEditorParams) {
          headerInfo = col.colDef.cellEditorParams.headerInfo
          objCls = headerInfo.obj_cls
        }

        if (this.rowNode.data[col.colId].uuid) {
          const cellData = {
            uuid: this.rowNode.data[col.colId].uuid,
            obj_cls: objCls
          }
          // If name or protocol def, include value for comparison
          if (headerInfo &&
              ['name', 'protocol', 'process_name'].includes(
                headerInfo.header_type)) {
            cellData.value = this.rowNode.data[col.colId].value
          }
          return cellData
        } else if (this.assayMode &&
            col.colId === this.sampleColId &&
            this.rowNode.data[col.colId].uuid_ref) {
          // Sample in an assay is a special case
          return {
            uuid: this.rowNode.data[col.colId].uuid_ref,
            obj_cls: objCls,
            value: this.rowNode.data[col.colId].value
          }
        }
        // Else return full data
        // TODO: Simplify once ONTOLOGY and EXTERNAL_LINKS are there
        // TODO: Refactor to only include specific fields instead of deleting
        // TODO: (Once there's a test for the ajax view)
        const data = Object.assign(this.rowNode.data[col.colId], headerInfo)
        delete data.colType
        delete data.newRow
        delete data.newInit
        delete data.editable
        if ('header_type' in data &&
            !['name', 'protocol', 'process_name'].includes(data.header_type)) {
          delete data.uuid
        }
        return data
      },
      getNewRowData () {
        // TODO: Simplify (there must be a better way to iterate through this..)
        const cols = this.gridOptions.columnApi.getAllColumns()
        const newRowData = {
          study: this.app.currentStudyUuid,
          assay: this.assayMode ? this.gridUuid : null,
          nodes: []
        }
        let startIdx
        let inSampleNode = false

        // Construct source node manually because we split the column groups
        if (!this.assayMode) {
          const sourceNode = { cells: [this.getCellData(cols[1])] }
          const sourceGroupId = cols[2].originalParent.groupId
          let i = 2

          // If the node is new, get remaining fields
          if (!sourceNode.cells[0].uuid) {
            sourceNode.headers = cols[1].originalParent.colGroupDef.cellRendererParams.headers

            while (i < cols.length - 1) {
              if (cols[i].originalParent.groupId !== sourceGroupId) {
                startIdx = i
                break
              }
              sourceNode.cells.push(this.getCellData(cols[i]))
              i += 1
            }
          }
          newRowData.nodes.push(sourceNode)

          if (!startIdx) {
            startIdx = this.app.findNextNodeIdx(cols, i, cols.length - 1)
          }
        } else { // Set assay start Idx
          startIdx = this.sampleIdx
          inSampleNode = true
        }

        // Get data from remaining columns
        let groupId = cols[startIdx].originalParent.groupId
        let fieldIdx = 0 // Field index within node
        let nodeCells = []
        let nodeClass
        let nodeStartIdx = startIdx

        for (let i = startIdx; i < cols.length - 1; i++) {
          if (fieldIdx === 0) {
            nodeStartIdx = i
            nodeClass = cols[i].colDef.cellEditorParams.headerInfo.obj_cls
          }

          // Add cells for new nodes, only the first node for existing ones
          if (nodeClass === 'Process' ||
              fieldIdx === 0 ||
              (!this.rowNode.data[cols[i].colId].uuid &&
              !(this.assayMode && inSampleNode))) {
            nodeCells.push(this.getCellData(cols[i]))
          }

          if (i === cols.length - 1 || groupId !== cols[i + 1].originalParent.groupId) {
            groupId = cols[i + 1].originalParent.groupId
            fieldIdx = 0
            const nodeData = { cells: Object.assign(nodeCells) }
            if (!nodeCells[0].uuid) {
              nodeData.headers = cols[nodeStartIdx].originalParent.colGroupDef.cellRendererParams.headers
            }
            newRowData.nodes.push(nodeData)
            nodeCells = []
            inSampleNode = cols[i + 1].colId === this.sampleColId
          } else fieldIdx += 1
        }
        return newRowData
      },
      refresh (params) {
        this.params = params
        return true
      }
    },
    beforeMount () {
      // console.dir(this.params) // DEBUG
      this.app = this.params.app
      this.gridUuid = this.params.gridUuid
      this.assayMode = this.params.assayMode
      this.gridOptions = this.app.getGridOptionsByUuid(this.gridUuid)
      this.rowNode = this.gridOptions.api.getRowNode(this.params.node.id)
      this.sampleColId = this.params.sampleColId
      this.sampleIdx = this.params.sampleIdx
    }
  }
)
</script>

<style scoped>
</style>
