<template>
  <b-modal id="sodar-ss-vue-col-manage-modal"
           ref="manageColumnModal"
           body-class="sodar-ss-vue-col-manage-body"
           centered no-fade hide-footer
           size="md"
           no-close-on-backdrop
           no-close-on-esc>
    <template slot="modal-header">
      <div class="w-100">
      <h5 class="modal-title text-nowrap" id="sodar-ss-vue-col-modal-title">
        {{ this.fieldDisplayName }}
        <span class="pull-right">
          <b-input-group class="sodar-header-input-group">
            <b-input-group-prepend>
            <b-button class="sodar-list-btn"
                      ref="copyBtn"
                      title="Copy configuration to clipboard"
                      v-clipboard:copy="this.getCopyData()"
                      v-clipboard:success="onCopySuccess"
                      v-clipboard:error="onCopyError"
                      v-b-tooltip.hover>
              <i class="fa fa-clipboard"></i>
            </b-button>
            </b-input-group-prepend>
            <b-form-input
              id="sodar-ss-vue-col-input-paste"
              ref="pasteInput"
              v-model="pasteData"
              @input="onPasteInput"
              placeholder="Paste"
              title="Paste a copied configuration here"
              v-b-tooltip.hover>
            </b-form-input>
          </b-input-group>
        </span>
        <span class="pull-right text-nowrap text-right">
          <notify-badge ref="notifyBadge"></notify-badge>
        </span>
        </h5>
      </div>
    </template>
    <div class="sodar-ss-vue-col-manage-content">
      <table v-if="fieldConfig"
            class="table table-borderless w-100"
            id="sodar-ss-vue-col-manage-table">
        <tbody>
          <!-- Editable -->
          <tr>
            <td>Editable</td>
            <td>
              <b-checkbox plain v-model="fieldConfig['editable']"></b-checkbox>
            </td>
          </tr>
          <!-- Format -->
          <tr>
            <td>Format</td>
            <td>
              <b-select id="sodar-ss-vue-col-select-format"
                        v-model="fieldConfig['format']"
                        @change="onFormatChange">
                <option v-for="(option, index) in this.formatOptions"
                        :key="index"
                        :value="option"
                        :selected="option === fieldConfig['format']">
                  {{ option }}
                </option>
              </b-select>
            </td>
          </tr>
          <tr>
            <td colspan="2"><hr class="my-1" /></td>
          </tr>
          <!-- Select -->
          <tr v-if="fieldConfig['format'] === 'select'">
            <td class="align-top pt-3">
              Options
              <i class="fa fa-info-circle text-info"
                 title="Separate options by newline"
                 v-b-tooltip.hover>
              </i>
            </td>
            <td>
              <b-textarea v-model="valueOptions"
                          rows="4"
                          @input="validate('select')">
                {{ valueOptions }}
              </b-textarea>
            </td>
          </tr>
          <!-- Range -->
          <tr v-if="fieldConfig['format'] === 'integer' ||
                    fieldConfig['format'] === 'double'">
            <td>Range</td>
            <td>
              <b-row>
                <b-col sm="5" class="p-0">
                  <b-input id="sodar-ss-vue-col-range-min"
                           class="text-right"
                           v-model="fieldConfig['range'][0]"
                           placeholder="Min"
                           ref="minRangeInput"
                           :class="formClasses['range']"
                           @input="validate('range')">
                    {{ fieldConfig['range'][0] }}
                  </b-input>
                </b-col>
                <b-col sm="2" class="text-center align-middle pt-1">-</b-col>
                <b-col sm="5" class="p-0">
                  <b-input id="sodar-ss-vue-col-range-max"
                           class="text-right"
                           v-model="fieldConfig['range'][1]"
                           placeholder="Max"
                           ref="maxRangeInput"
                           :class="formClasses['range']"
                           @input="validate('range')">
                    {{ fieldConfig['range'][1] }}
                  </b-input>
                </b-col>
              </b-row>
            </td>
          </tr>
          <!-- Regex -->
          <tr v-if="fieldConfig['format'] !== 'select'">
            <td>Regex</td>
            <td>
              <b-input v-model="fieldConfig['regex']"
                       @input="onRegexInput"
                       :class="formClasses['regex']">
              </b-input>
            </td>
          </tr>
          <!-- Unit -->
          <!-- TODO: Only allow for columns where this is valid -->
          <tr v-if="fieldConfig['format'] === 'integer' ||
                    fieldConfig['format'] === 'double'">
            <td class="align-top pt-3">
              Unit
              <i class="fa fa-info-circle text-info"
                 title="Separate options by newline"
                 v-b-tooltip.hover>
              </i>
            </td>
            <td>
              <b-textarea v-model="unitOptions" rows="2">
                {{ unitOptions }}
              </b-textarea>
            </td>
          </tr>
          <!-- Default unit -->
          <tr v-if="fieldConfig['format'] === 'integer' ||
                    fieldConfig['format'] === 'double'">
            <td>Default Unit</td>
            <td>
              <b-select v-model="fieldConfig['unit_default']"
                        :disabled="!unitOptions">
                <option :value="null">-</option>
                <option v-for="(option, index) in unitOptions.split('\n')"
                        :key="index"
                        :value="option">
                  {{ option }}
                </option>
              </b-select>
            </td>
          </tr>
          <!-- Default value -->
          <tr>
            <td>Default Value</td>
            <td>
              <!-- String/integer/double default -->
              <b-input v-if="fieldConfig['format'] !== 'select'"
                       v-model="fieldConfig['default']"
                       @input="onDefaultInput"
                       id="sodar-ss-vue-column-input-default"
                       :class="formClasses['default']">
              </b-input>
              <!-- Selection default -->
              <b-select v-else
                        v-model="fieldConfig['default']"
                        id="sodar-ss-vue-column-select-default"
                        @change="onDefaultChange"
                        :disabled="!valueOptions">
                <option :value="null">-</option>
                <option v-for="(option, index) in valueOptions.split('\n')"
                        :key="index"
                        :value="option">
                  {{ option }}
                </option>
              </b-select>
            </td>
          </tr>
          <tr>
            <td>Default Fill</td>
            <td>
              <span id="sodar-ss-vue-column-wrapper-default"
                    title="Fill empty column values with default value on update"
                    v-b-tooltip.right.hover>
                <b-checkbox
                    plain
                    v-model="defaultFill"
                    :disabled="!defaultFillEnable"
                    id="sodar-ss-vue-column-check-default">
                </b-checkbox>
              </span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <div>
      <b-button-group class="pull-right"
                      id="sodar-ss-vue-col-btn-group">
        <b-button variant="secondary" @click="hideModal(false)">
          <i class="fa fa-times"></i> Cancel
        </b-button>
        <b-button variant="primary"
                  @click="hideModal(true)"
                  ref="updateBtn">
          <i class="fa fa-check"></i> Update
        </b-button>
      </b-button-group>
    </div>
  </b-modal>
</template>

<script>
import NotifyBadge from './NotifyBadge.vue'
const integerRegex = /^(([1-9][0-9]*)|([0]?))$/
const invalidClasses = 'text-danger'

export default {
  name: 'ManageColumnModal',
  components: {
    NotifyBadge
  },
  props: [
    'app',
    'projectUuid',
    'studyUuid'
  ],
  data () {
    return {
      formatOptions: [
        'string',
        'integer',
        'select'
      ],
      fieldDisplayName: null,
      fieldConfig: null,
      newConfig: false,
      baseCellClasses: null,
      assayUuid: null,
      configNodeIdx: null,
      configFieldIdx: null,
      defNodeIdx: null,
      defFieldIdx: null,
      col: null,
      colType: null,
      gridOptions: null,
      valueOptions: '',
      unitEnabled: false,
      unitOptions: '',
      inputValid: {
        'options': true,
        'range': true,
        'regex': true,
        'default': true
      },
      formClasses: {
        'options': '',
        'range': '',
        'regex': '',
        'default': ''
      },
      defaultFill: false,
      defaultFillEnable: false,
      pasteData: ''
    }
  },
  methods: {
    /* Event handling ------------------------------------------------------- */
    onFormatChange () {
      this.validate()
    },
    onRegexInput () {
      this.validate('regex')
      if (this.inputValid['regex']) {
        this.validate('range') // Depends on regex
        this.validate('default') // Depends on regex
      }
    },
    onDefaultInput () {
      if (this.fieldConfig['default'].length === 0) {
        this.defaultFill = false // No default fill if we don't have default
      }
      this.validate('default')
    },
    onDefaultChange () {
      if (!this.fieldConfig['default'] ||
          this.fieldConfig['default'].length === 0) {
        this.defaultFill = false
        this.defaultFillEnable = false
      } else {
        this.defaultFillEnable = true
      }
    },
    onPasteInput (val) {
      let pasteData
      let pasteValid = true

      try {
        pasteData = JSON.parse(val)
      } catch (error) {
        this.$refs.notifyBadge.show('Invalid JSON', 'danger', 1000)
        pasteValid = false
      }

      if (pasteValid && (!pasteData.hasOwnProperty('format') ||
          !pasteData.hasOwnProperty('editable'))) {
        pasteValid = false
        this.$refs.notifyBadge.show('Invalid Data', 'danger', 2000)
      } // TODO: Other checks for required fields

      if (pasteValid) {
        let copyableKeys = [
          'format', 'editable', 'regex', 'options', 'range', 'default',
          'unit', 'unit_default'
        ]

        // Copy data from pasted content
        for (let i in copyableKeys) {
          let k = copyableKeys[i]
          if (pasteData.hasOwnProperty(k)) {
            this.fieldConfig[k] = pasteData[k]
          } else if (k === 'range') { // Range is a special case
            this.fieldConfig[k] = [null, null]
          } else if (['options', 'unit'].includes(k)) { // Options too
            this.fieldConfig[k] = []
          }
        }
        this.setWidgetData()
        this.validate()
        this.$refs.notifyBadge.show('Config Pasted', 'success', 1000)
      }

      // Clear the original value regardless of success/failure
      this.$nextTick(() => {
        this.pasteData = ''
      })
    },
    onCopySuccess (event) {
      this.$refs.notifyBadge.show('Config Copied', 'success', 1000)
    },
    onCopyError (event) {
      this.$refs.notifyBadge.show('Copy Error', 'danger', 2000)
      console.log('Copy Error: ' + event)
    },
    /* Helpers -------------------------------------------------------------- */
    setWidgetData () {
      // Set up certain data for the form widgets
      if (this.fieldConfig.hasOwnProperty('options')) {
        this.valueOptions = this.fieldConfig['options'].join('\n')
      }
      if (this.fieldConfig.hasOwnProperty('unit')) {
        this.unitEnabled = true
        this.unitOptions = this.fieldConfig['unit'].join('\n')
      }
    },
    validate (inputParam) {
      // Select
      if (!inputParam || inputParam === 'select') {
        let val = this.valueOptions
        let valSplit = val.split('\n')
        this.inputValid['options'] = val &&
          valSplit.length >= 2 &&
          !valSplit.includes('')
      }

      // Range
      if (!inputParam || inputParam === 'range') {
        let rangeValid = true
        let rangeMin = this.fieldConfig['range'][0] || ''
        let rangeMax = this.fieldConfig['range'][1] || ''

        // Validate individual min/max fields
        if (rangeValid) {
          let rangeRegex = this.getRegex()
          if (rangeRegex &&
              ((rangeMin && !rangeRegex.test(rangeMin)) ||
              (rangeMax && !rangeRegex.test(rangeMax)))) {
            rangeValid = false
          }
        }

        // Validate the actual range
        if (rangeValid &&
            ((rangeMin.length > 0 && rangeMax.length === 0) ||
            (rangeMax.length > 0 && rangeMin.length === 0) ||
            parseFloat(rangeMin) >= parseFloat(rangeMax))) {
          rangeValid = false
        }

        // Handle result
        this.formClasses['range'] = rangeValid ? '' : invalidClasses
        this.inputValid['range'] = rangeValid
      }

      // Regex
      if (!inputParam || inputParam === 'regex') {
        let val = this.fieldConfig['regex']
        try {
          RegExp(val)
          this.inputValid['regex'] = true
          this.formClasses['regex'] = ''
        } catch (error) {
          this.inputValid['regex'] = false
          this.formClasses['regex'] = invalidClasses
        }
      }

      // Default
      if (!inputParam || inputParam === 'default') {
        let valueRegex = this.getRegex()
        if (this.fieldConfig.hasOwnProperty('default') &&
            this.fieldConfig['default'].length > 0 &&
            valueRegex &&
            this.inputValid['regex']) {
          if (valueRegex.test(this.fieldConfig['default'])) {
            this.inputValid['default'] = true
            this.formClasses['default'] = ''
            this.defaultFillEnable = true
          } else {
            this.inputValid['default'] = false
            this.formClasses['default'] = invalidClasses
            this.defaultFillEnable = false
          }
        } else {
          this.inputValid['default'] = true
          this.formClasses['default'] = ''
          this.defaultFillEnable = false
        }
      }

      // Always call setUpdateState() after validation
      this.setUpdateState()
    },
    setUpdateState () {
      if (this.fieldConfig['format'] === 'select') {
        this.$refs.updateBtn.disabled = !this.inputValid['options'] ||
            !this.valueOptions
      } else if (this.fieldConfig['format'] === 'string') {
        this.$refs.updateBtn.disabled = !this.inputValid['regex'] ||
            !this.inputValid['default']
      } else {
        this.$refs.updateBtn.disabled = !this.inputValid['regex'] ||
            !this.inputValid['range'] ||
            !this.inputValid['default']
      }
      this.$refs.copyBtn.disabled = this.$refs.updateBtn.disabled
    },
    cleanupFieldConfig (config, valueOptions, unitOptions) {
      // Handle regex/options depending on select format
      if (config['format'] === 'select') {
        delete config['regex']
        config['options'] = valueOptions.split('\n')
      } else {
        delete config['options']
      }
      // Remove range and unit if not integer/double
      if (!['integer', 'double'].includes(config['format'])) {
        delete config['range']
        delete config['unit']
        delete config['unit_default']
      } else { // Set up unit
        if (unitOptions.length === 0) {
          delete config['unit']
        } else {
          config['unit'] = unitOptions.split('\n')
        }
      }
      return config
    },
    getRegex () {
      if (this.fieldConfig['regex'].length === 0) {
        if (this.fieldConfig['format'] === 'integer') {
          return integerRegex
        }
      } else if (this.inputValid['regex']) {
        return RegExp(this.fieldConfig['regex'])
      }
      return null
    },
    getCopyData () {
      if (!this.fieldConfig) {
        return ''
      }
      let copyConfig = JSON.parse(JSON.stringify(this.fieldConfig)) // Copy
      delete copyConfig['name']
      delete copyConfig['type']
      return JSON.stringify(
        this.cleanupFieldConfig(
          copyConfig, this.valueOptions, this.unitOptions))
    },
    updateColDefs (uuid, assayMode) {
      let gridOptions = this.app.getGridOptionsByUuid(uuid)

      let colDef
      if (!assayMode) {
        colDef = this.app.columnDefs['study'][this.defNodeIdx]
          .children[this.defFieldIdx]
      } else {
        colDef = this.app.columnDefs['assays'][uuid][this.defNodeIdx]
          .children[this.defFieldIdx]
      }

      colDef.headerComponentParams['colType'] = this.colType
      colDef.headerComponentParams['fieldConfig'] = this.fieldConfig
      colDef.cellEditorParams['editConfig'] = this.fieldConfig
      colDef.editable = this.fieldConfig['editable']

      if (this.fieldConfig['editable']) {
        colDef.cellClass = this.baseCellClasses
      } else {
        colDef.cellClass = this.baseCellClasses.concat(
          ['bg-light', 'text-muted']
        )
      }

      if (!assayMode) {
        this.app.columnDefs['study'][this.defNodeIdx]
          .children[this.defFieldIdx] = colDef
        gridOptions.api.setColumnDefs(this.app.columnDefs['study'])
      } else {
        this.app.columnDefs['assays'][uuid][this.defNodeIdx]
          .children[this.defFieldIdx] = colDef
        gridOptions.api.setColumnDefs(this.app.columnDefs['assays'][uuid]
        )
      }
    },
    handleUpdate () {
      // Determine current colType
      if (['integer', 'double'].includes(this.fieldConfig['format'])) {
        if (this.fieldConfig.hasOwnProperty('unit') &&
            this.fieldConfig['unit']) {
          this.colType = 'UNIT'
        } else {
          this.colType = 'NUMERIC'
        }
      } else { // TODO: Other column types
        this.colType = null
      }

      // console.log('colType: ' + this.ogColType + ' -> ' + this.colType) // DEBUG

      // Update column definitions in all tables
      if (this.defNodeIdx < this.app.columnDefs['study'].length) {
        this.updateColDefs(this.app.currentStudyUuid, false) // Update study
      }
      for (let k in this.app.columnDefs['assays']) { // Update assays
        this.updateColDefs(k, true)
      }

      // Fill default value to empty cells in column if selected
      if (this.defaultFill &&
          this.fieldConfig.hasOwnProperty('default') &&
          this.fieldConfig['default'].length > 0) {
        // Collect column cell data
        let field = this.col.colDef.field
        let cellUuids = [] // Store found cell UUIDs
        let upData = [] // The actual update data
        let refreshCells = true

        if (this.colType !== this.ogColType) {
          refreshCells = false
        }

        for (let i = 0; i < this.gridOptions.rowData.length; i++) {
          let row = this.gridOptions.rowData[i]

          if (row.hasOwnProperty(field) &&
              !cellUuids.includes(row[field]['uuid'])) {
            if (!row[field]['value'] || row[field]['value'].length === 0) {
              let cell = row[field]
              let ogValue = cell['value']
              cell['value'] = this.fieldConfig['default']
              upData.push(Object.assign(
                cell,
                {'og_value': ogValue},
                this.col.colDef.cellEditorParams['headerInfo']))
            }
            cellUuids.push(row[field]['uuid'])
          }
        }
        this.app.handleCellEdit(upData, refreshCells)
      }

      // If column type has changed, update colType and alignment
      if (this.colType !== this.ogColType) {
        this.app.updateColType(this.col.colDef.field, this.colType, true)
      }
      this.app.setDataUpdated(true)
    },
    /* Modal showing/hiding ------------------------------------------------- */
    showModal (data, col) {
      this.fieldDisplayName = data['fieldDisplayName']
      this.fieldConfig = data['fieldConfig']
      this.newConfig = data['newConfig']
      this.baseCellClasses = data['baseCellClasses']
      this.assayUuid = data['assayUuid']
      this.configNodeIdx = data['configNodeIdx']
      this.configFieldIdx = data['configFieldIdx']
      this.defNodeIdx = data['defNodeIdx']
      this.defFieldIdx = data['defFieldIdx']
      this.col = col
      this.colType = data['colType']
      this.ogColType = data['colType'] // Save original colType
      let gridUuid = !this.assayUuid ? this.studyUuid : this.assayUuid
      this.gridOptions = this.app.getGridOptionsByUuid(gridUuid)

      // Reset internal variables
      this.valueOptions = ''
      this.unitEnabled = false
      this.unitOptions = ''

      // Set up fieldConfig
      if (!this.fieldConfig.hasOwnProperty('default')) {
        this.fieldConfig['default'] = ''
      }

      if (this.newConfig) {
        let field = this.col.colDef.field

        // Unit and numeric column
        if (['UNIT', 'NUMERIC'].includes(this.colType)) {
          // TODO: Also support double
          this.fieldConfig['format'] = 'integer'

          if (this.colType === 'UNIT') {
            this.fieldConfig['unit'] = []
          }

          for (let i = 0; i < this.gridOptions.rowData.length; i++) {
            let cell = this.gridOptions.rowData[i][field]

            // TODO: TBD: Guess range or not?
            /*
            let valNum = parseInt(cell['value'])

            if (this.fieldConfig['range'][0] === null ||
                this.fieldConfig['range'][0] > valNum) {
              this.fieldConfig['range'][0] = valNum
            }
            if (this.fieldConfig['range'][1] === null ||
                this.fieldConfig['range'][1] < valNum) {
              this.fieldConfig['range'][1] = valNum
            }
            */

            if (this.colType === 'UNIT' &&
                cell.hasOwnProperty('unit') &&
                !this.fieldConfig['unit'].includes(cell['unit'])) {
              this.fieldConfig['unit'].push(cell['unit'])
            }
          }
        }
      }

      // Set up certain data for the form widgets
      this.setWidgetData()

      // Show modal
      this.$refs.manageColumnModal.show()
    },
    hideModal (update) {
      if (update) {
        // Cleanup config
        this.fieldConfig = this.cleanupFieldConfig(
          this.fieldConfig, this.valueOptions, this.unitOptions)

        // Save config on server
        let upData = {
          'fields': [
            {
              'action': 'update',
              'study': this.studyUuid,
              'assay': this.assayUuid,
              'node_idx': this.configNodeIdx,
              'field_idx': this.configFieldIdx,
              'config': this.fieldConfig
            }
          ]
        }
        fetch('/samplesheets/api/manage/post/' + this.projectUuid, {
          method: 'POST',
          body: JSON.stringify(upData),
          credentials: 'same-origin',
          headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'X-CSRFToken': this.app.sodarContext['csrf_token']
          }
        }).then(data => data.json())
          .then(
            data => {
              if (data['message'] === 'ok') {
                this.handleUpdate() // Handle successful update here
                this.app.showNotification('Column Updated', 'success', 1000)
              } else {
                console.log('Update status: ' + data['message'])
                this.app.showNotification('Update Failed', 'danger', 2000)
              }
            }
          ).catch(function (error) {
            console.log('Error updating field: ' + error.message)
          })
      }
      this.$refs.manageColumnModal.hide()
    }
  }
}
</script>

<style scoped>
div.sodar-ss-vue-col-manage-content {
  min-height: 560px !important;
}

#sodar-ss-vue-col-input-paste {
  width: 70px;
}

table#sodar-ss-vue-col-manage-table tbody td:first-child {
  width: 100px;
  max-width: 250px;
  vertical-align: middle;
  white-space: nowrap;
}

#sodar-ss-vue-col-btn-group {
  padding-right: 12px;
}

#sodar-ss-vue-column-wrapper-default .form-check {
  width: 20px !important;
}

</style>
