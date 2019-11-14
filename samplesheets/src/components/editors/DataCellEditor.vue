<template>
  <div v-if="value"
       :class="containerClasses">
    <!-- Value select -->
    <span v-if="editorType === 'select'">
      <select :ref="'input'"
              v-model="editValue"
              class="ag-cell-edit-input"
              @keydown="onKeyDown($event)">
        <option value="" :selected="selectEmptyValue(editValue)">-</option>
        <option v-for="(val, index) in editConfig['options']"
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
             :class="'ag-cell-edit-input ' + inputClasses"
             :style="inputStyle"
             @keydown="onKeyDown($event)"
             :placeholder="getInputPlaceholder('Value')" />
    </span>
    <!-- Unit select (in popup) -->
    <select :ref="'unitText'"
            v-if="editConfig.hasOwnProperty('unit') &&
                  editConfig['unit'].length > 1"
            v-model="editUnit"
            class="ag-cell-edit-input sodar-ss-vue-popup-input"
            :style="unitStyle">
      <option value="" :selected="selectEmptyValue(editUnit)">-</option>
      <option v-for="(unit, index) in editConfig['unit']"
              :key="index"
              :value="unit"
              :selected="editUnit === unit">
        {{ unit }}
      </option>
    </select>
  </div>
</template>

<script>
import Vue from 'vue'

const navKeyCodes = [33, 34, 35, 36, 37, 38, 39, 40]

export default Vue.extend({
  data () {
    return {
      app: null,
      headerInfo: null,
      editConfig: null,
      editorType: 'text',
      regex: null,
      valid: true,
      invalidMsg: null,
      objCls: null,
      headerType: null,
      value: null,
      editValue: '',
      ogEditValue: '',
      editUnitEnabled: false,
      editUnit: '',
      ogEditUnit: '',
      containerClasses: '',
      inputClasses: '',
      inputStyle: '',
      unitStyle: ''
    }
  },
  methods: {
    /* Implemented ag-grid editor methods ----------------------------------- */
    getValue () {
      return this.value
    },
    isPopup () {
      // Show popup editor if unit can be changed
      if (this.editUnitEnabled) {
        return true
      }
      return false
    },
    isCancelBeforeStart () {
      return false
    },
    isCancelAfterEnd () {
      return true
    },
    /* Event handling ------------------------------------------------------- */
    onKeyDown (event) {
      let keyCode = this.getKeyCode(event)

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
    setInputClasses () {
      let classes = ''
      // Alignment does not get inherited in case of popup
      if (this.isPopup()) {
        classes = classes + 'sodar-ss-vue-popup-input text-' + this.renderInfo['align']
      }
      if (!this.valid) {
        classes = classes + ' text-danger'
      }
      this.inputClasses = classes
    },
    getInputPlaceholder (text) {
      if (this.isPopup() && this.editUnitEnabled) {
        return text
      }
      return ''
    },
    getValidState () {
      if (this.editValue !== '') {
        // Test Regex
        if (this.regex && !this.regex.test(this.editValue)) {
          return false
        }
        // Test range
        if (['integer', 'double'].includes(this.editConfig['format']) &&
            this.editConfig.hasOwnProperty('range') &&
            this.editConfig['range'].length === 2) {
          let range = this.editConfig['range']
          let valNum = parseFloat(this.editValue)
          if (valNum < parseFloat(range[0]) ||
              valNum > parseFloat(range[1])) {
            this.invalidMsg = 'Not in Range (' +
              parseInt(range[0]) + '-' + parseInt(range[1]) + ')'
            return false
          }
        }
      }
      return true // Empty value or no failed tests
    }
  },
  created () {
    this.app = this.params.app
    this.app.selectEnabled = false // Disable editing
    this.value = this.params.value
    this.editValue = this.params.value['value']
    this.ogEditValue = this.editValue
    this.headerInfo = this.params.headerInfo
    this.renderInfo = this.params.renderInfo
    this.editConfig = this.params.editConfig

    // Set up unit value
    // TODO: Support ontology references for units
    if (this.editConfig.hasOwnProperty('unit') &&
        this.editConfig['unit'].length > 0 &&
        this.value.hasOwnProperty('unit')) {
      if (this.value['unit']) {
        this.editUnit = this.value['unit']
        this.ogEditUnit = this.value['unit']
      }
      this.editUnitEnabled = true
    }

    // Get initial valid state on existing value
    this.valid = this.getValidState()

    // Set classes and styling for popup
    if (this.isPopup()) {
      this.containerClasses = 'sodar-ss-vue-edit-popup text-nowrap'
      this.setInputClasses()

      let inputWidth = this.renderInfo['width']
      if (this.editUnitEnabled) {
        let unitWidth = Math.max(0, ...this.editConfig['unit'].map(el => el.length)) * 15 + 20
        inputWidth = Math.max(inputWidth - unitWidth, 120)
        this.unitStyle = 'width: ' + unitWidth.toString() + 'px !important;'
      }
      this.inputStyle = 'width: ' + inputWidth.toString() + 'px;'
    }

    // Set editor type
    if (this.editConfig['format'] === 'select' &&
        this.editConfig.hasOwnProperty('options') && // Options
        this.editConfig['options'].length > 0) {
      this.editorType = 'select'
    } else { // Basic text/integer/etc input
      this.editorType = 'basic'
    }

    // Set regex
    if (this.editConfig['format'] !== 'select' &&
        this.editConfig.hasOwnProperty('regex') &&
        this.editConfig['regex'].length > 0) {
      this.regex = new RegExp(this.editConfig['regex'])
    } else { // Default regex for certain fields
      if (this.editConfig['format'] === 'integer') {
        this.regex = /^(([1-9][0-9]*)|([0]?))$/ // TODO: TBD: Allow negative?
      }
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
      if (this.$refs.input) {
        this.$refs.input.focus()
      }
    })
  },
  updated () {
    this.valid = this.getValidState()
    this.setInputClasses()
    this.value['value'] = this.editValue
    if (this.editUnitEnabled && this.value.hasOwnProperty('unit')) {
      this.value['unit'] = this.editUnit
    }
  },
  beforeDestroy () {
    if (!this.valid) {
      this.value['value'] = this.ogEditValue
      this.value['unit'] = this.ogEditUnit
      this.app.showNotification(this.invalidMsg || 'Invalid value', 'danger', 1000)
    } else if (this.ogEditValue !== this.editValue ||
          (this.editUnitEnabled && this.ogEditUnit !== this.editUnit)) {
      // HACK: Force empty unit to null
      if (this.value['unit'] === '') {
        this.value['unit'] = null
      }
      // TODO: Is copying necessary?
      this.app.handleCellEdit(
        JSON.parse(JSON.stringify(this.value)), // Copying just in case..
        this.ogEditValue,
        this.headerInfo)
    }
    this.params.colDef.suppressKeyboardEvent = false
    this.app.selectEnabled = true
  }
})
</script>

<style scoped>
.sodar-ss-vue-edit-popup {
  border: 1px solid #6c757d;
  background: #ffffff;
  padding: 10px;
  // display: inline-block;
}

input.ag-cell-edit-input {
  -moz-appearance: none;
  -webkit-appearance: none;
  appearance: none;

  border: 0;
  height: 38px !important;
  background-color: #ffffd8;
  padding-left: 12px;
  padding-right: 15px;
  padding-top: 0;
  padding-bottom: 2px;
  text-align: inherit;
}

select.ag-cell-edit-input {
  -moz-appearance: none;
  -webkit-appearance: none;
  appearance: none;

  border: 0;
  height: 38px !important;
  background-color: #ffffd8;
  background-repeat: no-repeat;
  background-size: 0.5em auto;
  background-position: right 0.25em center;
  padding-left: 8px;
  padding-right: 18px;
  padding-top: 0;
  padding-bottom: 2px !important;
  text-align: inherit;

  background-image: url("data:image/svg+xml;charset=utf-8, \
    <svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 60 40'> \
      <polygon points='0,0 60,0 30,40' style='fill:black;'/> \
    </svg>");
}

input.sodar-ss-vue-popup-input,
select.sodar-ss-vue-popup-input {
  border: 1px solid #ced4da;
  border-radius: .25rem;
}

</style>
