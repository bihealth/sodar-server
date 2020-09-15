<template>
  <b-modal id="sodar-ss-vue-col-config-modal"
           ref="columnConfigModal"
           body-class="sodar-ss-vue-col-config-body"
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
                      :disabled="!enableCopy()"
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
              :disabled="!enableCopy()"
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
    <div class="sodar-ss-vue-col-config-content">
      <table v-if="fieldConfig"
            class="table table-borderless w-100"
            id="sodar-ss-vue-col-config-table">
        <!-- Editable (common for all types) -->
        <tbody>
          <tr>
            <td>Editable</td>
            <td>
              <b-checkbox plain v-model="fieldConfig.editable"></b-checkbox>
            </td>
          </tr>
        </tbody>
        <!-- Name column table body -->
        <tbody v-if="['NAME', 'LINK_FILE'].includes(colType)">
          <tr v-if="colType === 'NAME' &&
              headerInfo.item_type !== 'SOURCE'">
            <td>Default Suffix
              <i class="fa fa-info-circle text-info"
                 title="Pre-fill with the name of previous node plus a suffix if set"
                 v-b-tooltip.hover>
              </i>
            </td>
            <td>
              <b-input
                  v-model="fieldConfig.default"
                  @input="onDefaultInput"
                  id="sodar-ss-vue-column-input-default"
                  :class="formClasses.default">
              </b-input>
            </td>
          </tr>
          <tr>
            <td colspan="2" class="sodar-ss-vue-td-info text-danger">
              <strong>Warning:</strong> If you are storing project sample data
              in iRODS, renaming certain materials or processes may cause
              related iRODS links to stop working! When in doubt, please
              contact SODAR administrators or the project owner.
            </td>
          </tr>
        </tbody>
        <!-- Protocol table body -->
        <tbody v-else-if="colType === 'PROTOCOL'">
          <tr>
            <td>Default Value</td>
            <td>
              <b-select v-model="fieldConfig.default"
                        id="sodar-ss-vue-column-select-default"
                        @change="onDefaultChange">
                <option :value="null">-</option>
                <option v-for="(option, index) in app.editContext.protocols"
                        :key="index"
                        :value="option.uuid">
                  {{ option.name }}
                </option>
              </b-select>
            </td>
          </tr>
          <tr>
            <td colspan="2"><hr class="my-1" /></td>
          </tr>
          <tr>
            <td colspan="2" class="sodar-ss-vue-td-info text-muted">
              <em>Protocol editing will go here..</em>
            </td>
          </tr>
        </tbody>
        <!-- Contact table body -->
        <tbody v-else-if="colType === 'CONTACT'">
          <tr>
            <td colspan="2"><hr class="my-1" /></td>
          </tr>
          <tr>
            <td colspan="2" class="sodar-ss-vue-td-info">
              Enter the contact info as <code>Name &lt;email@domain.com&gt;</code>
              for linking. Popup editor is forthcoming.
            </td>
          </tr>
        </tbody>
        <!-- Date table body -->
        <tbody v-else-if="colType === 'DATE'">
          <tr>
            <td colspan="2"><hr class="my-1" /></td>
          </tr>
          <tr>
            <td colspan="2" class="sodar-ss-vue-td-info">
              Enter the date as <code>YYYY-MM-DD</code>.
            </td>
          </tr>
        </tbody>
        <!-- Basic field column table body -->
        <tbody v-else>
          <!-- Format -->
          <tr>
            <td>Format</td>
            <td>
              <b-select id="sodar-ss-vue-col-select-format"
                        v-model="fieldConfig.format"
                        @change="onFormatChange">
                <option v-for="(option, index) in this.formatOptions"
                        :key="index"
                        :value="option"
                        :selected="option === fieldConfig.format">
                  {{ option }}
                </option>
              </b-select>
            </td>
          </tr>
          <tr>
            <td colspan="2"><hr class="my-1" /></td>
          </tr>
          <!-- Select -->
          <tr v-if="fieldConfig.format === 'select'">
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
          <tr v-if="['integer', 'double'].includes(fieldConfig.format)">
            <td>Range</td>
            <td>
              <b-row>
                <b-col sm="5" class="p-0">
                  <b-input id="sodar-ss-vue-col-range-min"
                           class="text-right"
                           v-model="fieldConfig.range[0]"
                           placeholder="Min"
                           ref="minRangeInput"
                           :class="formClasses.range"
                           @input="validate('range')">
                    {{ fieldConfig.range[0] }}
                  </b-input>
                </b-col>
                <b-col sm="2" class="text-center align-middle pt-1">-</b-col>
                <b-col sm="5" class="p-0">
                  <b-input id="sodar-ss-vue-col-range-max"
                           class="text-right"
                           v-model="fieldConfig.range[1]"
                           placeholder="Max"
                           ref="maxRangeInput"
                           :class="formClasses.range"
                           @input="validate('range')">
                    {{ fieldConfig.range[1] }}
                  </b-input>
                </b-col>
              </b-row>
            </td>
          </tr>
          <!-- Regex -->
          <tr v-if="fieldConfig.format !== 'select'">
            <td>Regex</td>
            <td>
              <b-input v-model="fieldConfig.regex"
                       @input="onRegexInput"
                       :class="formClasses.regex">
              </b-input>
            </td>
          </tr>
          <!-- Default value -->
          <tr>
            <td>Default Value</td>
            <td>
              <!-- String/integer/double default -->
              <b-input v-if="fieldConfig.format !== 'select'"
                       v-model="fieldConfig.default"
                       @input="onDefaultInput"
                       id="sodar-ss-vue-column-input-default"
                       :class="formClasses.default">
              </b-input>
              <!-- Selection default -->
              <b-select v-else
                        v-model="fieldConfig.default"
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
              <span class="sodar-ss-vue-column-wrapper"
                    id="sodar-ss-vue-column-wrapper-default">
                <b-checkbox
                    plain
                    v-model="defaultFill"
                    :disabled="!defaultFillEnable"
                    title="Fill empty column values with default value on update"
                    id="sodar-ss-vue-column-check-default"
                    v-b-tooltip.right.hover>
                </b-checkbox>
              </span>
            </td>
          </tr>
          <!-- Enable/disable unit -->
          <!-- NOTE: Commented out as temporary fix for issue #889 -->
          <!--
          <tr v-if="['integer', 'double'].includes(fieldConfig.format)">
            <td>Enable Unit</td>
            <td>
              <span class="sodar-ss-vue-column-wrapper"
                    id="sodar-ss-vue-column-wrapper-unit"
                    title="Enable/disable unit: removes existing units from column if disabled"
                    v-b-tooltip.right.hover>
                <b-checkbox
                    plain
                    v-model="unitEnabled"
                    :disabled="!enableUnitSelect()"
                    id="sodar-ss-vue-column-check-unit">
                </b-checkbox>
              </span>
            </td>
          </tr>
          -->
          <!-- Unit -->
          <tr v-if="unitEnabled &&
                    ['integer', 'double'].includes(fieldConfig.format)">
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
          <tr v-if="unitEnabled &&
                    ['integer', 'double'].includes(fieldConfig.format)">
            <td>Default Unit</td>
            <td>
              <b-select v-model="fieldConfig.unit_default"
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
          <i :class="updateBtnClasses"></i> Update
        </b-button>
      </b-button-group>
    </div>
  </b-modal>
</template>

<script>
import NotifyBadge from '../NotifyBadge.vue'
const integerRegex = /^(([1-9][0-9]*)|([0]?))$/
const doubleRegex = /^-?[0-9]+\.[0-9]+?$/
const invalidClasses = 'text-danger'

export default {
  name: 'ColumnConfigModal',
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
      formatOptions: null,
      fieldDisplayName: null,
      fieldConfig: null,
      newConfig: false,
      assayUuid: null,
      configNodeIdx: null,
      configFieldIdx: null,
      col: null,
      colType: null,
      headerInfo: null,
      gridOptions: null,
      valueOptions: '',
      unitEnabled: false,
      unitOptions: '',
      inputValid: {
        options: true,
        range: true,
        regex: true,
        default: true
      },
      formClasses: {
        options: '',
        range: '',
        regex: '',
        default: ''
      },
      defaultFill: false,
      defaultFillEnable: false,
      pasteData: '',
      updateBtnClasses: null
    }
  },
  methods: {
    /* Event handling ------------------------------------------------------- */
    onFormatChange () {
      this.validate()
    },
    onRegexInput () {
      this.validate('regex')
      if (this.inputValid.regex) {
        this.validate('range') // Depends on regex
        this.validate('default') // Depends on regex
      }
    },
    onDefaultInput () {
      if (this.fieldConfig.default.length === 0) {
        this.defaultFill = false // No default fill if we don't have default
      }
      this.validate('default')
    },
    onDefaultChange () {
      this.toggleDefaultFill()
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

      if (pasteValid && (!('format' in pasteData) ||
          !('editable' in pasteData))) {
        pasteValid = false
        this.$refs.notifyBadge.show('Invalid Data', 'danger', 2000)
      } // TODO: Other checks for required fields

      if (pasteValid) {
        const copyableKeys = [
          'format', 'editable', 'regex', 'options', 'range', 'default',
          'unit', 'unit_default'
        ]

        // Copy data from pasted content
        for (const i in copyableKeys) {
          const k = copyableKeys[i]
          if (k in pasteData) {
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
    enableCopy () {
      return !(['NAME', 'LINK_FILE', 'PROTOCOL'].includes(this.colType))
    },
    /*
    enableUnitSelect () {
      return this.colType === 'UNIT' // HACK for issue #889
    },
    */
    toggleDefaultFill () {
      if (!('default' in this.fieldConfig) || !this.fieldConfig.default) {
        this.defaultFill = false
        this.defaultFillEnable = false
      } else {
        this.defaultFillEnable = true
      }
    },
    setWidgetData () {
      // Set up certain data for the form widgets
      if ('options' in this.fieldConfig) {
        this.valueOptions = this.fieldConfig.options.join('\n')
      }
      if ('unit' in this.fieldConfig) {
        this.unitEnabled = true
        this.unitOptions = this.fieldConfig.unit.join('\n')
      }
    },
    validate (inputParam) {
      // Select
      if (!inputParam || inputParam === 'select') {
        const val = this.valueOptions
        const valSplit = val.split('\n')
        this.inputValid.options = val &&
          valSplit.length >= 2 &&
          !valSplit.includes('')
      }

      // Range
      if (!inputParam || inputParam === 'range') {
        let rangeValid = true
        const rangeMin = this.fieldConfig.range[0] || ''
        const rangeMax = this.fieldConfig.range[1] || ''

        // Validate individual min/max fields
        if (rangeValid) {
          const rangeRegex = this.getRegex()
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
        this.formClasses.range = rangeValid ? '' : invalidClasses
        this.inputValid.range = rangeValid
      }

      // Regex
      if (!inputParam || inputParam === 'regex') {
        const val = this.fieldConfig.regex
        try {
          RegExp(val)
          this.inputValid.regex = true
          this.formClasses.regex = ''
        } catch (error) {
          this.inputValid.regex = false
          this.formClasses.regex = invalidClasses
        }
      }

      // Default
      if (!inputParam || inputParam === 'default') {
        const valueRegex = this.getRegex()
        if ('default' in this.fieldConfig &&
            this.fieldConfig.default.length > 0 &&
            valueRegex &&
            this.inputValid.regex) {
          if (valueRegex.test(this.fieldConfig.default)) {
            this.inputValid.default = true
            this.formClasses.default = ''
            this.defaultFillEnable = true
          } else {
            this.inputValid.default = false
            this.formClasses.default = invalidClasses
            this.defaultFillEnable = false
          }
        } else if (this.fieldConfig.default.length === 0) {
          this.inputValid.default = true
          this.formClasses.default = ''
          this.defaultFillEnable = false
        } else {
          this.inputValid.default = true
          this.formClasses.default = ''
          this.defaultFillEnable = true
        }
      }

      // Always call setUpdateState() after validation
      this.setUpdateState()
    },
    setUpdateState () {
      if (this.fieldConfig.format === 'select') {
        this.$refs.updateBtn.disabled = !this.inputValid.options ||
            !this.valueOptions
      } else if (this.fieldConfig.format === 'string') {
        this.$refs.updateBtn.disabled = !this.inputValid.regex ||
            !this.inputValid.default
      } else { // Integer and double
        this.$refs.updateBtn.disabled = !this.inputValid.regex ||
            !this.inputValid.range ||
            !this.inputValid.default
      }
      this.$refs.copyBtn.disabled = this.$refs.updateBtn.disabled
    },
    cleanupFieldConfig (config) {
      // Handle regex/options depending on select format
      if (config.format === 'select') {
        delete config.regex
        config.options = this.valueOptions.split('\n')
      } else {
        delete config.options
      }
      // Remove range and unit if not integer/double
      if (!['integer', 'double'].includes(config.format)) {
        delete config.range
        delete config.unit
        delete config.unit_default
      } else { // Set up unit
        if (!this.unitEnabled || this.unitOptions.length === 0) {
          delete config.unit
        } else {
          config.unit = this.unitOptions.split('\n')
        }
      }
      return config
    },
    getRegex () {
      if (this.fieldConfig.regex.length === 0) {
        if (this.fieldConfig.format === 'integer') {
          return integerRegex
        } else if (this.fieldConfig.format === 'double') {
          return doubleRegex
        }
      } else if (this.inputValid.regex) {
        return RegExp(this.fieldConfig.regex)
      }
      return null
    },
    getCopyData () {
      if (!this.fieldConfig) {
        return ''
      }
      const copyConfig = JSON.parse(JSON.stringify(this.fieldConfig)) // Copy
      delete copyConfig.name
      delete copyConfig.type
      return JSON.stringify(this.cleanupFieldConfig(copyConfig))
    },
    // Update column definition for the field in one grid by UUID
    updateColDefs (uuid, assayMode) {
      const gridOptions = this.app.getGridOptionsByUuid(uuid)
      const col = gridOptions.columnApi.getColumn(this.col.colDef.field)
      if (!col) return
      const colDef = col.colDef

      // TODO: We shouldn't have to update colType in so many places..
      // TODO: headerComponentParams update fails with certain columns, investigate!
      colDef.headerComponentParams.colType = this.colType
      colDef.cellRendererParams.colType = this.colType
      colDef.headerComponentParams.fieldConfig = this.fieldConfig
      colDef.cellEditorParams.editConfig = this.fieldConfig
      colDef.editable = this.fieldConfig.editable
      colDef.cellRendererParams.fieldEditable = this.fieldConfig.editable

      // Determine alignment
      let colAlign = 'left'
      if (['UNIT', 'NUMERIC'].includes(this.colType)) {
        colAlign = 'right'
      }
      // Update alignment for editor
      colDef.cellEditorParams.renderInfo.align = colAlign
    },
    // Update column type for a field in all grids
    // TODO: Remove once refactoring colType and comparators (see #747)
    updateColType (fieldId, colType) {
      const gridUuids = this.app.getStudyGridUuids()

      for (let i = 0; i < gridUuids.length; i++) {
        const gridOptions = this.app.getGridOptionsByUuid(gridUuids[i])
        const gridApi = gridOptions.api

        if (!gridOptions.columnApi.getColumn(fieldId)) {
          continue // Skip this grid if the column is not present
        }

        // Update colType for each cell (needed for comparator)
        gridApi.forEachNode(function (rowNode) {
          if (fieldId in rowNode.data) {
            const value = rowNode.data[fieldId]
            value.colType = colType
            rowNode.setDataValue(fieldId, value)
          }
        })
      }
    },
    handleUpdate () {
      const fieldId = this.col.colDef.field
      let refreshCalled = false

      // Determine current colType
      if (['integer', 'double'].includes(this.fieldConfig.format)) {
        if (this.unitEnabled &&
            'unit' in this.fieldConfig &&
            this.fieldConfig.unit) {
          this.colType = 'UNIT'
        } else {
          this.colType = 'NUMERIC'
        }
      } else if (!['NAME', 'LINK_FILE', 'PROTOCOL', 'CONTACT', 'DATE'].includes(this.colType)) {
        this.colType = null
      }

      // console.log('colType: ' + this.ogColType + ' -> ' + this.colType) // DEBUG

      // Update column definitions in all tables
      this.updateColDefs(this.studyUuid, false) // Update study
      const studyOptions = this.app.getGridOptionsByUuid(this.app.currentStudyUuid)
      const assayUuids = this.app.getStudyGridUuids(true)
      for (let i = 0; i < assayUuids.length; i++) { // Update assays
        if (assayUuids[i] === this.assayUuid ||
            studyOptions.columnApi.getColumn(this.col.colDef.field)) {
          this.updateColDefs(assayUuids[i], true)
        }
      }

      // Update column type if changed
      if (this.colType !== this.ogColType) {
        this.updateColType(fieldId, this.colType)
      }

      // Cell modifications
      let fillDefault = false
      let removeUnit = false
      if (this.defaultFill &&
          'default' in this.fieldConfig &&
          this.fieldConfig.default.length > 0) {
        fillDefault = true
      }
      if (this.colType !== 'UNIT' && this.ogColType === 'UNIT') {
        removeUnit = true
      }

      // Update cells for default filling and/or unit removal
      if (fillDefault || removeUnit) {
        // Collect column cell data
        const cellUuids = [] // Store found cell UUIDs
        const upData = [] // The actual update data

        for (let i = 0; i < this.gridOptions.rowData.length; i++) {
          const row = this.gridOptions.rowData[i]
          const cell = row[fieldId]

          if (fieldId in row && !cellUuids.includes(cell.uuid)) {
            const ogValue = cell.value
            let modified = false

            // Update default value
            if (cell.value.length === 0) {
              cell.value = this.fieldConfig.default
              modified = true
            }

            // Remove unit
            if (removeUnit && cell.unit && cell.unit.length > 0) {
              if (typeof cell.unit === 'object' && 'name' in cell.unit) {
                cell.unit.name = null
              } else {
                cell.unit = null
              }
              modified = true
            }

            if (modified) {
              upData.push(Object.assign(
                cell,
                { og_value: ogValue },
                this.col.colDef.cellEditorParams.headerInfo))
            }
            cellUuids.push(row[fieldId].uuid)
          }
        }
        this.app.handleCellEdit(upData, true)
        refreshCalled = true
      }

      if (!refreshCalled) {
        const gridUuids = this.app.getStudyGridUuids()
        const editable = this.fieldConfig.editable
        const colType = this.colType

        for (let i = 0; i < gridUuids.length; i++) {
          const gridApi = this.app.getGridOptionsByUuid(gridUuids[i]).api

          // Update cell editability override in new rows
          // TODO: Refactor and fix (see issue #897)
          gridApi.forEachNode(function (rowNode) {
            if ('newRow' in rowNode.data.col0 && fieldId in rowNode.data) {
              const newValue = rowNode.data[fieldId]
              if (['NAME', 'LINK_FILE', 'PROTOCOL'].includes(colType)) {
                newValue.editable = true
              } else if ('newInit' in newValue && !newValue.newInit) {
                newValue.editable = editable
              }
              rowNode.setDataValue(fieldId, newValue)
            }
          })

          // TODO: refreshCells doesn't work with dynamic cellClass. ag-grid bug?
          // gridApi.refreshCells({ columns: [fieldId], force: true })
          gridApi.redrawRows()
        }
      }
      this.app.setDataUpdated(true)
    },
    /* Modal showing/hiding ------------------------------------------------- */
    showModal (data, col) {
      this.fieldDisplayName = data.fieldDisplayName
      this.fieldConfig = data.fieldConfig
      this.newConfig = data.newConfig
      this.assayUuid = data.assayUuid
      this.configNodeIdx = data.configNodeIdx
      this.configFieldIdx = data.configFieldIdx
      this.col = col
      this.colType = data.colType
      this.headerInfo = this.col.colDef.cellEditorParams.headerInfo
      this.ogColType = data.colType // Save original colType
      const gridUuid = !this.assayUuid ? this.studyUuid : this.assayUuid
      this.gridOptions = this.app.getGridOptionsByUuid(gridUuid)
      this.updateBtnClasses = 'fa fa-fw fa-check'

      // Reset internal variables
      this.valueOptions = ''
      this.unitEnabled = false
      this.unitOptions = ''

      if (this.colType !== 'UNIT') {
        this.formatOptions = ['string', 'integer', 'double', 'select']
      } else {
        this.formatOptions = ['integer', 'double'] // HACK for issue #889
      }

      // console.log('colId/field=' + this.col.colDef.field) // DEBUG
      // console.log('colType=' + this.colType) // DEBUG
      // console.dir(this.fieldConfig) // DEBUG

      // Set up fieldConfig
      if (!('default' in this.fieldConfig)) {
        this.fieldConfig.default = ''
      }

      if (!['NAME', 'LINK_FILE'].includes(this.colType) && this.newConfig) {
        const field = this.col.colDef.field

        // Unit and numeric column
        if (['UNIT', 'NUMERIC'].includes(this.colType)) {
          this.fieldConfig.format = 'integer' // Double checked later
          const doubleSep = ['.', ',']

          if (this.colType === 'UNIT') {
            this.fieldConfig.unit = []
          }

          for (let i = 0; i < this.gridOptions.rowData.length; i++) {
            const cell = this.gridOptions.rowData[i][field]

            if (doubleSep.some(el => cell.value.includes(el))) {
              this.fieldConfig.format = 'double'
            }

            // TODO: TBD: Guess range or not?
            /*
            let valNum = parseInt(cell.value)

            if (this.fieldConfig.range[0] === null ||
                this.fieldConfig.range[0] > valNum) {
              this.fieldConfig.range[0] = valNum
            }
            if (this.fieldConfig.range[1] === null ||
                this.fieldConfig.range[1] < valNum) {
              this.fieldConfig.range[1] = valNum
            }
            */

            if (this.colType === 'UNIT' &&
                'unit' in cell &&
                !this.fieldConfig.unit.includes(cell.unit)) {
              this.fieldConfig.unit.push(cell.unit)
            }
          }
        } else if (this.colType === 'DATE') {
          this.fieldConfig.format = 'date'
        }
      }

      // Set up certain data for the form widgets
      this.setWidgetData()
      this.toggleDefaultFill()

      // Show modal
      this.$refs.columnConfigModal.show()
    },
    hideModal (update) {
      if (update) {
        this.updateBtnClasses = 'fa fa-fw fa-spin fa-refresh'

        // Cleanup config
        this.fieldConfig = this.cleanupFieldConfig(this.fieldConfig)

        // Save config on server
        const upData = {
          fields: [
            {
              action: 'update',
              study: this.studyUuid,
              assay: this.assayUuid,
              node_idx: this.configNodeIdx,
              field_idx: this.configFieldIdx,
              config: this.fieldConfig
            }
          ]
        }

        const postUpdate = async () => {
          const data = await fetch('/samplesheets/ajax/manage/' + this.projectUuid, {
            method: 'POST',
            body: JSON.stringify(upData),
            credentials: 'same-origin',
            headers: {
              Accept: 'application/json',
              'Content-Type': 'application/json',
              'X-CSRFToken': this.app.sodarContext.csrf_token
            }
          })
          const updateData = await data.json()

          if (updateData.message === 'ok') {
            this.handleUpdate() // Handle successful update here
            this.app.showNotification('Column Updated', 'success', 1000)
          } else {
            console.log('Update status: ' + updateData.message)
            this.app.showNotification('Update Failed', 'danger', 2000)
          }
        }

        try {
          postUpdate()
        } catch (error) {
          console.log('Update error: ' + error.message)
        }
      }
      this.$refs.columnConfigModal.hide()
    }
  }
}
</script>

<style scoped>
div.sodar-ss-vue-col-config-content {
  min-height: 620px !important;
}

#sodar-ss-vue-col-input-paste {
  width: 70px;
}

table#sodar-ss-vue-col-config-table tbody td:first-child {
  width: 100px;
  max-width: 250px;
  vertical-align: middle;
  white-space: nowrap;
}

#sodar-ss-vue-col-btn-group {
  padding-right: 12px;
}

.sodar-ss-vue-column-wrapper .form-check {
  width: 20px !important;
}

td.sodar-ss-vue-td-info {
  white-space: normal !important;
}

</style>
