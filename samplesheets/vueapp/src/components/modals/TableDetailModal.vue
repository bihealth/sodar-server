<template>
  <b-modal
      id="sodar-ss-table-detail-modal" ref="tableDetailModal"
      centered no-fade hide-footer
      size="xl"
      :title="title + ' Details'"
      :static="true">
    <div id="sodar-ss-table-detail-modal-content">
      <table-detail-list
          v-if="tableContext"
          :assay-mode="assayMode"
          :table-context="tableContext"
          :table-meta-fields="tableMetaFields"
          :table-sodar-fields="tableSODARFields"
          :key="'detail-list-' + gridUuid">
      </table-detail-list>
    </div>
  </b-modal>
</template>

<script>

import TableDetailList from '../TableDetailList.vue'
import {
  studyMetaFields,
  studySODARFields,
  assayMetaFields,
  assaySODARFields
} from '@/constants'

export default {
  name: 'TableDetailModal',
  components: { TableDetailList },
  props: ['app'],
  data () {
    return {
      assayMode: null,
      gridUuid: null,
      studyUuid: null,
      assayUuid: null,
      tableContext: null,
      tableMetaFields: null,
      tableSODARFields: null,
      title: null
    }
  },
  methods: {
    showModal (studyUuid, gridUuid) {
      this.gridUuid = gridUuid
      this.studyUuid = studyUuid
      if (gridUuid !== studyUuid) {
        this.title = 'Assay'
        this.assayUuid = gridUuid
        this.assayMode = true
        this.tableMetaFields = assayMetaFields
        this.tableSODARFields = assaySODARFields
        this.tableContext = this.app.sodarContext.studies[
          this.studyUuid].assays[this.assayUuid]
      } else {
        this.title = 'Study'
        this.assayMode = false
        this.tableMetaFields = studyMetaFields
        this.tableSODARFields = studySODARFields
        this.tableContext = this.app.sodarContext.studies[this.studyUuid]
      }
      this.$refs.tableDetailModal.show()
    },
    hideModal () {
      this.$refs.tableDetailModal.hide()
    }
  }
}
</script>

<style scoped>
</style>
