<template>
  <span class="text-nowrap sodar-ss-row-edit-buttons">
    <b-button
        variant="danger"
        class="sodar-list-btn sodar-ss-row-btn mr-1 sodar-ss-row-delete-btn"
        :title="getDeleteTitle()"
        :disabled="!enableDelete()"
        @click="onDelete()"
        v-b-tooltip.hover.d300>
      <i :class="getBtnClass(false)"></i>
    </b-button>
    <b-button
        v-if="isNewRow()"
        variant="success"
        class="sodar-list-btn sodar-ss-row-btn sodar-ss-row-save-btn"
        title="Save row"
        :disabled="!enableSave()"
        @click="onSave()"
        v-b-tooltip.hover.d300>
      <i :class="getBtnClass(true)"></i>
    </b-button>
 </span>
</template>

<script>
import Vue from 'vue'
const nodeIdTypes = ['name', 'process_name', 'protocol']

export default Vue.extend({
  data () {
    return {
      app: null,
      gridUuid: null,
      assayMode: null,
      gridOptions: null,
      rowNode: null,
      sampleColId: null,
      inserting: false,
      deleting: false
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
    getNodeNames (rowNode, cols) {
      let ret = ''
      let i = 1
      while (i < cols.length - 1) {
        const headerInfo = cols[i].colDef.cellEditorParams.headerInfo
        if (nodeIdTypes.includes(headerInfo.header_type)) {
          if (i > 1) ret += ';'
          ret += rowNode.data[cols[i].colId].value
          const nextNodeIdx = this.app.findNextNodeIdx(cols, i, cols.length - 1)
          if (!nextNodeIdx) break
          i = nextNodeIdx
        } else i += 1
      }
      return ret
    },
    onSave () {
      // HACK: Force hiding the tooltip
      // TODO: This does not always work, fix?
      this.$root.$emit('bv::hide::tooltip')
      this.inserting = true

      // Prevent insertion if an identical row exists
      const oldRowNodes = []
      let newRowNodes = null
      const currentRowNode = this.rowNode
      const getNodeNames = this.getNodeNames
      // Get node IDs for existing nodes
      const cols = this.gridOptions.columnApi.getAllColumns()
      this.gridOptions.api.forEachNode(function (r) {
        if (r.id !== currentRowNode.id) {
          oldRowNodes.push(getNodeNames(r, cols))
        } else newRowNodes = getNodeNames(r, cols)
      })
      if (oldRowNodes.includes(newRowNodes)) {
        this.app.showNotification('Identical Row', 'danger', 2000)
        this.inserting = false
        return
      }

      this.app.handleRowSave(
        this.gridOptions,
        this.rowNode,
        this.getNewRowData(),
        this.assayMode,
        this.finishUpdateCallback)
    },
    onDelete () {
      let msg
      let delRowData = null
      if (!this.isNewRow()) {
        msg = 'Delete row? This can not be undone.'
        this.deleting = true

        if (this.assayMode && this.app.sodarContext.irods_status) {
          msg += ' Note that If related sample data exists in iRODS, it ' +
            'may become unreachable.'
        }

        delRowData = {
          study: this.app.currentStudyUuid,
          assay: this.assayMode ? this.gridUuid : null,
          nodes: []
        }

        let currentNodeUuid = null
        const cols = this.gridOptions.columnApi.getAllColumns()
        let startIdx = 1
        if (this.assayMode) {
          startIdx = this.app.sampleIdx
        }

        for (let i = startIdx; i < cols.length - 1; i++) {
          const cell = this.rowNode.data[cols[i].colId]
          if ('uuid' in cell && cell.uuid && cell.uuid !== currentNodeUuid) {
            delRowData.nodes.push({
              uuid: cell.uuid,
              obj_cls: cols[i].colDef.cellEditorParams.headerInfo.obj_cls
            })
            currentNodeUuid = cell.uuid
          }
        }
      } else {
        msg = 'Cancel row insert?'
      }

      if (confirm(msg)) {
        this.app.handleRowDelete(
          this.gridOptions,
          this.gridUuid,
          this.rowNode,
          delRowData,
          this.assayMode,
          this.finishUpdateCallback)
      } else this.deleting = false // Cancel
    },
    finishUpdateCallback () {
      this.inserting = false
      this.deleting = false
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
      // return !this.rowNode.data[cols[1].colId].newInit && !this.app.updatingRow
    },
    getBtnClass (insert) {
      if ((insert && this.inserting) || ((!insert && this.deleting))) {
        return 'fa fa-spin fa-circle-o-notch'
      }
      if (insert) return 'fa fa-check'
      return 'fa fa-times'
    },
    enableDelete () {
      if (this.app.updatingRow ||
          (this.app.unsavedRow && !this.isNewRow()) ||
          this.gridOptions.api.getDisplayedRowCount() < 2) {
        return false
      }
      let sampleOk = true
      if (!this.assayMode && !this.isNewRow()) {
        const sampleUuid = this.rowNode.data[this.sampleColId].uuid
        if (this.app.editContext.samples[sampleUuid].assays.length > 0) {
          sampleOk = false
        }
      }
      return this.isNewRow() || sampleOk
    },
    getDeleteTitle () {
      if (this.isNewRow()) return 'Cancel row insertion'
      return 'Delete row'
    },
    getCellData (col) {
      // If referencing an existing node, only provide the UUID
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
        if (!sourceNode.cells[0].uuid) {
          sourceNode.headers = cols[1].originalParent.colGroupDef.cellRendererParams.headers
        }
        let i = 1
        // Only add more source columns if we actually have a split source
        if (this.app.sourceColSpan > 1) {
          i = 2
          const sourceGroupId = cols[2].originalParent.groupId
          // If the node is new, get remaining fields
          if (!sourceNode.cells[0].uuid) {
            while (i < cols.length - 1) {
              if (cols[i].originalParent.groupId !== sourceGroupId) {
                startIdx = i
                break
              }
              sourceNode.cells.push(this.getCellData(cols[i]))
              i += 1
            }
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

        if (i === cols.length - 1 ||
            groupId !== cols[i + 1].originalParent.groupId) {
          groupId = cols[i + 1].originalParent.groupId
          fieldIdx = 0
          const nodeData = { cells: Object.assign(nodeCells) }
          if (!nodeCells[0].uuid) {
            nodeData.headers =
              cols[nodeStartIdx].originalParent.colGroupDef.cellRendererParams.headers
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
    // this.rowNode = this.gridOptions.api.getRowNode(this.params.node.id)
    this.rowNode = this.params.node
    this.sampleColId = this.params.sampleColId
    this.sampleIdx = this.params.sampleIdx
  }
})
</script>

<style scoped>
</style>
