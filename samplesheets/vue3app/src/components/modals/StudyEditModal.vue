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
import { type SodarContextStudy, type StudyEditMeta } from '@/types.ts'
import { STUDY_UPDATE_OK_MSG, VARIANT_SUCCESS } from '@/constants.ts'

// External Data ---------------------------------------------------------------

const appStore = useAppStore()

// Refs ------------------------------------------------------------------------

const modalRef = useTemplateRef('studyEditModalRef')
const showModal = ref<boolean>(false)
const studyMeta = ref<StudyEditMeta | null>(null)

// Internal Vars ---------------------------------------------------------------

let tableContext: SodarContextStudy
let tableUuid: string

// Helpers ---------------------------------------------------------------------

// TODO: Add validation
// TODO: 1. Identifier can't be empty and must be unique within the inv
// TODO: 2. File name must be unique within study and start with "s_"
// TODO: More?

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

function show (uuid: string, context: SodarContextStudy) {
  studyMeta.value = {
    description: context.description,
    fileName: context.file_name,
    identifier: context.identifier,
    title: context.title,
  }
  tableContext = context
  tableUuid = uuid
  showModal.value = true
}

function hide (update: boolean) {
  if (update) {
    // TODO: If update, call Ajax view
    // TODO: Only update context if Ajax call was successful
    updateTableContext()
    if (appStore.notifyCb) {
      appStore.notifyCb(STUDY_UPDATE_OK_MSG, VARIANT_SUCCESS)
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
                  id="sodar-ss-study-input-meta-id">
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
                  id="sodar-ss-study-input-meta-file">
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
            @click="hide(false)">
          <i class="iconify" data-icon="mdi:close-thick"></i> Cancel
        </BButton>
        <BButton
            variant="primary"
            id="sodar-ss-study-edit-btn-update"
            ref="updateBtn"
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
