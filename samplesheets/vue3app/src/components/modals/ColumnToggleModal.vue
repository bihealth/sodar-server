<script setup lang="ts">
import { ref, useTemplateRef } from 'vue'
import {
  BButton,
  BFormCheckbox,
  BFormInput,
  BInputGroup,
  BModal,
  useToast,
  type CheckboxValue
} from 'bootstrap-vue-next'
import {
  type ColDef,
  type ColGroupDef,
  type GridApi
} from 'ag-grid-community'

import ModalHeader from '@/components/modals/ModalHeader.vue'
import { TOAST_INTERVAL_DEFAULT } from '@/constants.ts'
import {
  type SheetTableCellData,
  type SheetTableRowData,
  type StudyDisplayConfigNode
} from '@/types.ts'
import { useAppStore } from '@/stores/appStore.ts'
import { useTableStore } from '@/stores/tableStore.ts'

interface DisplayColGroup {
  headerName: string,
  headerClass: string,
  children: Array<ColDef>
}

// Stores
const appStore = useAppStore()
const tableStore = useTableStore()
// Modal setup
const modalRef = useTemplateRef('columnToggleModal')
const showModal = ref<boolean>(false)
// Composables
const { create } = useToast()
// Constants
const configUrl = '/samplesheets/ajax/display/update/' +
  appStore.currentStudyUuid

// Reactive vars
const checkVals = ref<Array<Array<boolean | null>>>([])
const displayCols = ref<Array<DisplayColGroup>>([]) // Formerly columnList
const displayConfig = ref<Array<StudyDisplayConfigNode>>([])
const filterInput = ref<string>('')
const modalTitle = ref<string>('')

// Regular vars
let colValueStatus: {[key: string]: boolean} // Formerly columnValues
let colDefs: Array<ColGroupDef>
let colsUpdated: boolean = false
let gridApi: GridApi
let rowData: Array<SheetTableRowData>

// Return column group to be displayed
function getDisplayColGroup (
    colDef: ColGroupDef,
    firstColIdx: number,
    headerName: string | undefined = undefined,
    headerClass: string | undefined = undefined
): DisplayColGroup {
  const ret: DisplayColGroup = {
    headerName: headerName || colDef.headerName as string,
    headerClass: headerClass || colDef.headerClass as string,
    children: []
  }
  for (let i = firstColIdx; i < colDef.children.length; i++) {
    const child = colDef.children[i] as ColDef
    child.context.visibleInList = true
    ret.children.push(child)
  }
  return ret
}

// Return top header classes as string
function getTopHeaderClass (topHeader: ColGroupDef): string {
  return (topHeader.headerClass as Array<string>).join(' ')
}

// Return true if column values have been filled in for any cell
function getColValueStatus (header: ColDef): boolean {
  return colValueStatus[header.field as string] as boolean
}

// Get checkbox state
function getCheckState (
    header: ColDef,
    topIdx: number,
    headerIdx: number
): boolean {
  // Update via local lookup table
  const savedVal = checkVals.value[topIdx]![headerIdx]
  if (savedVal !== null) return savedVal as boolean
  // If not yet in lookup table, return column visibility setting
  return gridApi?.getColumn(header.field as string)?.isVisible() as boolean
}

// Update column state
function onColUpdate (
    value: CheckboxValue | undefined,
    header: ColDef,
    topIdx: number,
    headerIdx: number
) {
  // Toggle column visibility in ag-grid
  gridApi.setColumnsVisible([header.field as string], value as boolean)
  // Update user display config
  const realHeaderIdx = headerIdx + 1 // The first field is always skipped
  displayConfig.value[topIdx]!.fields[realHeaderIdx]!.visible = value as boolean
  // Update check value lookup
  checkVals.value[topIdx]![headerIdx] = value as boolean
  colsUpdated = true
}

// Update column state for all columns in top column group
function onGroupUpdate (topHeader: ColGroupDef, topIdx: number) {
  // Toggle all fields in group
  let toggle = false
  for (let i = 0; i < topHeader.children.length; i++) {
    if (!gridApi?.getColumn(
        (topHeader.children[i] as ColDef).field as string)?.isVisible()) {
      toggle = true
      break
    }
  }
  const fields = []
  for (let i = 0; i < topHeader.children.length; i++) {
    fields.push((topHeader.children[i] as ColDef).field as string)
  }
  gridApi.setColumnsVisible(fields, toggle)
  // Update user display config
  const fieldLen = displayConfig.value[topIdx]!.fields.length
  for (let i = 1; i < fieldLen; i++) { // NOTE: Start at 1 to ignore name
    displayConfig.value[topIdx]!.fields[i]!.visible = toggle
  }
  // Update check value lookup
  for (let i = 0; i < checkVals.value[topIdx]!.length; i++) {
    checkVals.value[topIdx]![i] = toggle
  }
  colsUpdated = true
}

// Update column list for filter input
function updateFilter () {
  const inputVal = filterInput.value.toLowerCase()
  for (let i = 0; i < displayCols.value.length; i++) {
    for (let j = 0; j < displayCols.value[i]!.children.length; j++) {
      const child = (displayCols.value[i]?.children[j] as ColDef)
      child.context.visibleInList = !!(inputVal.length === 0 ||
        child.headerName?.toLowerCase().includes(inputVal))
    }
  }
}

// Save current config as default value
function saveDefaultConfig () {
  if (colsUpdated) postUpdate(true)
}

// Post display config update request
function postUpdate (setDefault: boolean) {
  fetch(configUrl, {
    method: 'POST',
    body: JSON.stringify({
      study_config: tableStore.studyDisplayConfig,
      set_default: setDefault
    }),
    credentials: 'same-origin',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      'X-CSRFToken': appStore.sodarContext?.csrf_token as string
    }
  }).then(data => data.json())
    .then(data => {
      if (data.detail === 'ok') {
        let toastBody = 'Display configuration saved'
        if (setDefault) toastBody += ' as default'
        create({
          body: toastBody,
          variant: 'success',
          modelValue: TOAST_INTERVAL_DEFAULT
        })
      }
    }).catch(function (error) {
      create({
        body: 'Error saving display config: ' + error.detail,
        variant: 'danger',
        modelValue: TOAST_INTERVAL_DEFAULT
      })
    })
}

// Show modal
function show (tableUuid: string, assayMode: boolean) {
  checkVals.value = []
  colValueStatus = {}
  colsUpdated = false
  displayCols.value = []
  const titleType = assayMode ? 'Assay' : 'Study'
  modalTitle.value = 'Toggle ' + titleType + ' Columns'

  if (!assayMode) {
    colDefs = tableStore.columnDefs.study
    displayConfig.value = (
      tableStore.studyDisplayConfig?.nodes as Array<StudyDisplayConfigNode>
    )
    gridApi = tableStore.gridApi.study as GridApi
    rowData = tableStore.rowData.study
  } else {
    colDefs = tableStore.columnDefs.assays[tableUuid] as Array<ColGroupDef>
    displayConfig.value = (
      tableStore.studyDisplayConfig?.assays[tableUuid]?.nodes as
        Array<StudyDisplayConfigNode>
    )
    gridApi = tableStore.gridApi.assays[tableUuid] as GridApi
    rowData = tableStore.rowData.assays[tableUuid] as Array<SheetTableRowData>
  }

  // Get top column group length and last index for iteration
  let topColLen = colDefs.length
  const lastColIdx = colDefs.length - 1
  const lastColName = colDefs[lastColIdx]?.headerName?.toLowerCase()
  const rightColumn = ['irods', 'links', 'edit'].includes(lastColName as string)
  if (rightColumn) topColLen -= 1

  // Build column list
  // First build source column separately
  // This is needed because we have to split the top header group
  displayCols.value.push(
      getDisplayColGroup(
        colDefs[2] as ColGroupDef,
        0, // First column index is 0 for the second source header group
        colDefs[1]?.headerName as string,
        colDefs[1]?.headerClass as string
      )
  )
  const firstTopIdx = 3 // First top header index for modification
  for (let i = firstTopIdx; i < topColLen; i++) {
    displayCols.value.push(getDisplayColGroup(colDefs[i] as ColGroupDef, 1))
  }

  // Populate colValueStatus (so we only have to iterate once)
  for (let i = 1; i < topColLen; i++) {
    for (let j = 0; j < colDefs[i]!.children.length; j++) {
      colValueStatus[
       (colDefs[i]!.children[j] as ColDef).field as string] = false
    }
  }
  for (const key in colValueStatus) {
    for (let i = 0; i < rowData.length - 1; i++) {
      if ((rowData[i]![key] as SheetTableCellData).value) {
        colValueStatus[key] = true
        break
      }
    }
  }

  // Populate checkVals (initially with null)
  // NOTE: We can't catch column visibility updates for the checkboxes, so we
  //       need to use a "lookup table".. Better approaches? Please open a PR :)
  for (let i = 0; i < displayCols.value.length; i++) {
    checkVals.value.push(
      new Array(displayCols.value[i]?.children.length).fill(null))
  }
  showModal.value = true
}
// Hide modal
function hideModal () {
  if (colsUpdated) postUpdate(false)
}
defineExpose({ show, hideModal })
</script>

<template>
  <BModal
      id="sodar-ss-col-toggle-modal"
      ref="columnToggleModal"
      v-model="showModal"
      size="md"
      @hide="hideModal"
      no-footer no-animation teleport-disabled>
    <template #header>
      <ModalHeader
          :modal-ref="modalRef"
          :title="modalTitle">
        <template v-slot:extend>
          <BInputGroup class="sodar-header-input-group justify-content-end">
            <BButton
                variant="secondary"
                id="sodar-ss-col-toggle-save-btn"
                title="Save current configuration as default for all project
                       members"
                @click="saveDefaultConfig">
              <i class="iconify" data-icon="mdi:content-save"></i>
            </BButton>
            <BFormInput
                id="sodar-ss-col-toggle-modal-filter"
                size="sm"
                placeholder="Filter"
                v-model="filterInput"
                @keyup="updateFilter">
            </BFormInput>
          </BInputGroup>
        </template>
      </ModalHeader>
    </template>
    <div v-if="displayCols"
           id="sodar-ss-col-toggle-modal-content">
      <table
          v-for="(topHeader, topIdx) in displayCols"
          :key="topIdx"
          class="table sodar-card-table sodar-ss-col-toggle-table">
        <thead>
          <tr class="sodar-ss-col-toggle-top-header">
            <th :class="'sodar-ss-col-toggle-top-title ' +
                        getTopHeaderClass(topHeader)">
              {{ topHeader.headerName }}
            </th>
            <th :class="'sodar-ss-col-toggle-top-btn ' +
                        getTopHeaderClass(topHeader)">
              <BButton
                  variant="secondary"
                  class="sodar-list-btn sodar-ss-toggle-node-btn pull-right"
                  title="Toggle all"
                  @click="onGroupUpdate(topHeader, topIdx)">
                <i class="iconify" data-icon="mdi:checkbox-multiple-marked"></i>
              </BButton>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(header, headerIdx) in topHeader.children"
              :key="headerIdx"
              v-show="header.context.visibleInList"
              class="sodar-ss-col-toggle-field">
            <td>
              {{ header.headerName }}
              <span v-if="appStore.editMode &&
                          header.cellRendererParams.fieldEditable"
                    class="text-muted font-italic pull-right
                           sodar-ss-toggle-field-info
                           sodar-ss-toggle-field-editable">
                Editable
              </span>
              <span v-else-if="!getColValueStatus(header)"
                    class="text-muted font-italic pull-right
                           sodar-ss-toggle-field-info
                           sodar-ss-toggle-field-no-data">
                No data
              </span>
            </td>
            <td class="text-center">
              <BFormCheckbox
                  class="sodar-ss-toggle-field-check"
                  :key="Math.random().toString(36).substring(3)"
                  :checked="getCheckState(header, topIdx, headerIdx)"
                  @update:model-value="onColUpdate(
                    $event, header, topIdx, headerIdx)"
                  plain>
              </BFormCheckbox>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </BModal>
</template>

<style scoped>
table.sodar-ss-col-toggle-table thead tr th,
table.sodar-ss-col-toggle-table tbody tr td {
  height: 38px;
  line-height: 24px;
  padding-top: 0;
  padding-bottom: 0;
  vertical-align: middle;
}
table.sodar-ss-col-toggle-table thead tr th {
  border-top: 0 !important;
  border-bottom: 1px solid #ffffff !important;
}
table.sodar-ss-col-toggle-table tbody tr:first-child td {
  border-top: 0;
}
table.sodar-ss-col-toggle-table thead th:first-child,
table.sodar-ss-col-toggle-table tbody td:first-child {
  width: 100%;
}
#sodar-ss-col-toggle-modal-filter {
  max-width: 125px;
}
/* Rounding CSS fails by default, possibly due to BS4 conflict? */
#sodar-ss-col-toggle-save-btn {
  padding-left: 8px;
  padding-right: 8px;
  border-top-right-radius: 0 !important;
  border-bottom-right-radius: 0 !important;
}
</style>
