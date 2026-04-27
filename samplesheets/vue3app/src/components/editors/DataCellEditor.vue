<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import { onMounted, onUnmounted } from 'vue'

// import { useEditStore } from '@/stores/editStore.ts'
// import { useTableStore } from '@/stores/tableStore.ts'
import { updateCells } from '@/utils/editUtils.ts'
import {
  type SheetTableCellData,
  type CellEditData,
  type NotifyCb,
  type SheetTableCellDataValue,
  type StudyEditConfigNodeField
} from '@/types.ts'
import { EDIT_REGEX } from '@/constants.ts'

// const editStore = useEditStore()
// const tableStore = useTableStore()
const props = defineProps({ params: Object })

// Data and initial setup ------------------------------------------------------

// Params shortcuts
const cellData = props.params?.value as SheetTableCellData
const editConfig = props.params?.editConfigField as
  StudyEditConfigNodeField
const headerType: string = props.params?.fieldHeader.type
const itemType: string | undefined = props.params?.fieldHeader.item_type
const notifyCb: NotifyCb | undefined = props.params?.notifyCb

// Internal variables
let inputStyle: string = ''
const nameColumn: boolean = ['name', 'process_name'].includes(headerType)
const nameValues: Array<string> = []
// const navKeyCodes = [33, 34, 35, 36, 37, 38, 39, 40]
let ogValue: SheetTableCellDataValue // Original value for saving and revert
if (cellData.value) {
  ogValue = JSON.parse(
    JSON.stringify(props.params!.value.value)) as SheetTableCellDataValue
} else ogValue = ''
let ogUnit: string // Original unit for saving and revert
let regex: RegExp
let unitEnabled: boolean = false
let unitStyle: string = ''
let valueSelect: boolean = false

// Refs
const containerClass = ref<string>('')
const editUnit = ref<string | undefined>(undefined) // Unit if supported
const editValue = ref<string | undefined>(undefined) // Value to be edited
if (Array.isArray(cellData.value)) {
  editValue.value = cellData.value.join('; ')
} else editValue.value = cellData.value
const input = ref<HTMLInputElement | undefined>()
// TODO: Implement getValidState() and get initial value
const valid = ref<boolean>(true)

// Enable select editor
if (editConfig.format === 'select' &&
    'options' in editConfig &&
    editConfig.options!.length > 0) {
  valueSelect = true
}

// Set up unit value
if (editConfig.unit) {
  if (cellData.unit) {
    editUnit.value = cellData.unit
    ogUnit = JSON.parse(JSON.stringify(cellData.unit))
  } else if (editConfig.unit_default) {
    editUnit.value = editConfig.unit_default
  }
  unitEnabled = true
}

// Set classes and styling for popup
if (unitEnabled) {
  containerClass.value = 'sodar-ss-data-cell-popup text-nowrap'
  let inputWidth = props.params?.colWidth
  const unitWidth = Math.max(
    0, ...editConfig.unit!.map(e => e.length)) * 15 + 15
  inputWidth = Math.max(inputWidth - unitWidth, 120)
  inputStyle = 'width: ' + inputWidth.toString() + 'px;'
  unitStyle = 'width: ' + unitWidth.toString() + 'px !important;'
}

// Set regex
if (editConfig.format !== 'select' && editConfig.regex) {
  regex = new RegExp(editConfig.regex)
} else if (headerType === 'name' && itemType === 'DATA') {
  // Data name is a special case
  regex = EDIT_REGEX.dataName as RegExp
} else if (headerType === 'name') {
  // Other name columns
  regex = EDIT_REGEX.name as RegExp
} else if (editConfig.format === 'integer') {
  regex = EDIT_REGEX.integer as RegExp
} else if (editConfig.format === 'double') {
  regex = EDIT_REGEX.double as RegExp
}

// TODO: Set up name column handling (incl. nameValues)

// Get initial valid state
valid.value = isValid()

// TODO: Set keyboard navigation prevention (if needed?)

// Helpers ---------------------------------------------------------------------

// Test regex with semicolon-separated list support
function testListRegex (): boolean {
  // Don't need to add this to multiple regexes this way..
  if (editValue.value?.slice(-1) === ';') return false
  const valSplit = editValue.value?.split(';') as Array<string>
  for (let i = 0; i < valSplit.length; i++) {
    if (!regex.test((valSplit[i] as string)?.trim())) return false
  }
  return true
}

// Return valid state for current value (formerly getValidState())
function isValid (): boolean {
  // Name field
  if (nameColumn) {
    // NOTE: Empty value is allowed for DATA materials
    if ((!editValue.value && itemType !== 'DATA') || (
        editValue.value &&
        !cellData.newRow &&
        editValue.value !== ogValue &&
        nameValues.includes(editValue.value))) {
      return false
    }
    // Prevent pooling of samples
    if (props.params?.fieldId === props.params?.sampleColId &&
        editValue.value !== ogValue &&
        nameValues.includes(editValue.value as string)) {
      return false
    }
  } else if (editValue.value !== '') { // Following checks only for filled value
    if (['double', 'integer'].includes(editConfig.format as string) &&
        editConfig.range &&
        editConfig.range.length === 2) {
      // Range
      const range = editConfig.range
      const valSplit = editValue.value?.split(';')
      for (let i = 0; i < valSplit!.length; i++) {
        const vNum = parseFloat((valSplit![i] as string)?.trim())
        if (vNum < parseFloat(range[0]) || vNum > parseFloat(range[1])) {
          return false
        }
      }
    } else if (editConfig.format === 'date') {
      // Date
      if (!(EDIT_REGEX.date as RegExp).test(editValue.value as string)) {
        return false
      } else {
        // Validate for correct date
        // TODO: There probably is a package for this? :)
        const dateSplit = editValue.value?.split('-')
        const y = parseInt(dateSplit![0] as string)
        const m = dateSplit![1] as string
        const mInt = parseInt(m)
        const d = parseInt(dateSplit![2] as string)
        if (['04', '06', '09', '11'].includes(m) && d > 30) {
          return false
        }
        if ((mInt === 2 && d > 29) || (mInt === 2 && d > 28 && y % 4 !== 0)) {
          return false
        }
      }
    } else if (editConfig.format === 'external_links') {
      if (!(EDIT_REGEX.externalLinks as RegExp).test(
          editValue.value as string)) {
        return false
      }
    }
  }
  // Finally, rest general regex for field if we have set one
  return !(editValue.value !== '' && regex && !testListRegex())
}

// Return input element extra classes
function getInputClass () {
  let ret = ''
  if (unitEnabled) ret += ' sodar-ss-popup-input'
  if (!valid.value) ret += ' text-danger'
  return ret + ' text-' + props.params?.colAlign
}

// TODO: add getSelectClass if needed
function selectEmptyValue (value: string | null | undefined): boolean {
  return value === '' || !value
}

// API and lifecycle -----------------------------------------------------------

// Return value for ag-grid API
function getValue () {
  if (editValue.value === null || editValue.value === undefined) {
    cellData.value = ''
  } else if (editValue.value && editValue.value.includes(';')) {
    cellData.value = editValue.value.split(';').filter(
      (x) => { return x != '' }).map((x) => x.trim())
  } else {
    cellData.value = editValue.value.trim()
  }
  if (unitEnabled) {
    cellData.unit = editUnit.value
  }
  return cellData
}
defineExpose({ getValue })

// Update valid state when editValue is updated
watch(() => editValue.value, () => {
  valid.value = isValid()
})

onMounted(() => {
  // TODO: Add selectEnabled in appStore, update
  // Force focus into input
  nextTick(() => {
    input.value?.focus()
  })
})

onUnmounted(() => {
  // Check and reject invalid value
  if (!valid.value) {
    cellData.value = ogValue
    if (notifyCb) notifyCb('Invalid cell value', 'danger', 0)
    // TODO: Implement and call finalization func
    return
  }

  // TODO: Add new row node renaming check and handling

  const finalValue = getValue().value

  // TODO: Update/initialize node
  // Update value of existing cell
  if (JSON.stringify(finalValue) !== JSON.stringify(ogValue) || (
      unitEnabled && finalValue !== '' && editUnit.value != ogUnit)) {
    const cellEditData: CellEditData = {
      fieldId: props.params?.fieldId,
      headerName: props.params?.fieldHeader.name,
      headerType: headerType,
      itemType: itemType,
      objCls: props.params?.fieldHeader.obj_cls,
      ogUnit: ogUnit,
      ogValue: ogValue,
      unit: editUnit.value,
      uuid: cellData.uuid,
      uuidRef: cellData.uuidRef,
      value: finalValue
    }
    updateCells(cellEditData, true, notifyCb)
    // TODO: Update sample list if sample has been renamed
    // TODO: Update selectEnabled
  }
  // TODO: Implement and call finalization func
})
</script>

<template>
  <div v-if="editValue !== undefined"
       :class="'sodar-ss-editor-cell ' + containerClass">
    <!-- Select input -->
    <span v-if="valueSelect">
      <select
          v-model="editValue"
          ref="input"
          class="ag-cell-edit-input sodar-ss-edit-select">
        <option
            value=""
            class="sodar-ss-edit-select-option
                   sodar-ss-edit-select-option-empty"
            :selected="selectEmptyValue(editValue)">
          -
        </option>
        <option
            v-for="(val, idx) in editConfig.options"
            :key="idx"
            :value="val"
            class="sodar-ss-edit-select-option"
            :selected="editValue === val">
          {{ val }}
        </option>
      </select>
    </span>
    <!-- Basic text input -->
    <span v-else>
      <input
          v-model.trim="editValue"
          :class="'ag-cell-edit-input sodar-ss-edit-input' + getInputClass()"
          ref="input"
          :style="inputStyle" />
    </span>
    <!-- Unit select (in popup) -->
    <select
        v-if="unitEnabled"
        v-model="editUnit"
        class="ag-cell-edit-input sodar-ss-popup-input sodar-ss-edit-unit ml-1"
        ref="unitText"
        :style="unitStyle">
      <option
          class="sodar-ss-edit-unit-option"
          :value="null">-</option>
      <option
          v-for="(unit, idx) in editConfig.unit"
          :key="idx"
          class="sodar-ss-edit-unit-option"
          :value="unit">
        {{ unit }}
      </option>
    </select>
  </div>
</template>

<style scoped>
/* See vue3app.css for common editor component styles */
</style>
