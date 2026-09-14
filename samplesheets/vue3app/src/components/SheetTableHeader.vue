<script setup lang="ts">
import { ref } from 'vue'
import { BButton } from 'bootstrap-vue-next'
import IrodsButtons from '@/components/IrodsButtons.vue'
import IrodsStatsBadge from '@/components/IrodsStatsBadge.vue'
import TableDetailModal from '@/components/modals/TableDetailModal.vue'
import { useAppStore } from '@/stores/appStore.ts'

// External Data ---------------------------------------------------------------

const appStore = useAppStore()
const props = defineProps(['assayMode', 'tableUuid'])

// Refs ------------------------------------------------------------------------

const tableDetailModalComponent = ref<typeof TableDetailModal | null>(null)

// Internal Vars ---------------------------------------------------------------

let tableType
let tableTitle
let tableContext

// Setup -----------------------------------------------------------------------

if (!props.assayMode) {
  tableType = 'study'
  tableTitle = 'Study'
  tableContext = appStore.sodarContext!.studies[props.tableUuid]
} else {
  tableType = 'assay'
  tableTitle = 'Assay'
  tableContext = appStore.sodarContext!.studies[
    appStore.currentStudyUuid]!.assays[props.tableUuid]
}
const tableIdSuffix = tableType + '-' + props.tableUuid

// Helpers ---------------------------------------------------------------------

function getTitleTextClass (): string {
  if (!props.assayMode) return 'text-info'
  return 'text-danger'
}
</script>

<template>
  <!-- Header -->
  <div :class="'row mb-4 sodar-ss-table-header-row sodar-ss-sheet-section-' +
               tableType"
       :id="'sodar-ss-sheet-section-' + tableIdSuffix">
    <div class="col-8 pl-0">
      <h4 :class="'font-weight-bold mb-0 sodar-ss-table-title ' +
                  getTitleTextClass()">
        <i v-if="!assayMode"
           class="iconify"
           data-icon="mdi:folder-table"></i>
        <i v-else class="iconify" data-icon="mdi:table-large"></i>
        {{ tableTitle }}: {{ tableContext!.display_name }}
        <span v-if="appStore.getPerm('edit_sheet') &&
                    tableContext!.plugin_title"
              class="sodar-ss-table-plugin">
          <i :class="'iconify ml-1 ' + getTitleTextClass()"
             data-icon="mdi:puzzle"
             :title="tableContext!.plugin_title">
          </i>
        </span>
        <span v-else-if="appStore.getPerm('edit_sheet') &&
                         !tableContext!.plugin_name &&
                         assayMode"
              class="sodar-ss-table-plugin sodar-ss-table-plugin-no-assay">
          <i class="iconify text-muted ml-1"
             data-icon="mdi:puzzle-remove"
             title="No assay plugin found: displaying default iRODS links">
          </i>
        </span>
      </h4>
    </div>
    <div class="col-4 text-right pr-0">
      <!-- Study iRODS collection stats badge -->
      <span v-if="!assayMode" class="mr-2 sodar-ss-study-title-badge">
        <span v-if="!appStore.editMode && appStore.getPerm('view_files')"
              class="badge-group text-nowrap">
          <span class="badge badge-pill badge-secondary">iRODS</span>
          <IrodsStatsBadge
              v-if="appStore.sodarContext!.irods_status"
              :irods-path="tableContext!.irods_path"
              :irods-status="appStore.sodarContext!.irods_status"
              :project-uuid="appStore.projectUuid">
          </IrodsStatsBadge>
          <!-- TODO: Make this a part of IrodsStatsBadge? -->
          <span v-if="!appStore.sodarContext!.irods_status"
                class="badge badge-pill badge-danger
                       sodar-ss-irods-not-created">
            Not Created
          </span>
        </span>
      </span>
      <!-- Buttons -->
      <span class="text-nowrap">
        <!-- Table detail modal button -->
        <BButton
            class="sodar-list-btn btn-info sodar-ss-btn-table-detail mr-1"
            :title="tableTitle + ' details'"
            @click="tableDetailModalComponent!.show(tableUuid, tableContext)">
          <i class="iconify" data-icon="mdi:information-slab-circle">
          </i>
        </BButton>
        <IrodsButtons
            :edit-mode="appStore.editMode"
            :irods-backend-enabled="appStore.sodarContext!.irods_backend_enabled"
            :irods-path="tableContext!.irods_path"
            :irods-status="appStore.sodarContext!.irods_status"
            :irods-webdav-url="appStore.sodarContext!.irods_webdav_url"
            :notify-cb="appStore.notifyCb"
            :show-file-list="false">
        </IrodsButtons>
      </span>
    </div>
  </div>
  <!-- Modals -->
  <TableDetailModal
      ref="tableDetailModalComponent"
      id="sodar-ss-table-detail-modal-component">
  </TableDetailModal>
</template>

<style scoped>
h4 {
  margin-left: 30px;
  text-indent: -30px;
}
</style>
