<template>
  <div class="ag-header-group-cell-label sodar-ss-header-edit">
    <span class="ag-header-group-text">
      {{ displayName }}
    </span>
    <span class="ml-auto">
      <b-button
          v-if="canEditConfig"
          variant="secondary"
          class="sodar-list-btn sodar-ss-col-config-btn"
          title="Configure Column"
          @click="onModalShow"
          :disabled="!isEnabled()"
          v-b-tooltip.hover>
        <i class="iconify" data-icon="mdi:lead-pencil"></i>
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
      fieldConfig: null,
      canEditConfig: null
    }
  },
  methods: {
    refresh (params) {
      this.params = params
      return true
    },
    onModalShow () {
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
        } else fieldConfig.format = 'string'
        newConfig = true // No existing config found
      }
      if (!('editable' in fieldConfig)) fieldConfig.editable = false
      if (!('range' in fieldConfig)) fieldConfig.range = [null, null]
      if (!('regex' in fieldConfig)) fieldConfig.regex = ''

      this.modalComponent.showModal({
        col: this.params.column,
        fieldConfig: fieldConfig,
        newConfig: newConfig,
        colType: this.params.colType,
        fieldDisplayName: this.displayName,
        assayUuid: this.params.assayUuid,
        configNodeIdx: this.params.configNodeIdx,
        configFieldIdx: this.params.configFieldIdx
      })
    },
    isEnabled () {
      // Temporary workaround for issue #897
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
    this.canEditConfig = this.params.canEditConfig
  }
})

</script>

<style scoped>
.sodar-ss-col-config-btn:focus {
  box-shadow: none !important;
}
</style>
