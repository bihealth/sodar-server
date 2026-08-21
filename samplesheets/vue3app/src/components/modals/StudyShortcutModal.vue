<script setup lang="ts">
import { ref, useTemplateRef } from 'vue'
import { BButton, BModal } from 'bootstrap-vue-next'

import ModalHeader from '@/components/modals/ModalHeader.vue'
import WaitSection from '@/components/WaitSection.vue'
import {
  type StudyShortcutCell,
  type StudyShortcutQuery,
  type StudyShortcutResponseBody,
  type StudyShortcutResponseCategory,
  type StudyShortcutResponseData
} from '@/types.ts'
import { useAppStore } from '@/stores/appStore.ts'

// External Data ---------------------------------------------------------------

const appStore = useAppStore()

// Internal Vars ---------------------------------------------------------------

const modalTitleDefault: string = 'Loading..'

// Refs ------------------------------------------------------------------------

const message = ref<string>('')
const modalData = ref<StudyShortcutResponseData | null>(null)
const modalRef = useTemplateRef('studyShortcutModal')
const modalTitle = ref<string>(modalTitleDefault)
const showModal = ref<boolean>(false)

// Helpers ---------------------------------------------------------------------

function handleShortcutResponse (response: StudyShortcutResponseBody) {
  if ('data' in response && 'title' in response) {
    modalTitle.value = response.title as string
    let filesFound = false
    for (const cat in response.data) {
      const catData = response.data[cat] as StudyShortcutResponseCategory
      if (catData.files.length > 0) {
        filesFound = true
        break
      }
    }
    if (filesFound) modalData.value = response.data || null
    else message.value = 'No files found'
  } else if ('error' in response) {
    message.value = response.error as string
  }
}

function getShortcuts (query: StudyShortcutQuery) {
  const listUrl: string = '/samplesheets/ajax/study/links/' +
    appStore.currentStudyUuid + '?' + query.key + '=' + query.value
  fetch(listUrl, { credentials: 'same-origin' })
    .then(response => response.json())
    .then(response => {
      handleShortcutResponse(response)
    }).catch(function (error) {
      message.value = 'Error fetching data: ' + error.detail
  })
}

// API and Life Cycle ----------------------------------------------------------

// Modal showing
function show (value: StudyShortcutCell) {
  // Reset previous data
  modalTitle.value = modalTitleDefault
  message.value = ''
  modalData.value = null
  // Show modal and query server for links
  showModal.value = true
  getShortcuts(value.files.query)
}
defineExpose({ show })
</script>

<template>
  <BModal
      id="sodar-ss-study-shortcut-modal"
      ref="studyShortcutModal"
      v-model="showModal"
      size="md"
      centered no-footer no-animation teleport-disabled>
    <template #header>
      <ModalHeader
          :modal-ref="modalRef"
          :title="modalTitle">
      </ModalHeader>
    </template>
    <div v-if="modalData"
         id="sodar-ss-shortcut-modal-content">
      <table
          v-for="(cat, index) in modalData"
          :key="index"
          class="table sodar-card-table pb-3 sodar-ss-shortcut-table">
        <thead>
          <tr>
            <th colspan="2">
              {{ cat.title }}
              <span v-if="cat.omit_info && cat.omit_info.length"
                    class="text-info sodar-ss-shortcut-info"
                    :title="'Omitted from IGV: ' + cat.omit_info">
                <i class="iconify" data-icon="mdi:info"></i>
              </span>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(file, fileIdx) in cat.files"
              :key="fileIdx"
              class="sodar-ss-shortcut-item">
            <td>
              <a :href="file.url"
                 target="_blank"
                 :title="file.title || ''"
                 class="sodar-ss-shortcut-link">
                {{ file.label }}
              </a>
            </td>
            <td class="text-right text-nowrap">
              <BButton
                  v-for="(extraLink, extraIdx) in file.extra_links"
                  :key="extraIdx"
                  variant="secondary"
                  class="sodar-list-btn sodar-ss-irods-btn
                         sodar-ss-shortcut-extra ml-1"
                  :title="extraLink.label"
                  :href="extraLink.url">
                <i class="iconify" :data-icon="extraLink.icon"></i>
              </BButton>
            </td>
          </tr>
          <tr v-if="!cat.files.length">
            <td class="text-muted sodar-ss-shortcuts-no-files"
                colspan="2">
              N/A
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <div v-else-if="message !== ''"
         class="text-danger font-italic"
         id="sodar-ss-shortcuts-message">
      {{ message }}
    </div>
    <WaitSection v-else></WaitSection>
  </BModal>
</template>

<style scoped>
</style>
