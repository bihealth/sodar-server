<script setup lang="ts">
import { ref, useTemplateRef } from 'vue'
import { BModal } from 'bootstrap-vue-next'

import ModalHeader from '@/components/modals/ModalHeader.vue'
import { type SodarContextStudy } from '@/types.ts'

// Refs ------------------------------------------------------------------------

const modalRef = useTemplateRef('studyEditModalRef')
const showModal = ref<boolean>(false)
const tableContext = ref<SodarContextStudy | null>(null)
const tableUuid = ref<string>('') // TODO: Do we need this as ref?

// API and Life Cycle ----------------------------------------------------------

function show (uuid: string, context: SodarContextStudy) {
  tableContext.value = context
  tableUuid.value = uuid
  showModal.value = true
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
          :modal-ref="modalRef"
          title="Update Study">
      </ModalHeader>
    </template>
    <div id="sodar-ss-study-edit-content">
      <div v-if="tableUuid && tableContext">
        <p>UUID: {{ tableUuid }}</p>
        <p>Identifier: {{ tableContext!.identifier }}</p>
        <p class="mb-0">TODO: Form goes here</p>
      </div>
    </div>
  </BModal>
</template>

<style scoped>
</style>
