<template>
  <span>
    <div class="card" id="sodar-ss-overview-investigation">
      <div class="card-header">
        <h4>Investigation Details</h4>
      </div>
      <div class="card-body">
        <list-row :legend="'Identifier'"
                  :value="sodarContext.investigation.identifier">
        </list-row>
        <list-row :legend="'Title'"
                  :value="sodarContext.investigation.title">
        </list-row>
        <list-row :legend="'Description'"
                  :value="sodarContext.investigation.description">
        </list-row>
        <list-row :legend="'Parser Version'"
                  :value="sodarContext.parser_version">
        </list-row>
        <dl class="row pb-0">
          <dt class="col-md-3">Configuration</dt>
          <dd class="col-md-9">
            <span v-if="sodarContext.configuration"
                  class="badge badge-pill badge-info">
              {{ sodarContext.configuration }}
            </span>
            <span v-else
                  class="badge badge-pill badge-danger">
              Unknown
            </span>
          </dd>
        </dl>
        <dl v-if="sodarContext.perms.view_files"
            class="row pb-0" id="sodar-ss-overview-irods">
          <dt class="col-md-3">iRODS Repository</dt>
          <dd class="col-md-9">
            <span v-if="sodarContext.irods_status">
              <irods-stats-badge
                ref="invStatsBadge"
                :projectUuid="sodarContext.project_uuid"
                :irodsStatus="sodarContext.irods_status"
                :irodsPath="sodarContext.irods_path">
              </irods-stats-badge>
            </span>
            <span v-else class="badge badge-pill badge-danger">
              Not Created
            </span>
          </dd>
        </dl>
        <span v-for="(val, key, index) in
                     sodarContext.investigation.comments"
              :key="index">
          <list-row :legend="key" :value="val"></list-row>
        </span>
      </div>
    </div>

    <div v-for="(studyInfo, studyUuid, index) in sodarContext.studies"
         :key="index"
         class="card sodar-ss-overview-study"
         :id="'sodar-ss-overview-study-' + studyUuid">
      <div class="card-header">
        <h4>Study Details: {{ studyInfo.display_name }}</h4>
      </div>
      <div class="card-body">
        <list-row :legend="'Identifier'"
                  :value="studyInfo.identifier">
        </list-row>
        <list-row :legend="'Title'"
                  :value="studyInfo.display_name">
        </list-row>
        <list-row :legend="'Description'"
                  :value="studyInfo.description">
        </list-row>
        <span v-for="(val, key, index) in studyInfo.comments"
              :key="index">
          <list-row :legend="key" :value="val"></list-row>
        </span>
      </div>
    </div>

    <div class="card" id="sodar-ss-overview-stats">
      <div class="card-header">
        <h4>Statistics</h4>
      </div>
      <div class="card-body p-0">
        <div class="table-responsive mb-0">
          <table class="table sodar-card-table">
            <thead>
              <tr>
                <th>Studies</th>
                <th>Assays</th>
                <th>Protocols</th>
                <th>Processes</th>
                <th>Sources</th>
                <th>Materials</th>
                <th>Samples</th>
                <th>Data&nbsp;Files</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>{{ sodarContext.sheet_stats.study_count }}</td>
                <td>{{ sodarContext.sheet_stats.assay_count }}</td>
                <td>{{ sodarContext.sheet_stats.protocol_count }}</td>
                <td>{{ sodarContext.sheet_stats.process_count }}</td>
                <td>{{ sodarContext.sheet_stats.source_count }}</td>
                <td>{{ sodarContext.sheet_stats.material_count }}</td>
                <td>{{ sodarContext.sheet_stats.sample_count }}</td>
                <td>{{ sodarContext.sheet_stats.data_count }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </span>
</template>

<script>
import ListRow from './ListRow.vue'
import IrodsStatsBadge from './IrodsStatsBadge.vue'

export default {
  name: 'Overview',
  components: { ListRow, IrodsStatsBadge },
  props: ['sodarContext'],
  mounted () {
    if (this.$refs.invStatsBadge) {
      this.$refs.invStatsBadge.updateStats()
    }
  }
}
</script>

<style scoped>
</style>
