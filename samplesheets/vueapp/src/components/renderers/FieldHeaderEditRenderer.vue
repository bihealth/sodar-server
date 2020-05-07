<template>
  <div class="ag-header-group-cell-label">
    <span class="ag-header-group-text">
      {{ displayName }}
    </span>
    <span class="ml-auto pt-1">
      <b-button
          variant="secondary"
          class="sodar-list-btn sodar-vue-col-config-btn"
          title="Configure Column"
          @click="onModalClick"
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
      // Refresh fieldConfig in case it's changed
      const fieldConfig = JSON.parse(
        JSON.stringify(this.params.column.colDef.headerComponentParams.fieldConfig)) // Copy
      let newConfig = false

      // Add default values for fieldConfig if they are not present
      if (!('format' in fieldConfig)) {
        fieldConfig.format = 'string'
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
        configFieldIdx: this.params.configFieldIdx,
        defNodeIdx: this.params.defNodeIdx,
        defFieldIdx: this.params.defFieldIdx
      }, this.params.column)
    }
  },
  beforeMount () {
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
