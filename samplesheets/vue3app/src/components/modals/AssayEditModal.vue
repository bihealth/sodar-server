<script setup lang="ts">
import { ref, useTemplateRef } from 'vue'
import { BButton, BButtonGroup, BFormInput, BModal } from 'bootstrap-vue-next'

import IsaCommentEditSection from '@/components/modals/include/IsaCommentEditSection.vue'
import ModalHeader from '@/components/modals/include/ModalHeader.vue'
import ModalTableSeparator from '@/components/modals/include/ModalTableSeparator.vue'

import { useAppStore } from '@/stores/appStore.ts'
import { useEditStore } from '@/stores/editStore.ts'
import { getAjaxRequestInit } from '@/utils/appUtils.ts'
import {
  type AssayEditMeta,
  type AssayEditRequestBody,
  type GenericResponseBody,
  type SodarContextAssay,
  type SodarContextComments,
} from '@/types.ts'
import {
  AJAX_RES_OK,
  ASSAY_UPDATE_OK_MSG,
  ASSAY_UPDATE_FAIL_PREFIX,
  EDIT_REGEX_FILE_NAME,
  REQ_POST,
  SODAR_ISA_ASSAY_DISPLAY_NAME,
  SODAR_ISA_ASSAY_MISC,
  SODAR_ISA_ASSAY_PATH_PREFIX,
  SODAR_ISA_ASSAY_PLUGIN,
  SODAR_ISA_ASSAY_RESULTS,
  SODAR_ISA_ASSAY_LINK_ROW,
  URL_ASSAY_UPDATE_PREFIX,
  VARIANT_DANGER,
  VARIANT_SUCCESS,
} from '@/constants.ts'

// Constants -------------------------------------------------------------------

const INVALID_CLASS = 'text-danger'
const MANDATORY_COMMENTS = [SODAR_ISA_ASSAY_DISPLAY_NAME]
const CACHE_UPDATE_COMMENTS = [
  SODAR_ISA_ASSAY_MISC,
  SODAR_ISA_ASSAY_PLUGIN,
  SODAR_ISA_ASSAY_RESULTS,
  SODAR_ISA_ASSAY_LINK_ROW
]

// External Data ---------------------------------------------------------------

const appStore = useAppStore()
const editStore = useEditStore()

// Refs ------------------------------------------------------------------------

const assayComments = ref<SodarContextComments | null>(null)
const assayMeta = ref<AssayEditMeta | null>(null)
const fileNameValid = ref<boolean>(true)
const modalRef = useTemplateRef('assayEditModalRef')
const showModal = ref<boolean>(false)
const updating = ref<boolean>(true)
const valid = ref<boolean>(true)

// Internal Vars ---------------------------------------------------------------

let assayFileNames: Array<string> = []
let ogContext: SodarContextAssay
let tableContext: SodarContextAssay
let tableUuid: string

// Helpers ---------------------------------------------------------------------

// Check dynamic generic plugin row paths for cache updating
function checkGenericRowPaths (
    comments1: SodarContextComments,
    comments2: SodarContextComments) {
  if (editStore.updateCache) return
  for (const c in comments1) {
    if (c.startsWith(SODAR_ISA_ASSAY_PATH_PREFIX) &&
        (comments1[c] !== comments2[c] || !(c in comments2))) {
      editStore.updateCache = true
      return
    }
  }
}

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
  const url = URL_ASSAY_UPDATE_PREFIX + tableUuid
  const updateBody: AssayEditRequestBody = {
    assay_meta: {
      file_name: assayMeta.value!.fileName.trim(),
      technology_platform: assayMeta.value!.technologyPlatform.trim(),
    },
    comments: assayComments.value!
  }
  const response = await fetch(url, getAjaxRequestInit(REQ_POST, updateBody))
  const resBody: GenericResponseBody = await response.json()
  if (resBody.detail == AJAX_RES_OK) {
    updateContext()
    if (appStore.notifyCb) {
      appStore.notifyCb(ASSAY_UPDATE_OK_MSG, VARIANT_SUCCESS)
    }
  } else {
    const msg: string = ASSAY_UPDATE_FAIL_PREFIX + resBody.detail
    if (appStore.notifyCb) appStore.notifyCb(msg, VARIANT_DANGER)
    console.error(msg)
  }
}

// Update tableContext and editStore
function updateContext () {
  // Update table context
  tableContext.file_name = assayMeta.value!.fileName.trim()
  tableContext.technology_platform = assayMeta.value!.technologyPlatform.trim()
  tableContext.comments = assayComments.value

  // Update display name
  if (!tableContext.comments ||
      !(SODAR_ISA_ASSAY_DISPLAY_NAME in tableContext.comments) ||
      tableContext.comments[SODAR_ISA_ASSAY_DISPLAY_NAME] === '') {
    let title = tableContext.file_name.slice(2, -4).replace(/_/g, ' ')
    title = title.split(' ').map(
      w => w[0]!.toUpperCase() + w.substring(1).toLowerCase()).join(' ')
    tableContext.display_name = title
  } else {
    tableContext.display_name = tableContext.comments[
      SODAR_ISA_ASSAY_DISPLAY_NAME]
  }

  // Update editStore
  // TODO: Add technology type and measurement type checks (see #2612)
  if (editStore.updateCache) return
  for (const c of CACHE_UPDATE_COMMENTS) {
    if (tableContext.comments![c] !== ogContext.comments![c]) {
      editStore.updateCache = true
      break
    }
  }
  checkGenericRowPaths(tableContext.comments!, ogContext.comments!)
  checkGenericRowPaths(ogContext.comments!, tableContext.comments!)
}

// API and Life Cycle ----------------------------------------------------------

function show (uuid: string) {
  tableContext = appStore.sodarContext!.studies[
    appStore.currentStudyUuid]!.assays[uuid]!
  tableUuid = uuid
  // Force null assay comments into empty object
  if (!tableContext.comments) tableContext.comments = {}
  // Store original values
  ogContext = JSON.parse(JSON.stringify(tableContext)) as SodarContextAssay

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
  assayComments.value = tableContext.comments
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
          icon="mdi:table-large"
          icon-variant="danger"
          :modal-ref="modalRef"
          title="Update Assay">
      </ModalHeader>
    </template>
    <div id="sodar-ss-assay-edit-content">
      <table
          v-if="assayMeta"
          class="table table-borderless sodar-ss-isa-isa-edit-table w-100 mb-3"
          id="sodar-ss-assay-edit-table">
        <!-- Metadata -->
        <tbody class="sodar-ss-assay-meta-edit-body">
          <tr>
            <th colspan="3">Metadata</th>
          </tr>
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
        <ModalTableSeparator colspan="3" />
        <!-- Comments -->
        <IsaCommentEditSection
            :comments="assayComments"
            :mandatory="MANDATORY_COMMENTS">
        </IsaCommentEditSection>
      </table>
    </div>
    <div id="sodar-ss-assay-edit-controls">
      <BButtonGroup
          class="sodar-ss-isa-edit-btn-group pull-right"
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
</style>
