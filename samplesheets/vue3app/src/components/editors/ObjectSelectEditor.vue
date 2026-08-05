<script setup lang="ts">
import { nextTick, onMounted, onUnmounted, ref } from 'vue'

import { useEditStore } from '@/stores/editStore.ts'
import { updateCells, updateNode } from '@/utils/editUtils.ts'
import {
  type CellEditData,
  type GridCellEditorParams,
  type SheetTableCellData
} from '@/types.ts'
import {
  EDIT_HEADER_TYPE_NAME,
  EDIT_HEADER_TYPE_PROTOCOL,
  EDIT_ITEM_TYPE_SAMPLE,
} from '@/constants.ts'

interface ObjectSelectOption {
  name: string,
  uuid: string,
}

// Data and initial setup ------------------------------------------------------

// Props and external
const editStore = useEditStore()
const props = defineProps({ params: Object })
const params = props.params as GridCellEditorParams
const cellData: SheetTableCellData = params.value
// console.dir(params)

// Refs
const editUuid = ref<string>(cellData.uuidRef as string)
const input = ref<HTMLInputElement | undefined>()
const selectOptions = ref<Array<ObjectSelectOption>>([])

// Internal
const nodeUpdateHeaders = [EDIT_HEADER_TYPE_NAME, EDIT_HEADER_TYPE_PROTOCOL]
const ogValue: string = cellData.value as string
const optionLookup: { [k: string]: string } = {}
const isSampleNameField: boolean = params.fieldHeader.type ===
  EDIT_HEADER_TYPE_NAME &&
  params.fieldHeader.item_type === EDIT_ITEM_TYPE_SAMPLE

if (params.fieldHeader.type === EDIT_HEADER_TYPE_PROTOCOL) {
  selectOptions.value = editStore.editContext?.protocols as
    Array<ObjectSelectOption>
  for (const p of editStore.editContext!.protocols) {
    optionLookup[p.uuid] = p.name
  }
} else if (isSampleNameField) {
  selectOptions.value = []
  for (const sUuid in editStore.editContext!.samples) {
    const s = editStore.editContext!.samples[sUuid]
    selectOptions.value.push({ name: s!.name as string, uuid: sUuid })
    optionLookup[sUuid] = s!.name
  }
  selectOptions.value = selectOptions.value.sort(
    (a, b) => a.name.localeCompare(b.name))
}

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
    if (nodeUpdateHeaders.includes(params.fieldHeader.type as string) &&
        (!editUuid.value || cellData.newRow)) {
      // Update node if on a new row
      cellData.newInit = false
      updateNode({
        api: params.api,
        assayMode: params.assayMode,
        column: params.column,
        createNew: params.fieldHeader.type === EDIT_HEADER_TYPE_PROTOCOL,
        nameCellData: isSampleNameField ? cellData : null,
        rowNode: params.node,
        tableUuid: params.tableUuid
      })
    } else {
      // Else update cell and related cells in other tables
      const cellEditData: CellEditData = {
        fieldId: params.fieldId as string,
        headerName: params.fieldHeader.name,
        headerType: params.fieldHeader.type || '',
        itemType: params.fieldHeader.item_type || '',
        objCls: params.fieldHeader.obj_cls,
        ogValue: ogValue,
        uuid: cellData.uuid,
        uuidRef: editUuid.value,
        value: newValue,
      }
      updateCells(cellEditData, true, params.notifyCb)
    }
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
