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
import { type NotifyCb } from '@/types.ts'
import {
  EDIT_MSG_SAVE,
  EDIT_MSG_SAVE_ERR_PREFIX,
  EDIT_MSG_SAVE_FAIL_PREFIX,
  URL_VERSION_SAVE_PREFIX,
} from '@/constants.ts'

// Data and initial setup ------------------------------------------------------

const appStore = useAppStore()
const editStore = useEditStore()

const description = ref<string>('')
const modalRef = useTemplateRef('versionSaveModal')
let notifyCb: NotifyCb | undefined = undefined
const showModal = ref<boolean>(false)
const url = URL_VERSION_SAVE_PREFIX + appStore.projectUuid

// Helpers ---------------------------------------------------------------------

function postSave () {
  fetch(url, {
    method: 'POST',
    body: JSON.stringify({ save: true, description: description.value }),
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      'X-CSRFToken': appStore.sodarContext!.csrf_token
    }
  }).then(data => data.json())
    .then(data => {
      if (data.detail === 'ok') {
        editStore.versionSaved = true
        if (notifyCb) notifyCb(EDIT_MSG_SAVE, 'success')
      } else {
        const msg = EDIT_MSG_SAVE_FAIL_PREFIX + data.detail
        console.error(msg)
        if (notifyCb) notifyCb(msg, 'danger', 2000)
      }
    }).catch(function (error) {
      const msg = EDIT_MSG_SAVE_ERR_PREFIX + error
      console.error(msg)
      if (notifyCb) notifyCb(msg, 'danger', 2000)
  })
}

// API and lifecycle -----------------------------------------------------------

function show (modalNotifyCb?: NotifyCb) {
  notifyCb = modalNotifyCb
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
