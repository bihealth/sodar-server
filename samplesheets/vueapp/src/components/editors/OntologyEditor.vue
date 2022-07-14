<template>
  <div class="sodar-ss-data-cell-busy text-muted text-center">
    <i class="iconify spin" data-icon="mdi:loading"></i>
  </div>
</template>

<script>
import Vue from 'vue'

export default Vue.extend({
  data () {
    return {
      app: null,
      gridOptions: null,
      value: null,
      editValue: null,
      ogEditValue: null,
      headerInfo: null,
      nodeName: null,
      destroyCalled: false // HACK for issue #869
    }
  },
  methods: {
    /* Implemented ag-grid editor methods ----------------------------------- */
    getValue () {
      return this.value
    },
    isPopup () {
      return false
    },
    isCancelBeforeStart () {
      return false
    },
    isCancelAfterEnd () {
      return true
    },
    /* Helpers -------------------------------------------------------------- */
    selectEmptyValue (value) {
      return value.uuid === '' || !value.uuid
    },
    getKeyCode (event) {
      return (typeof event.which === 'undefined') ? event.keyCode : event.which
    },
    getUpdateData () {
      if (this.ogEditValue) {
        for (let i = 0; i < this.ogEditValue.length; i++) {
          delete this.ogEditValue[i].editing
        }
      }
      return Object.assign(
        this.value, this.headerInfo, { og_value: this.ogEditValue })
    },
    finishEditCallback (editValue) {
      if (editValue) {
        this.value.value = editValue
        this.value.colType = 'ONTOLOGY'
        if (!this.value.newRow) {
          this.app.handleCellEdit(this.getUpdateData(), true)
        }
      }
      this.app.unsavedData = false // Allow navigation
      this.$destroy()
    }
  },
  created () {
    this.app = this.params.app
    this.gridOptions = this.app.getGridOptionsByUuid(this.params.gridUuid)
    this.headerInfo = this.params.colDef.cellEditorParams.headerInfo
    this.value = this.params.value

    // Cancel editing if editingCell is true
    if (this.app.editingCell) {
      this.editAllowed = false
      this.gridOptions.api.stopEditing(true)
    }

    // Get nodeName for modal
    // TODO: Make this a common helper function
    // console.dir(this.params) // DEBUG
    const cols = this.gridOptions.columnApi.getColumns()
    const parent = this.params.column.originalParent
    const isSourceNode = parent.colGroupDef.headerName === ''

    for (let i = 1; i < cols.length - 1; i++) {
      const col = cols[i]
      if ((col.originalParent === parent &&
          ['name', 'process_name'].includes(this.headerInfo.header_type)) ||
          (i === 1 && isSourceNode)) {
        this.nodeName = this.params.node.data[col.colId].value
        break
      }
    }
  },
  mounted () {
    // Store original edit value
    if (this.value && this.value.value && Array.isArray(this.value.value)) {
      this.ogEditValue = []
      for (let i = 0; i < this.value.value.length; i++) {
        this.ogEditValue.push(Object.assign(this.value.value[i]))
      }
    } else if (this.value && this.value.value) {
      this.ogEditValue = [Object.assign(this.value.value)]
    } else {
      this.ogEditValue = null
    }

    this.app.$refs.ontologyEditModal.showModal({
      value: this.value.value,
      nodeName: this.nodeName,
      headerName: this.params.column.colDef.headerName,
      editConfig: this.params.editConfig,
      sodarOntologies: this.params.sodarOntologies
    }, this.finishEditCallback)
  },
  updated () {
  },
  beforeDestroy () {
    if (!this.destroyCalled) {
      this.destroyCalled = true // HACK for issue #869
      // Redraw cells to display value
      // TODO: Why is this necessary? Is there another way to refresh this?
      this.gridOptions.api.redrawRows({ rows: [this.params.node] })
      if (this.editAllowed) this.app.editingCell = false
      this.app.selectEnabled = true
    }
  }
})
</script>

<style scoped>
</style>
