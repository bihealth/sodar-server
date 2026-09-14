<script setup lang="ts">
import { ref, useTemplateRef } from 'vue'
import {
  BButtonGroup,
  BButton,
  BFormTextarea,
  BModal
} from 'bootstrap-vue-next'

import ModalHeader from '@/components/modals/ModalHeader.vue'
import { useAppStore } from '@/stores/appStore.ts'
import { useEditStore } from '@/stores/editStore.ts'

import { getAjaxRequestInit } from '@/utils/appUtils.ts'
import {
  EDIT_MSG_SAVE,
  EDIT_MSG_SAVE_ERR_PREFIX,
  EDIT_MSG_SAVE_FAIL_PREFIX,
  REQ_POST,
  URL_VERSION_SAVE_PREFIX,
  VARIANT_DANGER,
  VARIANT_SUCCESS,
} from '@/constants.ts'

// External Data ---------------------------------------------------------------

const appStore = useAppStore()
const editStore = useEditStore()

// Refs ------------------------------------------------------------------------

const description = ref<string>('')
const modalRef = useTemplateRef('versionSaveModal')
const showModal = ref<boolean>(false)

// Internal Vars ---------------------------------------------------------------

const url = URL_VERSION_SAVE_PREFIX + appStore.projectUuid

// Helpers ---------------------------------------------------------------------

function postSave () {
  fetch(url, getAjaxRequestInit(
      REQ_POST, { save: true, description: description.value })
  ).then(data => data.json())
    .then(data => {
      if (data.detail === 'ok') {
        editStore.versionSaved = true
        if (appStore.notifyCb) {
          appStore.notifyCb(EDIT_MSG_SAVE, VARIANT_SUCCESS)
        }
      } else {
        const msg = EDIT_MSG_SAVE_FAIL_PREFIX + data.detail
        console.error(msg)
        if (appStore.notifyCb) appStore.notifyCb(msg, VARIANT_DANGER)
      }
    }).catch(function (error) {
      const msg = EDIT_MSG_SAVE_ERR_PREFIX + error
      console.error(msg)
      if (appStore.notifyCb) appStore.notifyCb(msg, VARIANT_DANGER)
  })
}

// API and Life Cycle ----------------------------------------------------------

function show () {
  showModal.value = true
}

function hideModal (save: boolean) {
  if (save) postSave()
  modalRef.value?.hide()
}

defineExpose({ show })
</script>

<template>
  <BModal
      id="sodar-ss-version-save-modal"
      ref="versionSaveModal"
      v-model="showModal"
      size="md"
      centered no-footer no-animation teleport-disabled>
    <template #header>
      <ModalHeader
          :modal-ref="modalRef"
          title="Save Sheet Version">
      </ModalHeader>
    </template>
    <div class="mb-4"
         id="sodar-ss-version-save-content">
      <p>
        Save the current sheet version as backup. You can add an
        optional description to be deplayed in the version list.
      </p>
      <BFormTextarea
          id="sodar-ss-version-save-desc"
          v-model="description"
          placeholder="Description (max. 128 characters)"
          rows="3"
          :state="description.length <= 128"
          no-resize>
      </BFormTextarea>
    </div>
    <div>
      <BButtonGroup
          class="pull-right"
          id="sodar-ss-version-btn-group">
        <BButton
            variant="secondary"
            id="sodar-ss-version-btn-cancel"
            @click="hideModal(false)">
          <i class="iconify" data-icon="mdi:close-thick"></i> Cancel
        </BButton>
        <BButton
            variant="primary"
            id="sodar-ss-version-btn-update"
            @click="hideModal(true)">
          <i class="iconify" data-icon="mdi:check-bold"></i> Update
        </BButton>
      </BButtonGroup>
    </div>
  </BModal>
</template>

<style scoped>
</style>
