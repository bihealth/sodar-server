<template>
  <div v-if="value && renderInfo"
       :title="containerTitle"
       :class="containerClasses"
       v-b-tooltip.hover>
    <!-- Value select -->
    <span v-if="editorType === 'select'">
      <select :ref="'input'"
              v-model="editValue"
              :class="'ag-cell-edit-input ' + getSelectClass()"
              @keydown="onKeyDown($event)">
        <option value="" :selected="selectEmptyValue(editValue)">-</option>
        <option v-for="(val, index) in editConfig.options"
                :key="index"
                :value="val"
                :selected="editValue === val">
          {{ val }}
        </option>
      </select>
    </span>
    <!-- Value basic input -->
    <span v-else>
      <input :ref="'input'"
             v-model="editValue"
             :class="'ag-cell-edit-input ' + getInputClasses()"
             :style="inputStyle"
             @keydown="onKeyDown($event)"
             :placeholder="getInputPlaceholder('Value')" />
    </span>
    <!-- Unit select (in popup) -->
    <select :ref="'unitText'"
            v-if="editConfig.hasOwnProperty('unit') &&
                  editConfig.unit.length > 0"
            v-model="editUnit"
            id="sodar-ss-vue-edit-select-unit"
            class="ag-cell-edit-input sodar-ss-vue-popup-input"
            :style="unitStyle">
      <option :value="null">-</option>
      <option v-for="(unit, index) in editConfig.unit"
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
const navKeyCodes = [33, 34, 35, 36, 37, 38, 39, 40]

export default Vue.extend({
  data () {
    return {
      app: null,
      gridOptions: null,
      headerInfo: null,
      renderInfo: null,
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
    onKeyDown (event) {
      const keyCode = this.getKeyCode(event)

      // Handle navigation keycodes
      // TODO: Better way to do this? event.stopPropagation() fails (see #690)
      if (navKeyCodes.indexOf(keyCode) !== -1) {
        let caretPos = event.currentTarget.selectionStart

        if (keyCode === 33 || keyCode === 36) { // PgUp/Home
          caretPos = 0
        } else if (keyCode === 34 || keyCode === 35) { // PgDown/End
          caretPos = event.currentTarget.value.length
        } else if (keyCode === 37) { // Left
          if (caretPos >= 1) {
            caretPos = caretPos - 1
          } else {
            caretPos = 0
          }
        } else if (keyCode === 39) { // Right
          caretPos = caretPos + 1
        }

        this.$nextTick(() => {
          event.currentTarget.setSelectionRange(caretPos, caretPos)
        })
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
        return 'sodar-ss-vue-select-firefox'
      }
    },
    getInputClasses () {
      let classes = ''
      if (!this.valid) {
        classes = classes + ' text-danger'
      }
      return classes + ' text-' + this.renderInfo.align
    },
    getInputPlaceholder (text) {
      if (this.isPopup() && this.editUnitEnabled) {
        return text
      }
      return ''
    },
    getValidState () {
      if (this.headerInfo.header_type === 'name') { // Name is a special case
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
    }
  },
  created () {
    this.app = this.params.app
    this.app.selectEnabled = false // Disable editing
    this.value = this.params.value
    this.editValue = this.params.value.value || ''
    if (Array.isArray(this.editValue)) {
      this.isValueArray = true
      this.editValue = this.editValue.join('; ')
    }
    this.ogEditValue = Object.assign(this.value.value)
    this.headerInfo = this.params.headerInfo
    this.renderInfo = this.params.renderInfo
    this.editConfig = this.params.editConfig
    this.sampleColId = this.params.sampleColId

    // Get current grid options for grid/column API access
    this.gridOptions = this.app.getGridOptionsByUuid(this.params.gridUuid)

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
      this.containerClasses = 'sodar-ss-vue-edit-popup text-nowrap'

      let inputWidth = this.renderInfo.width
      if (this.editUnitEnabled) {
        const unitWidth = Math.max(0, ...this.editConfig.unit.map(el => el.length)) * 15 + 30
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
    if (this.headerInfo.header_type === 'name') {
      if (this.value.newRow) this.containerTitle = 'Enter name of new or existing node'
      else this.containerTitle = 'Rename node'
      // If name, get other current values for comparison in validation
      this.setNameData(this.params.colDef.field, this.value)
    }

    // Prevent keyboard navigation in parent when editing
    // See onKeyDown() for manual in-cell editing
    this.params.colDef.suppressKeyboardEvent = function (params) {
      if (params.event.shiftKey) { // Key combinations break event keyCode
        return false
      }
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
    if (this.editUnitEnabled) {
      this.value.unit = this.editUnit
    }
  },
  beforeDestroy () {
    if (!this.destroyCalled) {
      this.destroyCalled = true // HACK for issue #869

      // Convert to list value if applicable
      if (this.editValue.includes(';') && (this.isValueArray ||
          (!['integer', 'double'].includes(this.editConfig.format) &&
          !this.value.unit))) { // TODO: More constraints for list values?
        this.value.value = this.editValue.split(';')
        for (let i = 0; i < this.value.value.length; i++) {
          this.value.value[i] = this.value.value[i].trim()
        }
      }

      // Check if we're in a named process without a protocol
      let namedProcess = false
      if (this.headerInfo.header_type === 'process_name') {
        namedProcess = true
        const groupId = this.params.column.originalParent.groupId
        const cols = this.gridOptions.columnApi.getAllColumns()
        for (let i = 1; i < cols.length - 1; i++) {
          if (cols[i].originalParent.groupId === groupId &&
              cols[i].colDef.cellEditorParams.headerInfo.header_type === 'protocol') {
            namedProcess = false
            break
          }
        }
      }

      if (!this.valid) {
        this.value.value = this.ogEditValue
        this.value.unit = this.ogEditUnit
        this.app.showNotification(this.invalidMsg || 'Invalid value', 'danger', 1000)
      } else if ((this.headerInfo.header_type === 'name' || namedProcess) &&
            (!this.value.uuid || this.value.newRow)) {
        // Set UUID if we are referring to an existing node (only if material)
        if (!namedProcess && this.nameValues.includes(this.value.value)) {
          this.value.uuid = this.nameUuids[this.value.value]
        } else if (!namedProcess) {
          // Clear UUID in case user switched from existing to new while editing
          this.value.uuid = null
        }
        // Set newInit to false as we have data now
        this.value.newInit = false

        // Handle updating/initiating node
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
        // Set unit
        if (this.value.unit === '' || !this.value.value) {
          this.value.unit = null
        } else {
          this.value.unit = this.editUnit
        }
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
      this.params.colDef.suppressKeyboardEvent = false
      this.app.selectEnabled = true
    }
  }
})
</script>

<style scoped>
</style>
