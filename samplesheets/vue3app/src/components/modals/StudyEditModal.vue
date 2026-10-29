<script setup lang="ts">
import { ref, useTemplateRef } from 'vue'
import {
  BButton,
  BButtonGroup,
  BFormInput,
  BModal,
  BFormTextarea
} from 'bootstrap-vue-next'

import ModalHeader from '@/components/modals/ModalHeader.vue'
import { useAppStore } from '@/stores/appStore.ts'
import { getAjaxRequestInit } from '@/utils/appUtils.ts'
import {
  type GenericResponseBody,
  type SodarContextStudy,
  type StudyEditMeta,
  type StudyEditRequestBody
} from '@/types.ts'
import {
  AJAX_RES_OK,
  EDIT_REGEX_FILE_NAME,
  REQ_POST,
  STUDY_UPDATE_FAIL_PREFIX,
  STUDY_UPDATE_OK_MSG,
  URL_STUDY_EDIT_PREFIX,
  VARIANT_DANGER,
  VARIANT_SUCCESS
} from '@/constants.ts'

// External Data ---------------------------------------------------------------

const appStore = useAppStore()

// Refs ------------------------------------------------------------------------

const fileNameClass = ref<string>('')
const modalRef = useTemplateRef('studyEditModalRef')
const showModal = ref<boolean>(false)
const studyMeta = ref<StudyEditMeta | null>(null)
const updating = ref<boolean>(true)
const valid = ref<boolean>(true)

// Internal Vars ---------------------------------------------------------------

let tableContext: SodarContextStudy
let tableUuid: string

// Helpers ---------------------------------------------------------------------

function enableSubmit () {
  return !updating.value && valid.value
}

function onFileNameInput () {
  const f = studyMeta.value!.fileName.trim()
  if (f === '' ||
      !f.startsWith('s_') ||
      !f.endsWith('.txt') ||
      !EDIT_REGEX_FILE_NAME.test(f)) {
    fileNameClass.value = 'text-danger'
    valid.value = false
  } else {
    fileNameClass.value = ''
    valid.value = true
  }
}

function onIdentifierInput () {
  valid.value = studyMeta.value!.identifier.trim() !== ''
}

// Post study update and handle the results
async function updateStudy () {
  const url = URL_STUDY_EDIT_PREFIX + tableUuid
  const updateBody: StudyEditRequestBody = {
    study_meta: {
      description: studyMeta.value!.description.trim(),
      file_name: studyMeta.value!.fileName.trim(),
      identifier: studyMeta.value!.identifier.trim(),
      title: studyMeta.value!.title.trim(),
    }
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
  tableContext.title = title
  if (studyMeta.value!.title) tableContext.display_name = title
  else tableContext.display_name = identifier
}

// API and Life Cycle ----------------------------------------------------------

function show (uuid: string) {
  tableContext = appStore.sodarContext!.studies[uuid]!
  studyMeta.value = {
    description: tableContext.description,
    fileName: tableContext.file_name,
    identifier: tableContext.identifier,
    title: tableContext.title,
  }
  tableUuid = uuid
  updating.value = false
  valid.value = true // We assume all data must be valid when opening
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
          :modal-ref="modalRef"
          title="Update Study">
      </ModalHeader>
    </template>
    <div id="sodar-ss-study-edit-content">
      <table
          v-if="studyMeta"
          class="table table-borderless w-100 mb-3"
          id="sodar-ss-study-edit-table">
        <tbody>
          <tr>
            <td>Identifier</td>
            <td>
              <BFormInput
                  v-model="studyMeta.identifier"
                  id="sodar-ss-study-input-meta-id"
                  @update:model-value="onIdentifierInput()">
              </BFormInput>
            </td>
          </tr>
          <tr>
            <td>Title</td>
            <td>
              <BFormInput
                  v-model="studyMeta.title"
                  id="sodar-ss-study-input-meta-title">
              </BFormInput>
            </td>
          </tr>
          <tr>
            <td>File Name</td>
            <td>
              <BFormInput
                  v-model="studyMeta.fileName"
                  :class="fileNameClass"
                  id="sodar-ss-study-input-meta-file"
                  @update:model-value="onFileNameInput()">
              </BFormInput>
            </td>
          </tr>
          <tr>
            <td>Description</td>
            <td>
              <BFormTextarea
                  v-model="studyMeta.description"
                  id="sodar-ss-study-input-meta-desc"
                  rows="4">
              </BFormTextarea>
            </td>
          </tr>
        </tbody>
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
  padding-top: 18px;
}
#sodar-ss-study-edit-btn-group {
  padding-right: 12px;
}
</style>
