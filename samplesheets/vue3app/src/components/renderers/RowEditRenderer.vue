<script setup lang="ts">
import { ref } from 'vue'
import { BButton } from 'bootstrap-vue-next'

import { useAppStore } from '@/stores/appStore.ts'
import { useEditStore } from '@/stores/editStore.ts'
import { useTableStore } from '@/stores/tableStore.ts'
import { deleteRow } from '@/utils/editUtils.ts'
import { type RowEditRendererParams } from '@/types.ts'
import {
  ROW_DEL_MSG_ALL,
  ROW_DEL_MSG_ASSAY,
  ROW_DEL_MSG_CANCEL,
  ROW_DEL_MSG_CONFIRM,
  ROW_DEL_MSG_CONFIRM_CANCEL,
  ROW_DEL_MSG_CONFIRM_IRODS,
  ROW_DEL_MSG_OK,
  ROW_DEL_MSG_UNSAVED,
} from '@/constants.ts'

// Data and initial setup ------------------------------------------------------

// External
const appStore = useAppStore()
const editStore = useEditStore()
const tableStore = useTableStore()
const props = defineProps({ params: Object })

// Refs
const deleting = ref<boolean>(false)
// const inserting = ref<boolean>(false)

// Internal
const params = props.params as RowEditRendererParams
const sampleUuid: string = params.node.data[tableStore.sampleColId].uuid

/*
if (params.node.id === '0') { // Limit debug prints to one row
  console.log('-------- DEBUG --------')
  console.log('Params:')
  console.dir(params)
}
*/

// Helpers ---------------------------------------------------------------------

function isNewRow (): boolean {
  return editStore.unsavedRow !== null &&
    editStore.unsavedRow.tableUuid === params.tableUuid &&
    editStore.unsavedRow.id === params.node.id
}

// Return true if row sample is used in assays
function isSampleUsed (): boolean {
  return sampleUuid !== '' &&
    editStore.editContext!.samples[sampleUuid]!.assays.length > 0
}

function enableDelete (): boolean {
  const newRow: boolean = isNewRow()
  if (editStore.updatingRow ||
      (editStore.unsavedRow && !newRow) ||
      (params.api.getDisplayedRowCount() < 2)) {
    return false
  }
  let sampleOk: boolean = true
  if (!params.assayMode && !newRow && isSampleUsed()) {
    sampleOk = false
  }
  return newRow || sampleOk
}

function enableSave (): boolean {
  const cols = params.api.getColumns()
  if (!cols) return true
  // NOTE: This assumes we have to fill all nodes in a column
  for (const c of cols) {
    const colId: string = c.getColId()
    if (!params.node.data[colId] || params.node.data[colId].newInit) {
      return false
    }
  }
  return true
  // NOTE: This allows saving incomplete rows (not yet implemented)
  // return !params.node.data[colId].newInit && !editStore.updatingRow
}

function getDeleteTitle (): string {
  if (editStore.updatingRow || editStore.unsavedRow) {
    if (isNewRow()) return ROW_DEL_MSG_CANCEL
    return ROW_DEL_MSG_UNSAVED
  } else if (!params.assayMode && sampleUuid && isSampleUsed()) {
    return ROW_DEL_MSG_ASSAY
  } else if (params.api.getDisplayedRowCount() < 2) {
    return ROW_DEL_MSG_ALL
  }
  return ROW_DEL_MSG_OK
}

// Modification API ------------------------------------------------------------

function finishUpdateCb () {
  // inserting.value = false
  deleting.value = false
}

function onDelete () {
  let confirmMsg: string

  if (!isNewRow()) {
    deleting.value = true
    confirmMsg = ROW_DEL_MSG_CONFIRM
    if (params.assayMode && appStore.sodarContext?.irods_status) {
      confirmMsg += ROW_DEL_MSG_CONFIRM_IRODS
    }
  } else confirmMsg = ROW_DEL_MSG_CONFIRM_CANCEL

  if (confirm(confirmMsg)) {
    deleteRow({
      api: params.api,
      assayMode: params.assayMode,
      finishCb: finishUpdateCb,
      notifyCb: params.notifyCb,
      rowNode: params.node,
      tableUuid: params.tableUuid
    })
  } else deleting.value = false // Cancel
}
</script>

<template>
  <div class="text-nowrap sodar-ss-row-edit-buttons">
    <BButton
        variant="danger"
        class="sodar-list-btn sodar-ss-row-btn mr-1 sodar-ss-row-delete-btn"
        :title="getDeleteTitle()"
        :disabled="!enableDelete()"
        @click="onDelete()">
      <i class="iconify" data-icon="mdi:close-thick"></i>
    </BButton>
    <!-- TODO: Add save functionality -->
    <BButton
        v-if="isNewRow()"
        variant="success"
        class="sodar-list-btn sodar-ss-row-btn sodar-ss-row-save-btn"
        title="Save row"
        :disabled="!enableSave()">
      <i class="iconify" data-icon="mdi:check-bold"></i>
    </BButton>
  </div>
</template>

<style scoped>
</style>
