<template>
  <div v-if="value"
       :title="containerTitle"
       :class="containerClasses"
       v-b-tooltip.hover>
    <!-- Value select -->
    <select :ref="'input'"
            v-model="editValue"
            :class="'ag-cell-edit-input ' + getSelectClass()">
      <option v-for="(value, index) in selectOptions"
              :key="index"
              :value="value"
              :selected="editValue.uuid === value.uuid">
        {{ value.name }}
      </option>
    </select>
  </div>
</template>

<script>
import Vue from 'vue'

export default Vue.extend({
  data () {
    return {
      app: null,
      gridOptions: null,
      headerInfo: null,
      renderInfo: null,
      editConfig: null,
      selectOptions: null,
      headerType: null,
      value: null,
      editValue: null,
      ogEditValue: null,
      containerClasses: '',
      containerTitle: '',
      inputStyle: '',
      unitStyle: '',
      nameValues: [],
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
    getSelectClass () {
      if (navigator.userAgent.search('Firefox') > -1) {
        return 'sodar-ss-vue-select-firefox'
      }
    },
    getUpdateData () {
      return Object.assign(
        this.value, this.headerInfo, { og_value: this.ogEditValue })
    }
  },
  created () {
    this.app = this.params.app
    this.app.selectEnabled = false // Disable editing
    this.value = this.params.value
    this.editValue = { uuid: this.value.uuid_ref, name: this.value.value }
    this.ogEditValue = Object.assign(this.editValue)
    this.headerInfo = this.params.headerInfo
    this.renderInfo = this.params.renderInfo
    this.editConfig = this.params.editConfig
    this.selectOptions = this.params.selectOptions

    // Get current grid options for grid/column API access
    this.gridOptions = this.app.getGridOptionsByUuid(this.params.gridUuid)

    // Special setup for the name column
    /*
    if (this.headerInfo.header_type === 'name') {
      this.containerTitle = 'Select existing node'
    }
    */
  },
  mounted () {
    Vue.nextTick(() => {
      if (this.$refs.input) this.$refs.input.focus()
    })
  },
  updated () {
    this.value.value = this.editValue.name
    this.value.uuid_ref = this.editValue.uuid
  },
  beforeDestroy () {
    if (!this.destroyCalled && this.ogEditValue !== this.editValue) {
      this.destroyCalled = true // HACK for issue #869

      if (['name', 'protocol'].includes(this.headerInfo.header_type) &&
          (!this.value.uuid || this.value.newRow)) {
        let createNew = false
        this.value.newInit = false
        if (this.headerInfo.header_type === 'protocol') createNew = true
        this.app.handleNodeUpdate(
          this.value,
          this.params.column,
          this.params.node,
          this.gridOptions,
          this.params.gridUuid,
          createNew
        )
      } else {
        this.app.handleCellEdit(this.getUpdateData(), true)
      }
      this.app.selectEnabled = true
    }
  }
})
</script>

<style scoped>
</style>
