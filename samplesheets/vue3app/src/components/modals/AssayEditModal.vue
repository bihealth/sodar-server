<script setup lang="ts">
import { ref, useTemplateRef } from 'vue'
import { BButton, BButtonGroup, BFormInput, BModal } from 'bootstrap-vue-next'

import ModalHeader from '@/components/modals/ModalHeader.vue'
import { useAppStore } from '@/stores/appStore.ts'
import { getAjaxRequestInit } from '@/utils/appUtils.ts'
import {
  type AssayEditMeta,
  type AssayEditRequestBody,
  type GenericResponseBody,
  type SodarContextAssay,
} from '@/types.ts'
import {
  AJAX_RES_OK,
  ASSAY_UPDATE_OK_MSG,
  ASSAY_UPDATE_FAIL_PREFIX,
  EDIT_REGEX_FILE_NAME,
  REQ_POST,
  SODAR_ISA_ASSAY_DISPLAY_NAME,
  URL_ASSAY_EDIT_PREFIX,
  VARIANT_DANGER,
  VARIANT_SUCCESS,
} from '@/constants.ts'

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

let assayFileNames: Array<string> = []
let tableContext: SodarContextAssay
let tableUuid: string

// Helpers ---------------------------------------------------------------------

function enableSubmit (): boolean {
  return !updating.value && valid.value
}

function getFileNameClass (): string {
  if (!fileNameValid.value) return INVALID_CLASS
  return ''
}

function onFileNameInput () {
  const f = assayMeta.value!.fileName.trim()
  if (!f.startsWith('a') ||
      !EDIT_REGEX_FILE_NAME.test(f) ||
      assayFileNames.includes(f)) {
    fileNameValid.value = false
    valid.value = false
  } else {
    fileNameValid.value = true
    valid.value = true
  }
}

// Post assay update and handle the results
async function updateAssay () {
  const url = URL_ASSAY_EDIT_PREFIX + tableUuid
  const updateBody: AssayEditRequestBody = {
    assay_meta: {
      file_name: assayMeta.value!.fileName.trim(),
      technology_platform: assayMeta.value!.technologyPlatform.trim(),
    }
  }
  const response = await fetch(url, getAjaxRequestInit(REQ_POST, updateBody))
  const resBody: GenericResponseBody = await response.json()
  if (resBody.detail == AJAX_RES_OK) {
    updateTableContext()
    if (appStore.notifyCb) {
      appStore.notifyCb(ASSAY_UPDATE_OK_MSG, VARIANT_SUCCESS)
    }
  } else {
    const msg: string = ASSAY_UPDATE_FAIL_PREFIX + resBody.detail
    if (appStore.notifyCb) appStore.notifyCb(msg, VARIANT_DANGER)
    console.error(msg)
  }
}

// Update tableContext with edited values
function updateTableContext () {
  tableContext.file_name = assayMeta.value!.fileName.trim()
  tableContext.technology_platform = assayMeta.value!.technologyPlatform.trim()

  // Update display name if SODAR assay display name is not set
  if (!tableContext.comments ||
      !(SODAR_ISA_ASSAY_DISPLAY_NAME in tableContext.comments) ||
      tableContext.comments[SODAR_ISA_ASSAY_DISPLAY_NAME] === '') {
    let title = tableContext.file_name.slice(2, -4).replace(/_/g, ' ')
    title = title.split(' ').map(
      w => w[0]!.toUpperCase() + w.substring(1).toLowerCase()).join(' ')
    tableContext.display_name = title
  }
}

// API and Life Cycle ----------------------------------------------------------

function show (uuid: string) {
  tableContext = appStore.sodarContext!.studies[
    appStore.currentStudyUuid]!.assays[uuid]!
  tableUuid = uuid

  // Store assay file names for uniqueness check
  assayFileNames = []
  for (const s of Object.values(appStore.sodarContext!.studies)) {
    for (const [k, v] of Object.entries(s.assays)) {
      if (k !== tableUuid) assayFileNames.push(v.file_name)
    }
  }

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
    updating.value = true
    try {
      updateAssay()
    } catch (error) {
      const msg: string = `Error updating assay: ${error}`
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

