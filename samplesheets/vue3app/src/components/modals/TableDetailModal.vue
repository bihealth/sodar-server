<script setup lang="ts">
import { ref, useTemplateRef } from 'vue'
import { BModal } from 'bootstrap-vue-next'

import ModalHeader from '@/components/modals/ModalHeader.vue'
import TableDetailList from '@/components/TableDetailList.vue'
import { useAppStore } from '@/stores/appStore.ts'
import {
  STUDY_META_FIELDS,
  STUDY_SODAR_FIELDS,
  ASSAY_META_FIELDS,
  ASSAY_SODAR_FIELDS,
} from '@/constants.ts'
import { type SodarContextAssay, type SodarContextStudy } from '@/types.ts'

// External Data ---------------------------------------------------------------

const appStore = useAppStore()
const modalRef = useTemplateRef('tableDetailModal')

// Refs ------------------------------------------------------------------------

const assayMode = ref<boolean>(false)
const metaFields = ref<object | null>(null)
const sodarFields = ref<object | null>(null)
const tableContext = ref<object | null>(null)
const tableTitle = ref<string>('')
const tableUuid = ref<string>('')
const showModal = ref<boolean>(false)

// API and Life Cycle ----------------------------------------------------------

function show (
    uuid: string,
    context: SodarContextAssay | SodarContextStudy
) {
  tableContext.value = context
  tableUuid.value = uuid
  if (tableUuid.value === appStore.currentStudyUuid) {
    assayMode.value = false
    metaFields.value = STUDY_META_FIELDS
    sodarFields.value = STUDY_SODAR_FIELDS
    tableTitle.value = 'Study'
  } else {
    assayMode.value = true
    tableTitle.value = 'Assay'
    metaFields.value = ASSAY_META_FIELDS
    sodarFields.value = ASSAY_SODAR_FIELDS
  }
  showModal.value = true
}
defineExpose({ show })
</script>

<template>
  <BModal
      id="sodar-ss-table-detail-modal"
      ref="tableDetailModal"
      v-model="showModal"
      size="xl"
      centered no-footer no-animation teleport-disabled>
    <template #header>
      <ModalHeader
          :modal-ref="modalRef"
          :title="tableTitle + ' Details'">
      </ModalHeader>
    </template>
    <div id="sodar-ss-table-detail-modal-content">
      <TableDetailList
          :assay-mode="assayMode"
          :table-context="tableContext"
          :table-meta-fields="metaFields"
          :table-sodar-fields="sodarFields"
          :table-uuid="tableUuid">
      </TableDetailList>
    </div>
  </BModal>
</template>

<style scoped>
</style>
