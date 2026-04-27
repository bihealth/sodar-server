<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { BButton, BNav, BDropdown, BDropdownItem } from 'bootstrap-vue-next'

import WinExportModal from '@/components/modals/WinExportModal.vue'
import { useAppStore } from '@/stores/appStore.ts'
import { useEditStore } from '@/stores/editStore.ts'
import { useTableStore } from '@/stores/tableStore.ts'
import {
  EDIT_BADGE_DEFAULT_LABEL,
  EDIT_BADGE_SAVED_LABEL,
  EDIT_BADGE_UNSAVED_LABEL,
  EDIT_MODE_EXIT_MSG,
  EDIT_MODE_SAVE_MSG,
  EDIT_MODE_UNSAVED_MSG,
  STUDY_NAV_DROPDOWN_LEN,
  STUDY_NAV_TAB_LEN
} from '@/constants.ts'

const route = useRoute()
const router = useRouter()
const appStore = useAppStore()
const editStore = useEditStore()
const tableStore = useTableStore()

const winExportCompRef = ref<typeof WinExportModal | null>(null)

// TODO: Move to common utils?
function truncate (s: string, maxLen: number): string {
  if (s.length > maxLen) return s.substring(0, maxLen) + '...'
  return s
}

function isStudyActive (studyUuid: string): boolean {
  return appStore.currentStudyUuid === studyUuid && !appStore.overviewActive
}

function handleStudyNavigation (studyUuid: string, assayUuid: string | null) {
  appStore.overviewActive = false
  // Scroll to study or assay in current view
  if (studyUuid === appStore.currentStudyUuid &&
      ['study', 'assay'].includes(route.name!.toString())) {
    if (assayUuid) {
      const anchorId = 'assay-anchor-' + assayUuid
      const anchorElem = document.getElementById(anchorId)
      if (anchorElem) anchorElem.scrollIntoView()
    } else {
      const anchorElem = document.getElementsByClassName(
        'sodar-app-container')[0]
      if (anchorElem) anchorElem.scrollTop = 0
    }
  } else { // Navigate to StudyView
      // Force reloading study
      // NOTE: We force reload because modal template refs become inaccessible
      //       when navigating back from Overview with the same study UUID. If
      //       you have a better idea on how to handle this, PR:s are welcome :)
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
    }
  }
}

function handleOverviewNavigation () {
  appStore.overviewActive = true
  router.push({ name: 'overview', replace: true })
}

function toggleEditMode () {
  appStore.editMode = !appStore.editMode
  if (appStore.editMode) { // Edit mode
    // Navigate to default study if needed
    if (appStore.overviewActive || !appStore.currentStudyUuid) {
      appStore.currentStudyUuid = Object.keys(
        appStore.sodarContext!.studies)[0] as string
      handleStudyNavigation(appStore.currentStudyUuid, null)
    }
  } else { // Browsing mode
    // TODO: Call finish editing handler once implemented
    // TODO: Update selectEnabled
    if (appStore.currentStudyUuid) {
      handleStudyNavigation(
        appStore.currentStudyUuid, appStore.currentAssayUuid)
    }
  }
  // NOTE: editDataUpdated was originally reset here, but that should not be
  //       needed anymore with the editStore reset. Ensure this is correct.
}

function getFinishEditTitle () {
  if (!editStore.unsavedRow) {
    let title = EDIT_MODE_EXIT_MSG
    if (!editStore.versionSaved && editStore.editDataUpdated) {
      title += EDIT_MODE_SAVE_MSG
    }
    return title
  } else return EDIT_MODE_UNSAVED_MSG
}
</script>

<template>
  <div class="row sodar-subtitle-container bg-white sticky-top mb-4"
       id="sodar-ss-subtitle">
    <div class="col"
         id="sodar-ss-subtitle-col-title">
      <h3 class="text-nowrap">
        <i class="iconify" data-icon="mdi:flask" /> Sample Sheets
      </h3>
    </div>
    <!-- Study navigation -->
    <div class="col"
         id="sodar-ss-subtitle-col-study-nav">
      <BNav pills v-if="appStore.sheetsAvailable"
            class="sodar-ss-nav me-0"
            id="sodar-ss-nav-tabs">
        <!-- NOTE: bootstrap-vue-next BNavItem fails if using @click -->
        <BButton
            v-for="(studyInfo, studyUuid) in appStore.sodarContext!.studies"
            :key="studyUuid"
            variant="light"
            class="sodar-ss-nav-tab sodar-ss-nav-tab-study mr-2"
            :id="'sodar-ss-nav-tab-study-' + studyUuid"
            @click="handleStudyNavigation(studyUuid as string, null)"
            :active="isStudyActive(studyUuid as string)"
            :disabled="appStore.gridsBusy">
          <i class="iconify" data-icon="mdi:folder-table"></i>
          {{ truncate(studyInfo.display_name, STUDY_NAV_TAB_LEN) }}
        </BButton>
        <BButton
            variant="light"
            class="sodar-ss-nav-tab"
            id="sodar-ss-nav-tab-overview"
            @click="handleOverviewNavigation()"
            :active="appStore.overviewActive"
            :disabled="appStore.gridsBusy || appStore.editMode">
          <i class="iconify" data-icon="mdi:sitemap"></i> Overview
        </BButton>
      </BNav>
    </div>
    <div class="col d-flex justify-content-end"
         id="sodar-ss-subtitle-right">
      <!-- Edit mode badge -->
      <!-- TODO: Implement editor help modal showing -->
      <div class="mr-1"
           id="sodar-ss-subtitle-badge-container">
      <span v-if="appStore.editMode"
            class="badge badge-pill badge-info mr-2"
            id="sodar-ss-badge-edit">
        <a id="sodar-ss-link-edit-help"
           title="Editor status">
          <i class="iconify mr-1" data-icon="mdi:lead-pencil"></i>
          <span v-if="editStore.unsavedData || editStore.unsavedRow">
            {{ EDIT_BADGE_UNSAVED_LABEL }}
          </span>
          <span v-else-if="editStore.editDataUpdated">
            {{ EDIT_BADGE_SAVED_LABEL }}
          </span>
          <span v-else>{{ EDIT_BADGE_DEFAULT_LABEL }}</span>
        </a>
      </span>
        </div>
      <!-- Nav dropdown -->
      <BDropdown
          v-if="appStore.sheetsAvailable"
          class="mr-1"
          id="sodar-ss-nav-dropdown"
          placement="bottom-end"
          variant="success"
          :disabled="appStore.gridsBusy">
        <template #button-content>
          <i class="iconify" data-icon="mdi:menu"></i>
        </template>
        <span
            v-for="(studyInfo, studyUuid) in appStore.sodarContext!.studies"
            :key="studyUuid">
          <BDropdownItem
              class="sodar-ss-nav-item"
              :id="'sodar-ss-nav-study-' + studyUuid"
              @click="handleStudyNavigation(studyUuid as string, null)">
            <i class="iconify text-info" data-icon="mdi:folder-table"></i>
            {{ truncate(studyInfo.display_name, STUDY_NAV_DROPDOWN_LEN) }}
          </BDropdownItem>
          <BDropdownItem
              v-for="(assayInfo, assayUuid) in studyInfo.assays"
              :key="assayUuid"
              class="sodar-ss-nav-item"
              :id="'sodar-ss-nav-assay-' + assayUuid"
              @click="handleStudyNavigation(
                studyUuid as string, assayUuid as string)">
            <i class="iconify text-danger ml-3" data-icon="mdi:table-large"></i>
            {{ assayInfo.display_name }}
          </BDropdownItem>
        </span>
        <BDropdownItem
            class="sodar-ss-nav-item"
            id="sodar-ss-nav-overview"
            @click="handleOverviewNavigation()"
            :disabled="appStore.editMode">
          <i class="iconify" data-icon="mdi:sitemap"></i> Overview
        </BDropdownItem>
      </BDropdown>
      <!-- TODO: Add save version button -->
      <!-- Operations dropdown -->
      <BDropdown
          v-if="!appStore.editMode"
          id="sodar-ss-op-dropdown"
          text="Sheet Operations"
          variant="primary"
          placement="bottom-end"
          :disabled="appStore.gridsBusy ||
                     !(appStore.sheetsAvailable ||
                     appStore.getPerm('edit_sheet'))">
        <BDropdownItem
            v-if="appStore.sodarContext &&
                  appStore.sodarContext.sheet_sync_enabled &&
                  appStore.getPerm('edit_sheet')"
            class="sodar-ss-op-item"
            id="sodar-ss-op-item-sync"
            :href="'sync/' + appStore.projectUuid">
          <i class="iconify" data-icon="mdi:table-refresh"></i>
          Sync Sheets
        </BDropdownItem>
        <BDropdownItem
            v-if="appStore.sodarContext &&
                  !appStore.sheetsAvailable &&
                  !appStore.sodarContext.sheet_sync_enabled &&
                  appStore.getPerm('edit_sheet')"
            class="sodar-ss-op-item"
            id="sodar-ss-op-item-import"
            :href="'import/' + appStore.projectUuid">
          <i class="iconify" data-icon="mdi:upload"></i> Import ISA-Tab
        </BDropdownItem>
        <BDropdownItem
            v-if="appStore.sodarContext &&
                  !appStore.sheetsAvailable &&
                  !appStore.sodarContext.sheet_sync_enabled &&
                  appStore.getPerm('edit_sheet')"
            class="sodar-ss-op-item"
            id="sodar-ss-op-item-create"
            :href="'template/select/' + appStore.projectUuid">
          <i class="iconify" data-icon="mdi:auto-fix"></i> Create from Template
        </BDropdownItem>
        <BDropdownItem
            v-if="appStore.sodarContext &&
                  appStore.sheetsAvailable &&
                  !appStore.sodarContext.sheet_sync_enabled &&
                  appStore.getPerm('edit_sheet')"
            class="sodar-ss-op-item"
            id="sodar-ss-op-item-edit"
            @click="toggleEditMode()">
          <i class="iconify" data-icon="mdi:lead-pencil"></i> Edit Sheets
        </BDropdownItem>
        <BDropdownItem
            v-if="appStore.sodarContext &&
                  appStore.sheetsAvailable &&
                  appStore.getPerm('edit_sheet')"
            class="sodar-ss-op-item"
            id="sodar-ss-op-item-warnings"
            :to="{ name: 'warnings' }"
            :disabled="!appStore.sodarContext.parser_warnings">
          <i class="iconify" data-icon="mdi:alert"></i> View Parser Warnings
        </BDropdownItem>
        <BDropdownItem
            v-if="appStore.sodarContext &&
                  appStore.sheetsAvailable &&
                  appStore.sodarContext.irods_status &&
                  appStore.getPerm('update_cache')"
            class="sodar-ss-op-item"
            id="sodar-ss-op-item-cache"
            :href="'cache/update/' + appStore.projectUuid">
          <i class="iconify" data-icon="mdi:database-refresh"></i>
          Update Sheet Cache
        </BDropdownItem>
        <BDropdownItem
            v-if="appStore.sodarContext &&
                  appStore.sheetsAvailable &&
                  !appStore.sodarContext.sheet_sync_enabled &&
                  appStore.getPerm('edit_sheet')"
            class="sodar-ss-op-item"
            id="sodar-ss-op-item-replace"
            :href="'import/' + appStore.projectUuid">
          <i class="iconify" data-icon="mdi:upload"></i> Replace ISA-Tab
        </BDropdownItem>
        <BDropdownItem
            v-if="appStore.sheetsAvailable && !appStore.windowsOs"
            class="sodar-ss-op-item"
            id="sodar-ss-op-item-export"
            :href="'export/isa/' + appStore.projectUuid">
          <i class="iconify" data-icon="mdi:download"></i> Export ISA-Tab
        </BDropdownItem>
        <BDropdownItem
            v-else-if="appStore.sheetsAvailable && appStore.windowsOs"
            class="sodar-ss-op-item"
            id="sodar-ss-op-item-export-win"
            @click="winExportCompRef!.show()">
          <i class="iconify" data-icon="mdi:download"></i> Export ISA-Tab
        </BDropdownItem>
        <BDropdownItem
            v-if="appStore.sodarContext &&
                  appStore.sheetsAvailable &&
                  !tableStore.renderError &&
                  appStore.getPerm('create_colls')"
            class="sodar-ss-op-item"
            id="sodar-ss-op-item-irods"
            :href="'collections/' + appStore.projectUuid">
          <span v-if="appStore.sodarContext.irods_status">
            <i class="iconify" data-icon="mdi:database-refresh"></i>
            Update iRODS Collections
          </span>
          <span v-else>
            <i class="iconify" data-icon="mdi:database-plus"></i>
            Create iRODS Collections
          </span>
        </BDropdownItem>
        <BDropdownItem
            v-if="appStore.sodarContext &&
                  appStore.sheetsAvailable &&
                  !appStore.sodarContext.sheet_sync_enabled"
            class="sodar-ss-op-item"
            id="sodar-ss-op-item-versions"
            :href="'versions/' + appStore.projectUuid">
          <i class="iconify" data-icon="mdi:table-search"></i> Sheet Versions
        </BDropdownItem>
        <BDropdownItem
            v-if="appStore.sodarContext &&
                  appStore.sheetsAvailable &&
                  appStore.sodarContext.irods_status &&
                  appStore.getPerm('view_tickets')"
            class="sodar-ss-op-item"
            id="sodar-ss-op-item-tickets"
            :href="'irods/tickets/' + appStore.projectUuid">
          <i class="iconify" data-icon="mdi:ticket"></i> iRODS Access Tickets
        </BDropdownItem>
        <BDropdownItem
            v-if="appStore.sodarContext &&
                  appStore.sheetsAvailable &&
                  appStore.sodarContext.irods_status &&
                  appStore.getPerm('edit_sheet')"
            class="sodar-ss-op-item"
            id="sodar-ss-op-item-requests"
            :href="'irods/requests/' + appStore.projectUuid">
          <i class="iconify" data-icon="mdi:trash-can"></i>
          iRODS Delete Requests
        </BDropdownItem>
        <BDropdownItem
            v-if="appStore.sodarContext &&
                  appStore.sheetsAvailable &&
                  !appStore.sodarContext.sheet_sync_enabled &&
                  appStore.getPerm('delete_sheet')"
            class="sodar-ss-op-item"
            id="sodar-ss-op-item-delete"
            variant="danger"
            :href="'delete/' + appStore.projectUuid">
          <i class="iconify" data-icon="mdi:close-thick"></i> Delete Sheets
          <span v-if="appStore.sodarContext.irods_status">and Data</span>
        </BDropdownItem>
      </BDropdown>
       <!-- Finish editing button (replace op dropdown in edit mode) -->
      <BButton
          v-if="appStore.editMode"
          variant="primary"
          class="text-left"
          id="sodar-ss-btn-edit-finish"
          :title="getFinishEditTitle()"
          @click="toggleEditMode()"
          :disabled="editStore.unsavedRow !== null">
        Finish editing
        <span class="pull-right">
          <i class="iconify" data-icon="mdi:check-bold"></i>
        </span>
      </BButton>
    </div>
  </div>
  <WinExportModal
      id="sodar-ss-win-export-modal-component"
      ref="winExportCompRef"
      :project-uuid="appStore.projectUuid">
  </WinExportModal>
</template>

<style scoped>
/* NOTE: See vue3app.css for further modifications */
/* Subtitle container elements behave differenly on Bootstrap v5 */
div.sodar-subtitle-container {
  background-color: #fff !important;
  margin-left: 0;
  margin-right: 0;
}
div#sodar-ss-subtitle-col-title {
  padding-left: 0;
  max-width: 240px;
}
div#sodar-ss-subtitle-right {
  padding-right: 0;
}
.sodar-ss-nav-tab {
  border: 0 !important;
}
#sodar-ss-subtitle-badge-container {
  margin-top: 6px;
}
#sodar-ss-btn-edit-finish {
  width: 163px;
}
/* Hide navbar if browser is too narrow */
@media screen and (max-width: 1300px) {
  div#sodar-ss-subtitle-col-study-nav {
    display: none;
  }
}
</style>
