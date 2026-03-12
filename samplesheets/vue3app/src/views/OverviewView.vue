<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import IrodsStatsBadge from '@/components/IrodsStatsBadge.vue'
import TableDetailList from '@/components/TableDetailList.vue'
import TableDetailListRow from '@/components/TableDetailListRow.vue'
import {
  ASSAY_META_FIELDS,
  ASSAY_SODAR_FIELDS,
  INV_META_FIELDS,
  STUDY_META_FIELDS,
  STUDY_SODAR_FIELDS,
  SHEET_STATS,
} from '@/constants'
import {
  useAppStore,
  type SodarContextInvestigation
} from '@/stores/appStore.ts'

const router = useRouter()
const appStore = useAppStore()

const isaMetaTitle = 'ISA-Tab metadata'
const sodarMetaTitle = 'SODAR metadata'

if (!appStore.overviewActive) appStore.overviewActive = true
const investigation = ref<SodarContextInvestigation>(
  appStore.sodarContext?.investigation as SodarContextInvestigation)

// Navigate to study and optionally assay
function handleNavigation (studyUuid: string, assayUuid: string | null) {
  // NOTE: Contains repetition from handleStudyNavigation() in PageHeader, ideas
  //       on how to nicely combine these?
  appStore.overviewActive = false
  appStore.gridsLoaded = false
  appStore.currentStudyUuid = studyUuid
  if (assayUuid) {
    router.push({
      name: 'assay',
      params: { studyUuid: studyUuid, assayUuid: assayUuid },
      replace: true
    })
  } else {
    router.push({
      name: 'study',
      params: { studyUuid: studyUuid },
      replace: true
    })
    const anchorElem = document.getElementsByClassName('sodar-app-container')[0]
    if (anchorElem) anchorElem.scrollTop = 0
  }
}

watch(() => appStore.sodarContext, (newContext) => {
  if (newContext && newContext.investigation) {
    investigation.value = newContext.investigation as SodarContextInvestigation
  }
})
</script>

<template>
  <div v-if="investigation">
    <!-- Investigation -->
    <div class="card"
         id="sodar-ss-overview-investigation">
      <div class="card-header">
        <h4>
          <i class="iconify"
             data-icon="mdi:folder-multiple"
             title="Investigation">
          </i>
          Investigation: {{ investigation.title }}
        </h4>
      </div>
      <div class="card-body px-1 pt-3 pb-2">
        <TableDetailListRow
            legend="File Name"
            :value="appStore.sodarContext?.inv_file_name"
            icon="mdi:file"
            icon-class=""
            :title="isaMetaTitle"
            row-class="sodar-ss-table-detail-row-meta">
        </TableDetailListRow>
        <TableDetailListRow
            v-for="(val, idx) in INV_META_FIELDS"
            :key="'inv-meta' + idx"
            :legend="val[0]"
            :value="investigation[val[1] as keyof SodarContextInvestigation]"
            icon="mdi:file"
            icon-class=""
            :title="isaMetaTitle"
            row-class="sodar-ss-table-detail-row-meta">
        </TableDetailListRow>
        <TableDetailListRow
            v-for="(val, key) in investigation.comments"
            :key="'inv-comment-' + key"
            :legend="key"
            :value="val"
            icon="mdi:comment"
            icon-class="text-primary"
            title="ISA-Tab comment"
            row-class="sodar-ss-table-detail-row-comment">
        </TableDetailListRow>
        <TableDetailListRow
            legend="Parser Version"
            :value="appStore.sodarContext?.parser_version"
            icon="mdi:code-braces"
            icon-class="text-secondary"
            :title="sodarMetaTitle"
            row-class="sodar-ss-table-detail-row-sodar">
        </TableDetailListRow>
        <TableDetailListRow
            legend="Configuration"
            :value="appStore.sodarContext?.configuration"
            icon="mdi:code-braces"
            icon-class="text-secondary"
            :title="sodarMetaTitle"
            row-class="sodar-ss-table-detail-row-sodar">
        </TableDetailListRow>
        <!-- TODO: Enable adding custom content in TableDetailListRow -->
        <dl class="row pb-0 sodar-ss-table-detail-row"
            id="sodar-ss-inv-detail-irods">
          <dt class="col-md-3 sodar-ss-table-detail-legend">
            <i class="iconify text-muted" data-icon="mdi:database"></i>
            iRODS Repository
          </dt>
          <dd class="col-md-9 sodar-ss-table-detail-value">
            <IrodsStatsBadge
                v-if="appStore.sodarContext!.irods_status"
                :irods-path="appStore.sodarContext!.irods_path"
                :irods-status="appStore.sodarContext!.irods_status"
                :project-uuid="appStore.projectUuid">
            </IrodsStatsBadge>
            <span v-if="!appStore.sodarContext!.irods_status"
                class="badge badge-pill badge-danger">
              Not Created
            </span>
          </dd>
        </dl>
      </div>
    </div>
    <!-- Study -->
    <span v-for="(studyContext, studyUuid) in appStore.sodarContext?.studies"
          :key="'study-' + studyUuid">
      <div class="card sodar-ss-overview-study"
           :id="'sodar-ss-overview-study-' + studyUuid">
        <div class="card-header">
          <h4>
            <i class="iconify text-info"
               data-icon="mdi:folder-table"
               title="Study">
            </i>
            Study:
            <a class="sodar-ss-overview-header-link"
               @click="handleNavigation(studyUuid as string, null)">
              {{ studyContext['display_name'] }}
            </a>
          </h4>
        </div>
        <div class="card-body px-1 pt-3 pb-2">
          <TableDetailList
             :assay-mode="false"
             :table-context="studyContext"
             :table-meta-fields="STUDY_META_FIELDS"
             :table-sodar-fields="STUDY_SODAR_FIELDS"
             :table-uuid="studyUuid">
          </TableDetailList>
        </div>
      </div>
      <!-- Assay -->
      <span v-for="(assayContext, assayUuid) in studyContext['assays']"
            :key="'assay-' + assayUuid">
        <div class="card sodar-ss-overview-assay"
             :id="'sodar-ss-overview-assay-' + assayUuid">
          <div class="card-header">
            <h4>
              <i class="iconify text-danger"
                 data-icon="mdi:table-large"
                 title="Assay">
              </i>
              Assay:
              <a class="sodar-ss-overview-header-link"
               @click="handleNavigation(
                 studyUuid as string, assayUuid as string)">
              {{ assayContext['display_name'] }}
            </a>
            </h4>
          </div>
          <div class="card-body px-1 pt-3 pb-2">
            <TableDetailList
                :assay-mode="true"
                :table-context="assayContext"
                :table-meta-fields="ASSAY_META_FIELDS"
                :table-sodar-fields="ASSAY_SODAR_FIELDS"
                :table-uuid="assayUuid">
            </TableDetailList>
          </div>
        </div>
      </span> <!-- Assay -->
    </span> <!-- Study -->
    <!-- Statistics -->
    <div class="card" id="sodar-ss-overview-stats">
      <div class="card-header">
        <h4>Statistics</h4>
      </div>
      <div class="card-body p-0">
        <div class="table-responsive mb-0">
          <table class="table sodar-card-table">
            <thead>
              <tr>
                <th v-for="(v, k) in SHEET_STATS"
                    :key="k"
                    class="text-nowrap text-center">
                  {{ v[0] }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td v-for="(v, k) in SHEET_STATS"
                    :key="k"
                    class="text-center">
                  {{ appStore.getStat(v[1]!) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
a.sodar-ss-overview-header-link {
  color: #000;
}
h4 {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
