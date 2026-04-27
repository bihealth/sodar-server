<script setup lang="ts">
import { nextTick, onMounted, onUnmounted, ref } from 'vue'

import { useEditStore } from '@/stores/editStore.ts'
import { updateCells } from '@/utils/editUtils.ts'
import {
  type CellEditData,
  type NotifyCb,
  type SheetTableCellData
} from '@/types.ts'

interface ObjectSelectOption {
  name: string,
  uuid: string,
}

// Data and initial setup ------------------------------------------------------

// Props and external
const editStore = useEditStore()
const props = defineProps({ params: Object })
const cellData = props.params?.value as SheetTableCellData

// Refs
const editUuid = ref<string>(cellData.uuidRef as string)
const input = ref<HTMLInputElement | undefined>()
const selectOptions = ref<Array<ObjectSelectOption>>([])

// Internal
const notifyCb: NotifyCb | undefined = props.params?.notifyCb
const ogValue: string = cellData.value as string
const optionLookup: { [k: string]: string } = {}

if (props.params?.fieldHeader.type === 'protocol') {
  selectOptions.value = editStore.editContext?.protocols as
    Array<ObjectSelectOption>
  for (const p of editStore.editContext!.protocols) {
    optionLookup[p.uuid] = p.name
  }
}
// TODO: Add support for samples once row editing is added (see #2458)

// Helpers ---------------------------------------------------------------------

function isSelected (uuid: string) {
  return uuid === editUuid.value
}

// API and lifecycle -----------------------------------------------------------

// Return value for ag-grid API
function getValue () {
  cellData.uuidRef = editUuid.value
  cellData.value = optionLookup[cellData.uuidRef] as string
  return cellData
}
defineExpose({ getValue })

onMounted(() => {
  // Force focus into input
  nextTick(() => {
    input.value?.focus()
  })
})

onUnmounted(() => {
  // Update value on server and tables if changed
  const newValue = optionLookup[editUuid.value] as string
  if (editUuid.value && newValue !== ogValue) {
    const cellEditData: CellEditData = {
      fieldId: props.params?.fieldId,
      headerName: props.params?.fieldHeader.name,
      headerType: props.params?.fieldHeader.type || '',
      itemType: props.params?.fieldHeader.item_type || '',
      objCls: props.params?.fieldHeader.obj_cls,
      ogValue: ogValue,
      uuid: cellData.uuid,
      uuidRef: editUuid.value,
      value: newValue,
    }
    updateCells(cellEditData, true, notifyCb)
  }
})
</script>

<template>
  <div v-if="cellData"
       class="sodar-ss-data-object-select">
    <select
        ref="input"
        class="ag-cell-edit-input"
        v-model="editUuid">
      <option
          v-for="(opt, idx) in selectOptions"
          :key="idx"
          class="sodar-ss-data-object-option"
          :value="opt.uuid"
          :selected="isSelected(opt.uuid)">
        {{ opt.name }}
      </option>
    </select>
  </div>
</template>

<style scoped>
</style>
