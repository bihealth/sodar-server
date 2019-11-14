<template>
  <b-modal id="sodar-ss-vue-col-manage-modal"
           ref="manageColumnModal"
           body-class="sodar-ss-vue-col-manage-body"
           centered no-fade hide-footer
           size="md">
    <template slot="modal-header">
      <h5 class="modal-title text-nowrap w-100">
        {{ this.fieldDisplayName }}
        <div class="pull-right text-muted text-nowrap text-right">Manage Column</div>
      </h5>
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
                          rows="5"
                          @input="onSelectInput">
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
                           :class="rangeClasses"
                           @input="onRangeInput">
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
                           :class="rangeClasses"
                           @input="onRangeInput">
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
                       :class="regexClasses">
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
              <b-textarea v-model="unitOptions" rows="3">
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
                       v-model="fieldConfig['default']">
              </b-input>
              <b-select v-else
                        v-model="fieldConfig['default']"
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

const integerRegex = /^(([1-9][0-9]*)|([0]?))$/

export default {
  name: 'ManageColumnModal',
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
      baseCellClasses: null,
      assayUuid: null,
      colIdx: null,
      fieldIdx: null,
      col: null,
      valueOptions: '',
      unitEnabled: false,
      unitOptions: '',
      inputValid: {
        'options': true,
        'range': true,
        'regex': true
      },
      regexClasses: '',
      rangeClasses: ''
    }
  },
  methods: {
    /* Event handling ------------------------------------------------------- */
    onFormatChange () {
      this.setUpdateState()
    },
    onSelectInput (val) {
      let valSplit = val.split('\n')
      this.inputValid['options'] = val && valSplit.length >= 2 && !valSplit.includes('')
      this.setUpdateState()
    },
    onRangeInput () {
      let rangeElems = [
        document.querySelector('#sodar-ss-vue-col-range-min'),
        document.querySelector('#sodar-ss-vue-col-range-max')
      ]
      let rangeValid = true
      let rangeRegex
      if (this.fieldConfig['regex'].length === 0 && this.inputValid['regex']) {
        rangeRegex = integerRegex
      } else {
        rangeRegex = RegExp(this.fieldConfig['regex'])
      }

      // Validate individual fields
      rangeElems.forEach(elem => {
        if (elem.value.length > 0 && !rangeRegex.test(elem.value)) {
          rangeValid = false
        }
      })

      // Check that range is valid
      if (rangeValid &&
          ((rangeElems[0].value.length > 0 && rangeElems[1].value.length === 0) ||
          (rangeElems[1].value.length > 0 && rangeElems[0].value.length === 0) ||
          parseFloat(rangeElems[0].value) >= parseFloat(rangeElems[1].value))) {
        rangeValid = false
      }

      // Handle validity
      if (rangeValid) {
        this.rangeClasses = ''
      } else {
        this.rangeClasses = 'text-danger'
      }
      this.inputValid['range'] = rangeValid
      this.setUpdateState()
    },
    onRegexInput (val) {
      try {
        RegExp(val)
        this.inputValid['regex'] = true
        this.regexClasses = ''
      } catch (e) {
        this.inputValid['regex'] = false
        this.regexClasses = 'text-danger'
      }
      this.setUpdateState()
    },
    /* Helpers -------------------------------------------------------------- */
    setUpdateState () {
      if (this.fieldConfig['format'] === 'select') {
        this.$refs.updateBtn.disabled = !this.inputValid['options'] || !this.valueOptions
      } else if (this.fieldConfig['format'] === 'string') {
        this.$refs.updateBtn.disabled = !this.inputValid['regex']
      } else {
        this.$refs.updateBtn.disabled = !this.inputValid['regex'] || !this.inputValid['range']
      }
    },
    /* Modal showing/hiding ------------------------------------------------- */
    showModal (data, col) {
      this.fieldDisplayName = data['fieldDisplayName']
      this.fieldConfig = JSON.parse(JSON.stringify(data['fieldConfig'])) // Copy
      this.baseCellClasses = data['baseCellClasses']
      this.assayUuid = data['assayUuid']
      this.nodeIdx = data['nodeIdx']
      this.fieldIdx = data['fieldIdx']
      this.col = col

      // Reset internal variables
      this.valueOptions = ''
      this.unitEnabled = false
      this.unitOptions = ''

      // Set up certain data for the form widgets
      if (this.fieldConfig.hasOwnProperty('options')) {
        this.valueOptions = this.fieldConfig['options'].join('\n')
      }
      if (this.fieldConfig.hasOwnProperty('unit')) {
        this.unitEnabled = true
        this.unitOptions = this.fieldConfig['unit'].join('\n')
      }

      this.$refs.manageColumnModal.show()
    },
    hideModal (update) {
      if (update) {
        // Cleanup config
        // Handle regex/options depending on select format
        if (this.fieldConfig['format'] === 'select') {
          delete this.fieldConfig['regex']
          this.fieldConfig['options'] = this.valueOptions.split('\n')
        } else {
          delete this.fieldConfig['options']
        }
        // Remove range and unit if not integer/double
        if (!['integer', 'double'].includes(this.fieldConfig['format'])) {
          delete this.fieldConfig['range']
          delete this.fieldConfig['unit']
          delete this.fieldConfig['unit_default']
        } else { // Set up unit
          if (this.unitOptions.length === 0) {
            delete this.fieldConfig['unit']
          } else {
            this.fieldConfig['unit'] = this.unitOptions.split('\n')
          }
        }

        // Update fieldConfig in all tables (if study field in multiple tables)
        let colField = this.col.colDef.field
        let columnApis = [this.app.gridOptions['study'].columnApi]
        for (let k in this.app.gridOptions['assays']) {
          columnApis.push(this.app.gridOptions['assays'][k].columnApi)
        }

        for (let i = 0; i < columnApis.length; i++) {
          let col = columnApis[i].getColumn(colField)

          if (col) {
            // Set the edited fieldConfig to the field header and the editor
            col.colDef.headerComponentParams['fieldConfig'] = this.fieldConfig
            col.colDef.cellEditorParams['editConfig'] = this.fieldConfig
            col.colDef.editable = this.fieldConfig['editable']

            if (this.fieldConfig['editable']) {
              col.colDef.cellClass = this.baseCellClasses
            } else {
              col.colDef.cellClass = this.baseCellClasses.concat(
                ['bg-light', 'text-muted']
              )
            }
            // Refresh view for layout changes to take effect
            // NOTE: refreshCells() for the column only works the other way around
            // TODO: Report? (possible bug in ag-grid)
            col.gridApi.redrawRows()
          }
        }

        // Save config on server
        let upData = {
          'fields': [
            {
              'action': 'update',
              'study': this.studyUuid,
              'assay': this.assayUuid,
              'node_idx': this.nodeIdx,
              'field_idx': this.fieldIdx,
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
                this.app.showNotification('Column Updated', 'success', 1000)
              } else {
                console.log('Update status: ' + data['message']) // DEBUG
                this.app.showNotification('Update Failed', 'danger', 1000)
              }
            }
          ).catch(function (error) {
            console.log('Error updating field: ' + error.message)
          })
      } else {
        this.app.showNotification('Update Cancelled', 'secondary', 1000)
      }
      this.$refs.manageColumnModal.hide()
    }
  }
}
</script>

<style scoped>
div.sodar-ss-vue-col-manage-content {
  min-height: 550px !important;
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

</style>
