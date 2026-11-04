<script setup lang="ts">
import { ref, useTemplateRef } from 'vue'
import { BButton, BButtonGroup, BModal } from 'bootstrap-vue-next'

import ModalHeader from '@/components/modals/include/ModalHeader.vue'
import InvStudyMetaEditSection from '@/components/modals/include/InvStudyMetaEditSection.vue'
import { useEditStore } from '@/stores/editStore.ts'

import { useAppStore } from '@/stores/appStore.ts'
import { getAjaxRequestInit } from '@/utils/appUtils.ts'
import {
  type GenericResponseBody,
  type InvStudyEditMeta,
  type InvestigationEditRequestBody,
  type SodarContextInvestigation,
} from '@/types.ts'

import {
  AJAX_RES_OK,
  REQ_POST,
  INV_UPDATE_FAIL_PREFIX,
  INV_UPDATE_OK_MSG,
  URL_INV_UPDATE_PREFIX,
  VARIANT_DANGER,
  VARIANT_SUCCESS
} from '@/constants.ts'

// External Data ---------------------------------------------------------------

const appStore = useAppStore()
const editStore = useEditStore()

// Refs ------------------------------------------------------------------------

// const fieldsValid = ref<FieldValidStatus>({})
const modalRef = useTemplateRef('invEditModalRef')
const showModal = ref<boolean>(false)
const invMeta = ref<InvStudyEditMeta | null>(null)
const updating = ref<boolean>(true)

// Helpers ---------------------------------------------------------------------

function enableSubmit (): boolean {
  return !updating.value && editStore.modalEditValid
}

// Post investigation update and handle the results
async function updateInvestigation () {
  const invUuid = (appStore.sodarContext!.investigation as
      SodarContextInvestigation).sodar_uuid
  const url = URL_INV_UPDATE_PREFIX + invUuid
  const updateBody: InvestigationEditRequestBody = {
    inv_meta: {
      description: invMeta.value!.description.trim(),
      file_name: invMeta.value!.fileName.trim(),
      identifier: invMeta.value!.identifier.trim(),
      public_release_date: invMeta.value!.publicReleaseDate.trim(),
      submission_date: invMeta.value!.submissionDate.trim(),
      title: invMeta.value!.title.trim(),
    } // TODO: Trim with a oneliner or otherwise ensure sanitization
  }
  const response = await fetch(url, getAjaxRequestInit(REQ_POST, updateBody))
  const resBody: GenericResponseBody = await response.json()
  if (resBody.detail == AJAX_RES_OK) {
    updateInvContext()
    if (appStore.notifyCb) {
      appStore.notifyCb(INV_UPDATE_OK_MSG, VARIANT_SUCCESS)
    }
  } else {
    const msg: string = INV_UPDATE_FAIL_PREFIX + resBody.detail
    if (appStore.notifyCb) appStore.notifyCb(msg, VARIANT_DANGER)
    console.error(msg)
  }
}

// Update investigation context with edited values
function updateInvContext () {
  const invContext = appStore.sodarContext!.investigation as
    SodarContextInvestigation
  invContext.description = invMeta.value!.description
  appStore.sodarContext!.inv_file_name = invMeta.value!.fileName
  invContext.identifier = invMeta.value!.identifier
  invContext.public_release_date = invMeta.value!.publicReleaseDate
  invContext.submission_date = invMeta.value!.submissionDate
  invContext.title = invMeta.value!.title
}

// API and Life Cycle ----------------------------------------------------------

function show () {
  const invContext = appStore.sodarContext!.investigation as
    SodarContextInvestigation
  invMeta.value = {
    description: invContext.description,
    fileName: appStore.sodarContext!.inv_file_name as string,
    identifier: invContext.identifier,
    publicReleaseDate: invContext.public_release_date,
    submissionDate: invContext.submission_date,
    title: invContext.title,
  }
  updating.value = false
  editStore.modalEditValid = true // Assume all data must be valid when opening
  showModal.value = true
}

function hide (update: boolean) {
  if (update) {
    updating.value = true
    try {
      updateInvestigation()
    } catch (error) {
      const msg: string = `Error updating investigation: ${error}`
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
      id="sodar-ss-inv-edit-modal"
      ref="invEditModalRef"
      v-model="showModal"
      size="lg"
      centered no-footer no-animation teleport-disabled>
    <template #header>
      <ModalHeader
          :hide-close-button="true"
          :modal-ref="modalRef"
          title="Update Investigation">
      </ModalHeader>
    </template>
    <div id="sodar-ss-inv-edit-content">
      <table
          v-if="invMeta"
          class="table table-borderless w-100 mb-3"
          id="sodar-ss-inv-edit-table">
        <InvStudyMetaEditSection
            :file-names="[]"
            :identifiers="[]"
            :metadata="invMeta"
            :study-mode="false">
        </InvStudyMetaEditSection>
      </table>
    </div>
    <div id="sodar-ss-inv-edit-controls">
      <BButtonGroup
          class="pull-right"
          id="sodar-ss-inv-edit-btn-group">
        <BButton
            variant="secondary"
            id="sodar-ss-inv-edit-btn-cancel"
            :disabled="updating"
            @click="hide(false)">
          <i class="iconify" data-icon="mdi:close-thick"></i> Cancel
        </BButton>
        <BButton
            variant="primary"
            id="sodar-ss-inv-edit-btn-update"
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
table#sodar-ss-inv-edit-table tbody td:first-child {
  width: 100px;
  max-width: 250px;
  vertical-align: top;
  white-space: nowrap;
  padding-top: 20px;
}
#sodar-ss-inv-edit-btn-group {
  padding-right: 12px;
}
</style>
