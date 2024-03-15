<template>
  <div v-if="value && renderInfo"
       :title="containerTitle"
       :class="'sodar-ss-data-cell-editor ' + containerClasses"
       v-b-tooltip.hover>
    <!-- Value select -->
    <span v-if="editorType === 'select'">
      <select
          :ref="'input'"
          v-model="editValue"
          :class="'ag-cell-edit-input ' + getSelectClass()">
        <option
            value=""
            :selected="selectEmptyValue(editValue)">
          -
        </option>
        <option
            v-for="(val, index) in editConfig.options"
            :key="index"
            :value="val"
            :selected="editValue === val">
          {{ val }}
        </option>
      </select>
    </span>
    <!-- Value basic input -->
    <span v-else>
      <input
          :ref="'input'"
          v-model.trim="editValue"
          :class="'ag-cell-edit-input ' + getInputClasses()"
          :style="inputStyle"
          :placeholder="getInputPlaceholder('Value')"
          @copy="onCopy"/>
    </span>
    <!-- Unit select (in popup) -->
    <select
        ref="unitText"
        v-if="'unit' in editConfig && editConfig.unit.length > 0"
        v-model="editUnit"
        id="sodar-ss-data-cell-unit"
        class="ag-cell-edit-input sodar-ss-popup-input"
        :style="unitStyle">
      <option :value="null">-</option>
      <option
          v-for="(unit, index) in editConfig.unit"
          :key="index"
          :value="unit">
        {{ unit }}
      </option>
    </select>
  </div>
</template>

<script>
import Vue from 'vue'

const dateRegex = /^\d{4}-(0[1-9]|1[012])-(0[1-9]|[12][0-9]|3[01])$/
const exLinkRegex = /^([\w-]+:[\w\-_]+)(;\s*[\w-]+:[\w-_]+)*$/
const navKeyCodes = [33, 34, 35, 36, 37, 38, 39, 40]

export default Vue.extend({
  data () {
    return {
      app: null,
      gridOptions: null,
      headerInfo: null,
      renderInfo: null,
      editAllowed: true,
      editConfig: null,
      editorType: 'text',
      regex: null,
      valid: true,
      invalidMsg: null,
      objCls: null,
      headerType: null,
      value: null,
      isValueArray: false,
      editValue: '',
      ogEditValue: '',
      editUnitEnabled: false,
      editUnit: '',
      ogEditUnit: '',
      containerClasses: '',
      containerTitle: '',
      inputStyle: '',
      unitStyle: '',
      nameValues: [],
      nameUuids: {},
      sampleColId: null,
      nameColumn: false,
      destroyCalled: false // HACK for issue #869
    }
  },
  methods: {
    /* Implemented ag-grid editor methods ----------------------------------- */
    getValue () {
      return this.value
    },
    isPopup () {
      // Show popup editor if unit can be changed
      return this.editUnitEnabled
    },
    getPopupPosition () {
      return 'over'
    },
    isCancelBeforeStart () {
      return 'editable' in this.params.value && !this.params.value.editable
    },
    isCancelAfterEnd () {
      return true
    },
    /* Event handling ------------------------------------------------------- */
    onCopy (event) {
      if (event.currentTarget.selectionEnd > event.currentTarget.selectionStart) {
        this.app.showNotification('Copied', 'success', 1000)
      }
    },
    /* Helpers -------------------------------------------------------------- */
    selectEmptyValue (value) {
      return value === '' || !value
    },
    getKeyCode (event) {
      return (typeof event.which === 'undefined') ? event.keyCode : event.which
    },
    getSelectClass () {
      if (navigator.userAgent.search('Firefox') > -1) {
        return 'sodar-ss-select-firefox'
      }
      return ''
    },
    getInputClasses () {
      let classes = ''
      if (!this.valid) classes = classes + ' text-danger'
      return classes + ' text-' + this.renderInfo.align
    },
    getInputPlaceholder (text) {
      if (this.isPopup() && this.editUnitEnabled) return text
      return ''
    },
    getValidState () {
      if (this.nameColumn) { // Name is a special case
        // TODO: Cleanup/simplify
        // NOTE: Empty value is allowed for DATA materials
        if ((this.editValue.length === 0 &&
            'item_type' in this.headerInfo &&
            this.headerInfo.item_type !== 'DATA') ||
            (this.editValue.length > 0 &&
            !this.value.newRow &&
            this.editValue !== this.ogEditValue &&
            this.nameValues.includes(this.editValue))) {
          return false
        }
        // Prevent pooling of samples
        if (this.params.colDef.field === this.sampleColId &&
            this.editValue !== this.ogEditValue &&
            this.nameValues.includes(this.editValue)) {
          return false
        }
      } else if (this.editValue !== '') {
        // Test range
        if (['integer', 'double'].includes(this.editConfig.format) &&
            'range' in this.editConfig &&
            this.editConfig.range.length === 2) {
          const range = this.editConfig.range
          const valNum = parseFloat(this.editValue)
          if (valNum < parseFloat(range[0]) ||
              valNum > parseFloat(range[1])) {
            this.invalidMsg = 'Not in Range (' +
              parseInt(range[0]) + '-' + parseInt(range[1]) + ')'
            return false
          }
        } else if (this.editConfig.format === 'date') {
          if (!dateRegex.test(this.editValue)) {
            return false
          } else {
            // Actually validate the date
            const dateSplit = this.editValue.split('-')
            const y = dateSplit[0]
            const m = dateSplit[1]
            const d = dateSplit[2]
            if (['04', '06', '09', '11'].includes(m) && d > 30) return false
            if ((m === 2 && d > 29) || (m === 2 && d > 28 && y % 4 !== 0)) return false
          }
        } else if (this.editConfig.format === 'external_links') {
          if (!exLinkRegex.test(this.editValue)) return false
        }
      }
      // Test Regex
      return !(this.editValue !== '' &&
          this.regex &&
          !this.regex.test(this.editValue)
      )
    },
    getUpdateData () {
      return Object.assign(
        this.value, this.headerInfo, { og_value: this.ogEditValue })
    },
    setNameData (field, value) {
      // Set node name UUIDs and values for comparison
      // TODO: Optimize by only searching in the relevant assay/study table
      const gridUuids = this.app.getStudyGridUuids()
      const nameUuids = {}
      const nameValues = []

      for (let i = 0; i < gridUuids.length; i++) {
        const gridOptions = this.app.getGridOptionsByUuid(gridUuids[i])
        const gridApi = gridOptions.api

        if (!gridOptions.columnApi.getColumn(this.params.colDef.field)) {
          continue // Skip this grid if the column is not present
        }

        gridApi.forEachNode(function (rowNode) {
          if (field in rowNode.data) {
            const compValue = rowNode.data[field]
            if (compValue.uuid !== value.uuid &&
                !nameValues.includes(compValue.value)) {
              nameValues.push(compValue.value)
              nameUuids[compValue.value] = compValue.uuid
            }
          }
        })
      }
      this.nameUuids = nameUuids
      this.nameValues = nameValues
    },
    finalizeDestroy () {
      if (this.editAllowed) this.app.editingCell = false
      this.params.colDef.suppressKeyboardEvent = false
      this.app.selectEnabled = true
    }
  },
  created () {
    this.app = this.params.app
    this.gridOptions = this.app.getGridOptionsByUuid(this.params.gridUuid)
    // Cancel editing if editingCell is true
    if (this.app.editingCell) {
      this.editAllowed = false
      this.gridOptions.api.stopEditing(true)
    }

    this.app.editingCell = true // Disallow editing multiple cells
    this.app.selectEnabled = false // Disable cell selection
    this.value = this.params.value
    this.editValue = this.params.value.value || ''
    if (Array.isArray(this.editValue)) {
      this.isValueArray = true
      this.editValue = this.editValue.join('; ')
    }
    if (this.value.value) {
      this.ogEditValue = Object.assign(this.value.value)
    } else {
      this.ogEditValue = null
    }
    this.headerInfo = this.params.headerInfo
    this.renderInfo = this.params.renderInfo
    this.editConfig = this.params.editConfig
    this.sampleColId = this.params.sampleColId
    if (['name', 'process_name'].includes(this.headerInfo.header_type)) {
      this.nameColumn = true
    }
    // console.log('Edit colId/field: ' + this.params.colDef.field) // DEBUG

    // Set up unit value
    // TODO: Support ontology references for units
    if ('unit' in this.editConfig &&
        this.editConfig.unit.length > 0) {
      if ('unit' in this.value &&
          this.value.unit) {
        this.editUnit = this.value.unit
        this.ogEditUnit = this.value.unit
      } else if ('unit_default' in this.editConfig &&
          this.editConfig.unit_default.length > 0) {
        this.editUnit = this.editConfig.unit_default
      }
      this.editUnitEnabled = true
    }

    // Get initial valid state on existing value
    this.valid = this.getValidState()

    // Set classes and styling for popup
    if (this.isPopup()) {
      this.containerClasses = 'sodar-ss-data-cell-popup text-nowrap'

      let inputWidth = this.renderInfo.width
      if (this.editUnitEnabled) {
        const unitWidth = Math.max(
          0, ...this.editConfig.unit.map(el => el.length)) * 15 + 30
        inputWidth = Math.max(inputWidth - unitWidth, 120)
        this.unitStyle = 'width: ' + unitWidth.toString() + 'px !important;'
      }
      this.inputStyle = 'width: ' + inputWidth.toString() + 'px;'
    }

    // Set editor type
    if (this.editConfig.format === 'select' &&
        'options' in this.editConfig && // Options
        this.editConfig.options.length > 0) {
      this.editorType = 'select'
    } else { // Basic text/integer/etc input
      this.editorType = 'basic'
    }

    // Set regex
    if (this.editConfig.format !== 'select' &&
        'regex' in this.editConfig &&
        this.editConfig.regex.length > 0) {
      this.regex = new RegExp(this.editConfig.regex)
    } else if (this.headerInfo.header_type === 'name' &&
        this.headerInfo.item_type === 'DATA') { // Data name is a special case
      this.regex = /^[\w\-.]+$/
    } else if (this.headerInfo.header_type === 'name') { // Other names
      this.regex = /^([A-Za-z0-9-_/]*)$/
    } else { // Default regex for certain fields
      if (this.editConfig.format === 'integer') {
        this.regex = /^(([1-9][0-9]*)|([0]?))$/ // TODO: TBD: Allow negative?
      } else if (this.editConfig.format === 'double') {
        this.regex = /^-?[0-9]+\.[0-9]+?$/
      }
    }

    // Special setup for the name column
    if (this.nameColumn) {
      if (this.value.newRow) this.containerTitle = 'Enter name of new or existing node'
      else this.containerTitle = 'Rename node'
      // If name, get other current values for comparison in validation
      this.setNameData(this.params.colDef.field, this.value)
    }

    // Prevent keyboard navigation in parent when editing
    this.params.colDef.suppressKeyboardEvent = function (params) {
      // Key combinations break event keyCode
      if (params.event.shiftKey) return false
      return navKeyCodes.indexOf(params.event.keyCode) !== -1
    }
  },
  mounted () {
    Vue.nextTick(() => {
      if (this.$refs.input) this.$refs.input.focus()
    })
  },
  updated () {
    this.valid = this.getValidState()
    this.value.value = this.editValue
    if (this.editUnitEnabled) this.value.unit = this.editUnit
  },
  beforeDestroy () {
    if (!this.destroyCalled) {
      this.destroyCalled = true // HACK for issue #869
      // Convert to list value if applicable
      if (this.editValue.includes(';') &&
        this.headerInfo.header_type !== 'comments' && (
        this.isValueArray || (
          !['integer', 'double'].includes(this.editConfig.format) &&
          !this.value.unit))) {
        this.value.value = this.editValue.split(';')
        for (let i = 0; i < this.value.value.length; i++) {
          this.value.value[i] = this.value.value[i].trim()
        }
      }

      // Reject invalid value
      if (!this.valid) {
        this.value.value = this.ogEditValue
        this.value.unit = this.ogEditUnit
        this.app.showNotification(this.invalidMsg || 'Invalid value', 'danger', 1000)
        this.finalizeDestroy()
        return
      }

      // Confirm renaming node into an existing node and overwriting values
      if ((this.nameColumn) &&
          this.value.newRow &&
          this.ogEditValue &&
          this.nameValues.includes(this.editValue)) {
        const proceedVal = confirm(
          'A node named "' + this.editValue + '" already exists in this ' +
          'column. Renaming will replace all values in the material/process ' +
          'fields. Proceed?')
        if (!proceedVal) {
          this.value.value = this.ogEditValue
          this.finalizeDestroy()
          this.app.showNotification(this.invalidMsg || 'Cancel rename', 'info', 1000)
          return
        }
      }

      // Proceed with setting values and saving
      if (this.nameColumn && (!this.value.uuid || this.value.newRow)) {
        // Set UUID if we are referring to an existing node (only if material)
        if (this.nameValues.includes(this.value.value)) {
          this.value.uuid = this.nameUuids[this.value.value]
        } else {
          // Clear UUID in case user switched from existing to new while editing
          this.value.uuid = null
        }
        // Set newInit to false as we have data now
        this.value.newInit = false

        // Set unit
        if (this.value.unit === '' || !this.value.value) this.value.unit = null
        else this.value.unit = this.editUnit

        // Handle updating/initiating node
        // TODO: Ensure this works also if setting process name value to empty
        this.app.handleNodeUpdate(
          this.value,
          this.params.column,
          this.params.node,
          this.gridOptions,
          this.params.gridUuid,
          !(this.value.value && this.nameValues.includes(this.value.value)) // createNew
        )
      } else if (JSON.stringify(this.value.value) !== JSON.stringify(this.ogEditValue) ||
          (this.editUnitEnabled &&
          this.value.value &&
          this.ogEditUnit !== this.editUnit)) {
        // Update cell (only if we already have the UUID!)
        if (this.value.uuid) {
          this.app.handleCellEdit(this.getUpdateData(), true)
          // If a sample has been renamed, update sample list for assay
          if (this.headerInfo.header_type === 'name' &&
              this.params.colDef.field === this.sampleColId) {
            this.app.editContext.samples[this.value.uuid].name = this.editValue
          }
        }
      }
      this.finalizeDestroy()
    }
  }
})
</script>

<style scoped>
</style>
