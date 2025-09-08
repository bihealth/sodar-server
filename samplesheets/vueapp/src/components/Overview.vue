<template>
  <span>
    <div class="card" id="sodar-ss-overview-investigation">
      <div class="card-header">
        <h4>
          <i class="iconify"
               data-icon="mdi:folder-multiple"
               title="Investigation">
            </i>
          Investigation: {{ sodarContext.investigation.title }}
        </h4>
      </div>
      <div class="card-body">
        <table-detail-list-row
            legend="File Name"
            :value="sodarContext.inv_file_name"
            icon="mdi:file"
            icon-class=""
            :title="isaMetaTitle"
            row-class="sodar-ss-table-detail-row-meta">
        </table-detail-list-row>
        <table-detail-list-row
            v-for="(val, idx) in invMetaFields"
            :key="'inv-meta' + idx"
            :legend="val[0]"
            :value="sodarContext.investigation[val[1]]"
            icon="mdi:file"
            icon-class=""
            :title="isaMetaTitle"
            row-class="sodar-ss-table-detail-row-meta">
        </table-detail-list-row>
        <table-detail-list-row
            v-for="(val, key, idx) in sodarContext.investigation.comments"
            :key="'inv-comment' + idx"
            :legend="key"
            :value="val"
            icon="mdi:comment"
            icon-class="text-primary"
            title="ISA-Tab comment"
            row-class="sodar-ss-table-detail-row-comment">
        </table-detail-list-row>
        <table-detail-list-row
            legend="Parser Version"
            :value="sodarContext.parser_version"
            icon="mdi:code-braces"
            icon-class="text-secondary"
            :title="sodarMetaTitle"
            row-class="sodar-ss-table-detail-row-sodar">
        </table-detail-list-row>
        <table-detail-list-row
            legend="Configuration"
            :value="sodarContext.configuration"
            icon="mdi:code-braces"
            icon-class="text-secondary"
            :title="sodarMetaTitle"
            row-class="sodar-ss-table-detail-row-sodar">
        </table-detail-list-row>
        <dl v-if="sodarContext.perms.view_files"
            class="row pb-0" id="sodar-ss-overview-irods">
          <dt class="col-md-3">
            <i class="iconify text-secondary"
               data-icon="mdi:database"
               title="iRODS information">
            </i>
            iRODS Repository
          </dt>
          <dd class="col-md-9 pl-2">
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
      </div>
    </div>

    <span v-for="(studyContext, studyUuid, studyIdx) in sodarContext.studies"
          :key="'study' + studyIdx">
      <div class="card sodar-ss-overview-study"
           :id="'sodar-ss-overview-study-' + studyUuid">
        <div class="card-header">
          <h4>
            <i class="iconify text-info"
               data-icon="mdi:folder-table"
               title="Study">
            </i>
            Study:
            <a href="#"
               class="sodar-ss-overview-header-link"
               @click="handleNavCallback(studyUuid)">
              {{ studyContext.display_name }}
            </a>
          </h4>
        </div>
        <div class="card-body">
          <table-detail-list
            :assay-mode="false"
            :table-context="studyContext"
            :table-meta-fields="studyMetaFields"
            :table-sodar-fields="studySODARFields">
          </table-detail-list>
        </div>
      </div>
      <span v-for="(assayContext, assayUuid, assayIdx) in studyContext.assays"
            :key="'assay' + assayIdx">
        <div class="card sodar-ss-overview-assay"
           :id="'sodar-ss-overview-assay-' + assayUuid">
        <div class="card-header">
          <h4>
            <i class="iconify text-danger"
               data-icon="mdi:table-large"
               title="Assay">
            </i>
            Assay:
            <a href="#"
               class="sodar-ss-overview-header-link"
               @click="handleNavCallback(studyUuid, assayUuid)">
              {{ assayContext.display_name }}
            </a>
          </h4>
        </div>
        <div class="card-body">
          <table-detail-list
            :assay-mode="true"
            :table-context="assayContext"
            :table-meta-fields="assayMetaFields"
            :table-sodar-fields="assaySODARFields">
          </table-detail-list>
        </div>
      </div>
      </span> <!-- Assays in study -->
    </span> <!-- Studies -->

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
import TableDetailListRow from './TableDetailListRow.vue'
import IrodsStatsBadge from './IrodsStatsBadge.vue'
import TableDetailList from './TableDetailList.vue'
import {
  invMetaFields,
  studyMetaFields,
  studySODARFields,
  assayMetaFields,
  assaySODARFields
} from '@/constants'

export default {
  name: 'Overview',
  components: { TableDetailListRow, IrodsStatsBadge, TableDetailList },
  props: [
    'sodarContext',
    'handleNavCallback'
  ],
  data () {
    return {
      invMetaFields: invMetaFields,
      studyMetaFields: studyMetaFields,
      studySODARFields: studySODARFields,
      assayMetaFields: assayMetaFields,
      assaySODARFields: assaySODARFields,
      isaMetaTitle: 'ISA-Tab metadata',
      sodarMetaTitle: 'SODAR metadata'
    }
  },
  mounted () {
    if (this.$refs.invStatsBadge) {
      this.$refs.invStatsBadge.updateStats()
    }
  }
}
</script>

<style scoped>
a.sodar-ss-overview-header-link {
  color: #000;
}
</style>
