<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import { onMounted, onUnmounted } from 'vue'

import { useEditStore } from '@/stores/editStore.ts'
import { useTableStore } from '@/stores/tableStore.ts'
import { updateCells, updateNode } from '@/utils/editUtils.ts'
import {
  type SheetTableCellData,
  type CellEditData,
  type GridCellEditorParams,
  type NotifyCb,
  type SheetTableCellDataValue,
  type StudyEditConfigNodeField
} from '@/types.ts'
import {
  CELL_NODE_NAME_NEW,
  CELL_NODE_NAME_RENAME,
  EDIT_HEADER_TYPE_NAME,
  EDIT_HEADER_TYPE_PROCESS,
  EDIT_REGEX,
  NODE_RENAME_MSG
} from '@/constants.ts'

// Data and initial setup ------------------------------------------------------

// External
const editStore = useEditStore()
const tableStore = useTableStore()
const props = defineProps({ params: Object })

// Params shortcuts
const params = props.params as GridCellEditorParams
const cellData = params.value as SheetTableCellData
const editConfig = params.editConfigField as StudyEditConfigNodeField
const headerType: string = params.fieldHeader.type as string
const itemType: string | null = params.fieldHeader.item_type
const notifyCb: NotifyCb | undefined = params.notifyCb

// console.log('DataCellEditor params:')
// console.dir(params)

// Internal variables
let inputStyle: string = ''
const nameColumn: boolean = [
  EDIT_HEADER_TYPE_NAME, EDIT_HEADER_TYPE_PROCESS].includes(headerType)
const nameUuids: { [key: string]: string } = {}
const nameValues: Array<string> = []
// const navKeyCodes = [33, 34, 35, 36, 37, 38, 39, 40]
let ogValue: SheetTableCellDataValue // Original value for saving and revert
if (cellData.value) {
  ogValue = JSON.parse(
    JSON.stringify(params.value.value)) as SheetTableCellDataValue
} else ogValue = ''
let ogUnit: string // Original unit for saving and revert
let regex: RegExp
let unitEnabled: boolean = false
let unitStyle: string = ''
let valueSelect: boolean = false

// Refs
const containerClass = ref<string>('')
const containerTitle = ref<string>('')
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
  let inputWidth = params.colWidth
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

// Set up name column handling
if (nameColumn) {
  containerTitle.value = cellData.newRow ?
    CELL_NODE_NAME_NEW : CELL_NODE_NAME_RENAME
  setNameData() // Set nameValues and nameUuids
}

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
    if (params.fieldId === params.sampleColId &&
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
  return ret + ' text-' + params.colAlign
}

// TODO: add getSelectClass if needed
function selectEmptyValue (value: string | null | undefined): boolean {
  return value === '' || !value
}

// Save node names and UUIDs for comparison
// TODO: We should maintain these in a store instead of building here
function setNameData () {
  const fieldId = params.fieldId as string
  // TODO: Do we need to iterate through all grids? (see old implementation)
  for (const api of tableStore.getGridApis()) {
    if (!api.getColumn(fieldId)) continue // Skip grid if column is not present
    api.forEachNode(function (rowNode) {
      if (fieldId in rowNode.data) {
        const cmpData = rowNode.data[fieldId]
        if (cmpData.uuid !== cellData.uuid &&
            !nameValues.includes(cmpData.value)) {
          nameValues.push(cmpData.value)
          nameUuids[cmpData.value] = cmpData.uuid
        }
      }
    })
  }
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
  // Update cell/node
  const finalValue = getValue().value

  // Confirm renaming node into an existing node and overwriting values
  if (nameColumn &&
      cellData.newRow &&
      ogValue &&
      nameValues.includes(finalValue as string) &&
      !confirm(NODE_RENAME_MSG)) {
    cellData.value = ogValue
    // TODO: Implement and call finalization func
    if (params.notifyCb) params.notifyCb('Renaming cancelled', 'info', 0)
  }

  if (nameColumn && (!cellData.uuid || cellData.newRow)) { // Update/init node
     cellData.newInit = false

    // Set or clear UUID
    if (nameValues.includes(finalValue as string)) {
      cellData.uuid = nameUuids[finalValue as string]
    } else cellData.uuid = ''

    // Set unit
    if (!editUnit.value || !finalValue) cellData.unit = ''
    else cellData.unit = editUnit.value

    updateNode({
      api: params.api,
      assayMode: params.assayMode,
      column: params.column,
      createNew: !(finalValue && nameValues.includes(finalValue as string)),
      nameCellData: cellData,
      rowNode: params.node,
      tableUuid: params.tableUuid
    })
  } else if ( // Update value of existing cell
      cellData.uuid && (
      JSON.stringify(finalValue) !== JSON.stringify(ogValue) || (
      unitEnabled && finalValue !== '' && editUnit.value != ogUnit))) {
    const cellEditData: CellEditData = {
      fieldId: props.params?.fieldId,
      headerName: props.params?.fieldHeader.name,
      headerType: headerType,
      itemType: itemType as string,
      objCls: props.params?.fieldHeader.obj_cls,
      ogUnit: ogUnit,
      ogValue: ogValue,
      unit: editUnit.value,
      uuid: cellData.uuid,
      uuidRef: cellData.uuidRef,
      value: finalValue
    }
    updateCells(cellEditData, true, notifyCb)
    // Update sample list if sample has been renamed
    if (headerType === EDIT_HEADER_TYPE_NAME &&
        params.fieldId === params.sampleColId) {
      editStore.editContext!.samples[cellData.uuid]!.name = finalValue as string
    }
  }
  // TODO: Implement and call finalization func
})
</script>

<template>
  <div v-if="editValue !== undefined"
       :class="'sodar-ss-editor-cell ' + containerClass"
       :title="containerTitle">
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
</style>
