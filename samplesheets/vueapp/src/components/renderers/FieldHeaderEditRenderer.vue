<template>
  <div class="ag-header-group-cell-label">
    <span class="ag-header-group-text">
      {{ displayName }}
    </span>
    <span class="ml-auto">
      <b-button
          variant="secondary"
          class="sodar-list-btn sodar-vue-col-config-btn"
          title="Configure Column"
          @click="onModalClick"
          :disabled="!isEnabled()"
          v-b-tooltip.hover>
        <i class="fa fa-pencil"></i>
      </b-button>
    </span>
  </div>
</template>

<script>
import Vue from 'vue'

export default Vue.extend({
  data () {
    return {
      app: null,
      modalComponent: null,
      displayName: null,
      fieldConfig: null
    }
  },
  methods: {
    refresh (params) {
      this.params = params
      return true
    },
    onModalClick () {
      const colDef = this.params.column.colDef
      let fieldConfig
      let newConfig

      // Refresh fieldConfig in case it's changed
      if (colDef.headerComponentParams.fieldConfig) {
        fieldConfig = JSON.parse(
          JSON.stringify(colDef.headerComponentParams.fieldConfig)) // Copy
        newConfig = false
      } else {
        fieldConfig = {}
        newConfig = true
      }

      // Add default values for fieldConfig if they are not present
      // TODO: Refactor/simplify
      // TODO: Move to ColumnConfigModal?
      if (!('name' in fieldConfig)) {
        fieldConfig.name = this.displayName
      }
      if (!('type' in fieldConfig)) {
        fieldConfig.type = this.params.headerType
      }
      if (!('format' in fieldConfig)) {
        if (fieldConfig.type === 'protocol') {
          fieldConfig.format = 'protocol'
        } else if (fieldConfig.type === 'perform_date') {
          fieldConfig.format = 'date'
        } else {
          fieldConfig.format = 'string'
        }
        newConfig = true // No existing config found
      }
      if (!('editable' in fieldConfig)) {
        fieldConfig.editable = false
      }
      if (!('range' in fieldConfig)) {
        fieldConfig.range = [null, null]
      }
      if (!('regex' in fieldConfig)) {
        fieldConfig.regex = ''
      }

      this.modalComponent.showModal({
        fieldConfig: fieldConfig,
        newConfig: newConfig,
        colType: this.params.colType,
        fieldDisplayName: this.displayName,
        assayUuid: this.params.assayUuid,
        configNodeIdx: this.params.configNodeIdx,
        configFieldIdx: this.params.configFieldIdx
      }, this.params.column)
    },
    isEnabled () {
      return !(this.app &&
        this.app.unsavedRow &&
        ['NAME', 'PROTOCOL', 'FILE_LINK'].includes(this.params.colType))
    }
  },
  beforeMount () {
    this.app = this.params.app
    this.modalComponent = this.params.modalComponent
    this.displayName = this.params.displayName
    this.fieldConfig = this.params.fieldConfig
  }
})

</script>

<style scoped>

.sodar-vue-col-config-btn:focus {
  box-shadow: none !important;
}

</style>
