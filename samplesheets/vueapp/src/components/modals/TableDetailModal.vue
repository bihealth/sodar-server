<template>
  <b-modal
      id="sodar-ss-table-detail-modal" ref="tableDetailModal"
      centered no-fade hide-footer
      size="xl"
      :title="title + ' Details'"
      :static="true">
    <div id="sodar-ss-table-detail-modal-content">
      <div v-if="tableContext" id="sodar-ss-table-detail-modal-container">
        <dl v-for="(val, idx) in tableFields"
            :key="idx"
            class="row pb-0 sodar-ss-table-detail-row">
          <dt class="col-md-3 sodar-ss-table-detail-legend">
            {{ val[0] }}
          </dt>
          <dd v-if="!(['', null].includes(tableContext[val[1]]))"
              class="col-md-9 sodar-ss-table-detail-value">
            {{ tableContext[val[1]] }}
          </dd>
          <dd v-else
              class="col-md-9 sodar-ss-table-detail-value
                     sodar-ss-table-detail-value-empty text-muted">
            N/A
          </dd>
        </dl>
        <dl v-for="(val, key, idx) in tableContext.comments"
            :key="'C' + idx"
            class="row pb-0 sodar-ss-table-detail-row-comment">
          <dt class="col-md-3 sodar-ss-table-detail-legend-comment">
            {{ key }}
            <i class="iconify text-info"
               data-icon="mdi:comment"
               title="Comment">
            </i>
          </dt>
          <dd v-if="!(['', null].includes(val))"
              class="col-md-9 sodar-ss-table-detail-value-comment">
            {{ val }}
          </dd>
          <dd v-else
              class="col-md-9 text-muted sodar-ss-table-detail-value-comment
                     sodar-ss-table-detail-value-comment-empty">
            N/A
          </dd>
        </dl>
      </div>
    </div>
  </b-modal>
</template>

<script>

const studyFields = [
  ['Display Name', 'display_name'],
  ['File Name', 'file_name'],
  ['Identifier', 'identifier'],
  ['Title', 'title'],
  ['Description', 'description'],
  ['Plugin Name', 'plugin_name'],
  ['Plugin Title', 'plugin_title']
]
const assayFields = [
  ['Display Name', 'display_name'],
  ['File Name', 'file_name'],
  ['Measurement Type', 'measurement_type'],
  ['Technology Type', 'technology_type'],
  ['Technology Platform', 'technology_platform'],
  ['Plugin Name', 'plugin_name'],
  ['Plugin Title', 'plugin_title'],
  ['Display Row Links', 'display_row_links']
]

export default {
  name: 'TableDetailModal',
  props: ['app'],
  data () {
    return {
      studyUuid: null,
      assayUuid: null,
      tableContext: null,
      tableFields: null,
      title: null
    }
  },
  methods: {
    showModal (studyUuid, gridUuid) {
      this.studyUuid = studyUuid
      if (gridUuid !== studyUuid) {
        this.title = 'Assay'
        this.assayUuid = gridUuid
        this.tableFields = assayFields
        this.tableContext = this.app.sodarContext.studies[
          this.studyUuid].assays[this.assayUuid]
      } else {
        this.title = 'Study'
        this.tableFields = studyFields
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
