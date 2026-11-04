<script setup lang="ts">
import { ref, useTemplateRef } from 'vue'
import { BButton, BButtonGroup, BModal } from 'bootstrap-vue-next'

import ModalHeader from '@/components/modals/include/ModalHeader.vue'
import InvStudyMetaEditSection from '@/components/modals/include/InvStudyMetaEditSection.vue'
import { useAppStore } from '@/stores/appStore.ts'
import { useEditStore } from '@/stores/editStore.ts'
import { getAjaxRequestInit } from '@/utils/appUtils.ts'
import {
  type GenericResponseBody,
  type SodarContextStudy,
  type InvStudyEditMeta,
  type StudyEditRequestBody,
} from '@/types.ts'
import {
  AJAX_RES_OK,
  REQ_POST,
  STUDY_UPDATE_FAIL_PREFIX,
  STUDY_UPDATE_OK_MSG,
  URL_STUDY_UPDATE_PREFIX,
  VARIANT_DANGER,
  VARIANT_SUCCESS
} from '@/constants.ts'

// External Data ---------------------------------------------------------------

const appStore = useAppStore()
const editStore = useEditStore()

// Refs ------------------------------------------------------------------------

const modalRef = useTemplateRef('studyEditModalRef')
const showModal = ref<boolean>(false)
const studyMeta = ref<InvStudyEditMeta | null>(null)
const updating = ref<boolean>(true)

// Internal Vars ---------------------------------------------------------------

let studyFileNames: Array<string> = []
let studyIds: Array<string> = []
let tableContext: SodarContextStudy
let tableUuid: string

// Helpers ---------------------------------------------------------------------

function enableSubmit (): boolean {
  return !updating.value && editStore.modalEditValid
}

// Post study update and handle the results
async function updateStudy () {
  const url = URL_STUDY_UPDATE_PREFIX + tableUuid
  const updateBody: StudyEditRequestBody = {
    study_meta: {
      description: studyMeta.value!.description.trim(),
      file_name: studyMeta.value!.fileName.trim(),
      identifier: studyMeta.value!.identifier.trim(),
      public_release_date: studyMeta.value!.publicReleaseDate.trim(),
      submission_date: studyMeta.value!.submissionDate.trim(),
      title: studyMeta.value!.title.trim(),
    } // TODO: Trim with a oneliner or otherwise ensure sanitization
  }
  const response = await fetch(url, getAjaxRequestInit(REQ_POST, updateBody))
  const resBody: GenericResponseBody = await response.json()
  if (resBody.detail == AJAX_RES_OK) {
    updateTableContext()
    if (appStore.notifyCb) {
      appStore.notifyCb(STUDY_UPDATE_OK_MSG, VARIANT_SUCCESS)
    }
  } else {
    const msg: string = STUDY_UPDATE_FAIL_PREFIX + resBody.detail
    if (appStore.notifyCb) appStore.notifyCb(msg, VARIANT_DANGER)
    console.error(msg)
  }
}

// Update tableContext with edited values
function updateTableContext () {
  const identifier = studyMeta.value!.identifier
  const title = studyMeta.value!.title
  tableContext.description = studyMeta.value!.description
  tableContext.file_name = studyMeta.value!.fileName
  tableContext.identifier = identifier
  tableContext.public_release_date = studyMeta.value!.publicReleaseDate
  tableContext.submission_date = studyMeta.value!.submissionDate
  tableContext.title = title
  if (studyMeta.value!.title) tableContext.display_name = title
  else tableContext.display_name = identifier
}

// API and Life Cycle ----------------------------------------------------------

function show (uuid: string) {
  tableContext = appStore.sodarContext!.studies[uuid]!
  tableUuid = uuid

  // Store info from other studies for uniqueness checks
  studyFileNames = []
  studyIds = []
  for (const [k, v] of Object.entries(appStore.sodarContext!.studies)) {
    if (k !== tableUuid) {
      studyFileNames.push(v.file_name)
      studyIds.push(v.identifier)
    }
  }

  studyMeta.value = {
    description: tableContext.description,
    fileName: tableContext.file_name,
    identifier: tableContext.identifier,
    publicReleaseDate: tableContext.public_release_date,
    submissionDate: tableContext.submission_date,
    title: tableContext.title,
  }
  editStore.modalEditValid = true // Assume all data must be valid when opening
  updating.value = false
  showModal.value = true
}

function hide (update: boolean) {
  if (update) {
    updating.value = true
    try {
      updateStudy()
    } catch (error) {
      const msg: string = `Error updating study: ${error}`
      if (appStore.notifyCb) appStore.notifyCb(msg, VARIANT_DANGER)
      console.error(msg)
    }
  }
  modalRef.value?.hide()
}

defineExpose({ show })
</script>

<template>
  <BModal
      id="sodar-ss-study-edit-modal"
      ref="studyEditModalRef"
      v-model="showModal"
      size="lg"
      centered no-footer no-animation teleport-disabled>
    <template #header>
      <ModalHeader
          :hide-close-button="true"
          icon="mdi:folder-table"
          icon-variant="info"
          :modal-ref="modalRef"
          title="Update Study">
      </ModalHeader>
    </template>
    <div id="sodar-ss-study-edit-content">
      <table
          v-if="studyMeta"
          class="table table-borderless w-100 mb-3"
          id="sodar-ss-study-edit-table">
        <InvStudyMetaEditSection
            :file-names="studyFileNames"
            :identifiers="studyIds"
            :metadata="studyMeta"
            :study-mode="true">
        </InvStudyMetaEditSection>
      </table>
    </div>
    <div id="sodar-ss-study-edit-controls">
      <BButtonGroup
          class="pull-right"
          id="sodar-ss-study-edit-btn-group">
        <BButton
            variant="secondary"
            id="sodar-ss-study-edit-btn-cancel"
            :disabled="updating"
            @click="hide(false)">
          <i class="iconify" data-icon="mdi:close-thick"></i> Cancel
        </BButton>
        <BButton
            variant="primary"
            id="sodar-ss-study-edit-btn-update"
            ref="updateBtn"
            :disabled="!enableSubmit()"
            @click="hide(true)">
          <i class="iconify" data-icon="mdi:check-bold"></i> Update
        </BButton>
      </BButtonGroup>
    </div>
  </BModal>
</template>

<style scoped>
table#sodar-ss-study-edit-table tbody td:first-child {
  width: 100px;
  max-width: 250px;
  vertical-align: top;
  white-space: nowrap;
  padding-top: 20px;
}
#sodar-ss-study-edit-btn-group {
  padding-right: 12px;
}
</style>
