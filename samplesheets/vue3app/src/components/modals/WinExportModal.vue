<script setup lang="ts">
import { ref, useTemplateRef } from 'vue'
import { BButton, BModal } from 'bootstrap-vue-next'
import ModalHeader from '@/components/modals/ModalHeader.vue'

const props = defineProps(['projectUuid'])

const modalRef = useTemplateRef('winExportModal')
const showModal = ref<boolean>(false)

function onClick () {
  window.location.href = 'export/isa/' + props.projectUuid
  showModal.value = false
}

function show () {
  showModal.value = true
}
defineExpose({ show })
</script>

<template>
  <BModal
      id="sodar-ss-win-export-modal"
      ref="winExportModal"
      v-model="showModal"
      size="md"
      centered no-footer no-animation>
    <template #header>
      <ModalHeader
          :modal-ref="modalRef"
          title="Windows ISA-Tab Export">
      </ModalHeader>
    </template>
    <div id="sodar-ss-win-export-modal-content">
      <p>
        Please note that built-in zip archive handling in Windows may
        <strong>not</strong> unarchive all files in this export correctly.
      </p>
      <p>
        To ensure access to all files, please use third party software such as
        <a href="https://apps.microsoft.com/store/detail/nanazip/9N8G7TSCL18R"
           target="_blank">NanaZip</a>
        to unarchive the export.
      </p>
      <BButton
          variant="primary"
          class="pull-right"
          id="sodar-ss-win-export-btn"
          @click="onClick">
        <i class="iconify" data-icon="mdi:download"></i> Export ISA-Tab
      </BButton>
    </div>
  </BModal>
</template>

<style scoped>
</style>
