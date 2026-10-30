<script setup lang="ts">
import { ref, useTemplateRef } from 'vue'
import { BButton, BButtonGroup, BFormInput, BModal } from 'bootstrap-vue-next'

import ModalHeader from '@/components/modals/ModalHeader.vue'
import { useAppStore } from '@/stores/appStore.ts'
import { type AssayEditMeta, type SodarContextAssay } from '@/types.ts'
import { EDIT_REGEX_FILE_NAME } from '@/constants.ts'

// Constants -------------------------------------------------------------------

const INVALID_CLASS = 'text-danger'

// External Data ---------------------------------------------------------------

const appStore = useAppStore()

// Refs ------------------------------------------------------------------------

const assayMeta = ref<AssayEditMeta | null>(null)
const fileNameValid = ref<boolean>(true)
const modalRef = useTemplateRef('assayEditModalRef')
const showModal = ref<boolean>(false)
const updating = ref<boolean>(true)
const valid = ref<boolean>(true)

// Internal Vars ---------------------------------------------------------------

let tableContext: SodarContextAssay
// let tableUuid: string

// Helpers ---------------------------------------------------------------------

function enableSubmit (): boolean {
  return !updating.value && valid.value
}

function getFileNameClass (): string {
  if (!fileNameValid.value) return INVALID_CLASS
  return ''
}

function onFileNameInput () {
  // TODO: Add uniqueness check
  const f = assayMeta.value!.fileName.trim()
  if (!f.startsWith('a') || !EDIT_REGEX_FILE_NAME.test(f)) {
    fileNameValid.value = false
    valid.value = false
  } else {
    fileNameValid.value = true
    valid.value = true
  }
}

// API and Life Cycle ----------------------------------------------------------

function show (uuid: string) {
  tableContext = appStore.sodarContext!.studies[
    appStore.currentStudyUuid]!.assays[uuid]!
  // tableUuid = uuid
  // TODO: Add technology type and measurement type fields (see #2612)
  assayMeta.value = {
    fileName: tableContext.file_name,
    technologyPlatform: tableContext.technology_platform,
  }
  updating.value = false
  valid.value = true // We assume all data must be valid when opening
  fileNameValid.value = true
  showModal.value = true
}

function hide (update: boolean) {
  if (update) {
    // TODO: Add update logic here
  }
  modalRef.value?.hide()
}

defineExpose({ show })
</script>

<template>
  <BModal
      id="sodar-ss-assay-edit-modal"
      ref="assayEditModalRef"
      v-model="showModal"
      size="lg"
      centered no-footer no-animation teleport-disabled>
    <template #header>
      <ModalHeader
          :hide-close-button="true"
          :modal-ref="modalRef"
          title="Update Assay">
      </ModalHeader>
    </template>
    <div id="sodar-ss-assay-edit-content">
      <table
          v-if="assayMeta"
          class="table table-borderless w-100 mb-3"
          id="sodar-ss-assay-edit-table">
        <tbody>
          <tr>
            <td>File Name</td>
            <td>
              <BFormInput
                  v-model="assayMeta.fileName"
                  :class="getFileNameClass()"
                  id="sodar-ss-assay-input-meta-file"
                  @update:model-value="onFileNameInput()">
              </BFormInput>
            </td>
          </tr>
          <tr>
            <td>Technology Platform</td>
            <td>
              <BFormInput
                  v-model="assayMeta.technologyPlatform"
                  id="sodar-ss-assay-input-meta-tech-platform">
              </BFormInput>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <div id="sodar-ss-assay-edit-controls">
      <BButtonGroup
          class="pull-right"
          id="sodar-ss-assay-edit-btn-group">
        <BButton
            variant="secondary"
            id="sodar-ss-assay-edit-btn-cancel"
            :disabled="updating"
            @click="hide(false)">
          <i class="iconify" data-icon="mdi:close-thick"></i> Cancel
        </BButton>
        <BButton
            variant="primary"
            id="sodar-ss-assay-edit-btn-update"
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
table#sodar-ss-assay-edit-table tbody td:first-child {
  width: 100px;
  max-width: 250px;
  vertical-align: top;
  white-space: nowrap;
  padding-top: 20px;
}
#sodar-ss-assay-edit-btn-group {
  padding-right: 12px;
}
</style>

