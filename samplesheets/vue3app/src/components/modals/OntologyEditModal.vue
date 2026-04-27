<script setup lang="ts">
import { ref, useTemplateRef } from 'vue'
import {
  BButtonGroup,
  BButton,
  BCol,
  BFormCheckbox,
  BFormInput,
  BFormSelect,
  BFormSelectOption,
  BInputGroup,
  BModal,
  BRow
} from 'bootstrap-vue-next'
import { useClipboard } from '@vueuse/core'

import ModalHeader from '@/components/modals/ModalHeader.vue'
import { useEditStore } from '@/stores/editStore.ts'
import { updateCells } from '@/utils/editUtils.ts'
import {
  type CellEditData,
  type EditOntologyRef,
  type GridCellEditorParams,
  type OntologyTermCellData,
  type OntologyTermResponseBody,
  type OntologyTermResponseRef,
  type SheetTableCellDataValue,
  type StudyEditConfigNodeField,
  type StudyEditContextOntology,
} from '@/types.ts'
import { EDIT_TERM_QUERY_MIN_LEN } from '@/constants.ts'

// Data and initial setup ------------------------------------------------------

// External
const clipboard = useClipboard()
const modalRef = useTemplateRef('ontologyEditModal')
const editStore = useEditStore()

// Refs
const cellData = ref<OntologyTermCellData | null>(null)
const editConfig = ref<StudyEditConfigNodeField | null>(null)
const editDataValid = ref<boolean>(true)
const insertDataValid = ref<boolean>(true)
const insertValue = ref<EditOntologyRef>({
  name: '', ontology_name: '', accession: ''
})
const modalTitle = ref<string>('Edit Ontology Term')
const searchOntologies = ref<Array<string>>([]) // Ontology IDs to search
const searchInput = ref<string>('')
const showModal = ref<boolean>(false)
const pasteData = ref<string>('')
const queryActive = ref<boolean>(false)
const queryLimit = ref<string>('')
const queryOrder = ref<boolean>(false)
const responseDetail = ref<string>('')
const responseDetailType = ref<string>('')
const sodarOntologies = ref<{ [key: string]: StudyEditContextOntology }>({})
const termOptions = ref<Array<OntologyTermResponseRef>>([])
const updated = ref<boolean>(false)

// Internal variables
let allowLimit: boolean = false
let editIdx: number | null = null
let editTermVal: string = '' // Stored as string for comparison
let params: GridCellEditorParams
let prevSearchInput: string = ''
let termRefresh: boolean = false

// Helpers ---------------------------------------------------------------------

// Insert OR replace term, return false is operation was cancelled
function addTerm (
    name: string,
    ontologyName: string,
    accession: string,
    obsolete: boolean
): boolean {
  const oName = ontologyName.toUpperCase()
  if (cellData.value?.value) {
    for (let i = 0; i < cellData.value?.value.length; i++) {
      if (cellData.value.value[i]?.name === name &&
          cellData.value.value[i]?.ontology_name === oName) {
        return false
      }
    }
  }
  if (!enableInsert()) cellData.value!.value = [] // Clear and replace
  cellData.value!.value.push({
    name: name,
    ontology_name: oName,
    accession: accession,
    obsolete: obsolete
  })
  return true
}

function copyValue () {
  clipboard.copy(JSON.stringify(cellData.value!.value))
  let s = ''
  if (cellData.value?.value.length !== 1) s = 's'
  if (params.notifyCb) {
    params.notifyCb(`Ontology term${s} copied into clipboard`, 'success', 0)
  }
}

function enableDelete (idx: number): boolean {
  return (!termRefresh && (editIdx === null || idx === editIdx))
}

function enableEdit (): boolean {
  return !termRefresh && editIdx === null
}

function enableEditSave (idx: number): boolean {
  const value = cellData.value?.value || []
  if (!value || idx > value.length - 1) {
    return false
  } else if (!value[idx]?.name ||
      !value[idx].ontology_name ||
      !value[idx].accession) {
    return false
  } else {
    for (let i = 0; i < value.length; i++) {
      if (i !== idx && ((value[idx].name === value[i]?.name &&
          value[idx].ontology_name === value[i]?.ontology_name) ||
          value[idx].accession === value[i]?.accession)) {
        return false
      }
    }
  }
  return true
}

function enableInsert (): boolean {
  return (editConfig.value &&
    (editConfig.value.allow_list ||
      cellData.value?.value.length === 0)) as boolean
}

function enableInsertInputs (): boolean {
  return editIdx === null
}

function enableInsertSave (): boolean {
  if (termRefresh ||
      !insertValue.value.name ||
      !insertValue.value.ontology_name ||
      !insertValue.value.accession) {
    return false
  } else {
    const value = cellData.value?.value || []
    for (let i = 0; i < value.length; i++) {
      if ((insertValue.value.name.toLowerCase() ===
            value[i]?.name.toLowerCase() &&
          insertValue.value.ontology_name.toLowerCase() ===
            (value[i]?.ontology_name as string).toLowerCase()) ||
          insertValue.value.accession === value[i]?.accession) {
        return false
      }
    }
  }
  return true
}

// Return true if term move button is enabled
function enableMove (idx: number, up: boolean): boolean {
  const valueLen = cellData.value?.value.length || 0
  return (
    !termRefresh &&
    editIdx === null &&
    valueLen > 1 && ((idx > 0 && up) || (idx !== valueLen - 1 && !up)))
}

function enableSearch (): boolean {
  return editIdx === null && !queryActive.value
}

function enableUpdate (): boolean {
  return editIdx === null && updated.value
}

function getLimitLabel (): string {
  if (allowLimit) return 'Allowed ontologies'
  return 'All ontologies'
}

function getQueryUrl (searchValue: string): string {
  // TODO: Should get root URL from server
  // TODO: Cleaner way to build querystring?
  let url = '/ontology/ajax/obo/term/query?s=' +
    encodeURIComponent(searchValue)
  if (queryLimit.value) {
    url += '&o=' + encodeURIComponent(queryLimit.value)
  } else if (
      editConfig.value?.ontologies &&
      editConfig.value.ontologies.length > 0) {
    for (let i = 0; i < searchOntologies.value.length; i++) {
      url += '&o=' + encodeURIComponent(searchOntologies.value[i] as string)
    }
  }
  if (!queryLimit.value && queryOrder.value) url += '&order=1'
  return url
}

function getTermNameClass (term: EditOntologyRef): string {
  if (term.obsolete || term.unknown) return 'text-danger'
  return ''
}

function getOntologyNameClass (term: EditOntologyRef): string {
  if (!term.ontology_name ||
      !sodarOntologies.value ||
      !(term.ontology_name.toUpperCase() in sodarOntologies.value)) {
    return 'text-danger'
  }
  return ''
}

function getOntologyNameInputClass (edit: boolean): string {
  if ((edit && !editDataValid.value) || (!edit && !insertDataValid.value)) {
    return 'text-danger'
  }
  return ''
}

function onOntologyNameInput (name: string, edit: boolean) {
  let valid: boolean = true
  if (allowLimit &&
      !editConfig.value?.ontologies?.includes(name.toUpperCase())) {
    valid = false
  }
  if (edit) editDataValid.value = valid
  else insertDataValid.value = valid
}

function onPasteInput () {
  let pasteOk: boolean = true
  let val: Array<EditOntologyRef> = []
  try {
    val = JSON.parse(pasteData.value)
  } catch (error) {
    if (params.notifyCb) {
      params.notifyCb('Error parsing pasted terms: ' + error, 'danger', 0)
      pasteOk = false
    }
  }
  // TODO: Check if array or fail?
  if (val && pasteOk && editConfig.value!.ontologies!.length > 0) {
    for (let i = 0; i < val.length; i++) {
      if (!editConfig.value?.ontologies?.includes(
          val[i]?.ontology_name as string)) {
        if (params.notifyCb) {
          params.notifyCb(
            'Ontology not allowed: ' + (val[i]?.ontology_name as string),
            'danger',
            0)
        }
        pasteOk = false
        break
      }
    }
  }
  if (val && pasteOk && !editConfig.value?.allow_list && val.length > 1) {
    if (params.notifyCb) {
      params.notifyCb('List of terms not allowed', 'danger', 0)
    }
    pasteOk = false
  }
  if (pasteOk) {
    cellData.value!.value = val
    if (params.notifyCb) {
      let s = ''
      if (val.length !== 1) s = 's'
      params.notifyCb(`Ontology term${s} replaced`, 'success', 0)
    }
    updated.value = true
  }
  pasteData.value = ''
}

function onSearchUpdate () {
  searchInput.value = searchInput.value.trim()
  if (!queryActive.value &&
      searchInput.value.length >= EDIT_TERM_QUERY_MIN_LEN &&
      searchInput.value != prevSearchInput) {
    // Set initial delay if typing
    // TODO: Recognize copy paste instead of typing and eliminate delay
    let delay = 350
    if (prevSearchInput) delay = 750
    submitTermQuery(delay)
  } else if (searchInput.value.length < EDIT_TERM_QUERY_MIN_LEN) {
    prevSearchInput = ''
    termOptions.value = []
  }
}

function onSearchParamUpdate () {
  if (searchInput.value.length >= EDIT_TERM_QUERY_MIN_LEN) {
    submitTermQuery(0)
  }
}

function onTermDeleteClick (idx: number) {
  cellData.value?.value.splice(idx, 1)
  updated.value = true
  editDataValid.value = true
  editIdx = null
  editTermVal = ''
}

function onTermEditClick (idx: number) {
  if (editIdx === null) {
    editTermVal = JSON.stringify(cellData.value?.value[idx])
    cellData.value!.value[idx]!.editing = true
    editIdx = idx
  } else {
    cellData.value!.value[idx]!.editing = false
    editIdx = null
    // Cleanup data (NOTE: trim() should already happen in field)
    cellData.value!.value[idx]!.ontology_name =
      cellData.value!.value[idx]!.ontology_name!.trim().toUpperCase()
    // TODO: Query for new value and set/unset unknown accordingly
    if (cellData.value?.value[idx] && 'unknown' in cellData.value.value[idx]) {
      delete cellData.value.value[idx].unknown
    }
    delete cellData.value!.value[idx]!.editing // Remove this from comparison
    if (JSON.stringify(cellData.value?.value[idx]) !== editTermVal) {
      updated.value = true
    }
    editTermVal = ''
  }
  editDataValid.value = true
}

function onTermInsertClick () {
  if (
    addTerm(
      insertValue.value.name,
      insertValue.value.ontology_name as string,
      insertValue.value.accession,
      false)) {
    updated.value = true
    resetInsertValue()
    insertDataValid.value = true
  }
}

function onTermMoveClick (idx: number, up: boolean) {
  let otherIdx: number
  if (up) otherIdx = idx - 1
  else otherIdx = idx + 1
  const tmpVal = Object.assign(
    cellData.value?.value[idx] as EditOntologyRef)
  cellData.value!.value[idx] = cellData.value?.value[otherIdx] as
    EditOntologyRef
  cellData.value!.value[otherIdx] = tmpVal
  updated.value = true
}

function onTermOptionClick (term: OntologyTermResponseRef) {
  if (term &&
      addTerm(
        term.name,
        term.ontology_name as string,
        term.accession,
        term.is_obsolete)) {
    updated.value = true
  }
}

function resetInsertValue () {
  insertValue.value = { name: '', ontology_name: '', accession: '' }
}

function resetModalState () {
  editDataValid.value = true
  insertDataValid.value = true
  pasteData.value = ''
  queryActive.value = false
  queryLimit.value = ''
  queryOrder.value = false
  responseDetail.value = ''
  responseDetailType.value = ''
  searchInput.value = ''
  sodarOntologies.value = editStore.editContext?.sodar_ontologies || {}
  termOptions.value = []
  updated.value = false
  editIdx = null
  prevSearchInput = ''
  termRefresh = false
  resetInsertValue() // Clears insertValue
}

function setupModalTitle (p: GridCellEditorParams) {
  // Set up title
  let title: string = ''
  const cols = p.api.getColumns()
  const parent = p.column.getOriginalParent()
  const isSourceNode: boolean = parent?.getColGroupDef()?.headerName === ''
  for (let i = 1; i < cols!.length - 1; i++) {
    const c = cols![i]
    if ((c?.getOriginalParent() === parent &&
        ['name', 'process_name'].includes(p.fieldHeader.type as string)) ||
        (i === 1 && isSourceNode)) {
      title = p.node.data[c?.getColId() as string].value + ': '
      break
    }
  }
  title += p.fieldHeader.value
  modalTitle.value = title
}

function setupOntologies () {
  // Set up ontologies for search
  const sodarOntologyKeys = Object.keys(
    sodarOntologies.value as
      { [key: string]: StudyEditContextOntology })
  let ontologyIds: Array<string>
  if (editConfig.value?.ontologies && editConfig.value?.ontologies.length > 0) {
    allowLimit = true
    ontologyIds = editConfig.value.ontologies
  } else {
    allowLimit = false
    ontologyIds =  sodarOntologyKeys
  }
  searchOntologies.value = []
  for (const id of ontologyIds) {
    if (sodarOntologyKeys.includes(id)) {
      searchOntologies.value.push(id)
    }
  }
  if (searchOntologies.value.length === 1) {
    queryLimit.value = searchOntologies.value[0] as string
  }
}

function submitTermQuery(delay: number | undefined) {
  if (delay === undefined) delay = 350
  queryActive.value = true
  setTimeout(() => {
    const searchValue = JSON.parse(JSON.stringify(searchInput.value))
    fetch(getQueryUrl(searchValue), {
      method: 'GET',
      credentials: 'same-origin',
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json'
      }
    }).then(data => data.json()).then(data => {
      const resData: OntologyTermResponseBody = data
      if ('detail' in data) {
        responseDetail.value = data.detail
        responseDetailType.value = data.detail_type || 'danger'
      } else {
        responseDetail.value = ''
        responseDetailType.value = ''
      }
      termOptions.value = resData.terms || []
      // If typing was stopped while querying and value has changed..
      const currentValue: string = JSON.parse(
        JSON.stringify(searchInput.value.trim()))
      if (currentValue != searchValue &&
          currentValue.length >= EDIT_TERM_QUERY_MIN_LEN) {
        submitTermQuery(0)
      } else {
        prevSearchInput = searchValue
        queryActive.value = false
      }
    })
  }, delay)
}

// API and lifecycle -----------------------------------------------------------

function show (p: GridCellEditorParams) {
  params = p
  // console.dir(p) // DEBUG
  // Copy value in case we cancel
  cellData.value = JSON.parse(JSON.stringify(p.value)) as OntologyTermCellData
  if (!cellData.value.value) cellData.value.value = []
  editConfig.value = p.editConfigField
  // Reset states and set up data
  resetModalState() // Make sure to call reset before setting up other data!
  setupModalTitle(p)
  setupOntologies()
  // Display modal
  showModal.value = true
}

function hideModal (save: boolean) {
  if (params && save && updated.value) {
    // Cleanup editor metadata
    for (let i = 0; i < cellData.value!.value?.length; i++) {
      delete cellData.value?.value[i]?.editing
      delete cellData.value?.value[i]?.obsolete
      delete cellData.value?.value[i]?.unknown
    }
    // Update value
    const cellEditData: CellEditData = {
      fieldId: params.fieldId as string,
      headerName: params.fieldHeader.name,
      headerType: params.fieldHeader.type || '',
      itemType: params.fieldHeader.item_type || '',
      objCls: params.fieldHeader.obj_cls,
      ogValue: params.value?.value,
      uuid: cellData.value?.uuid,
      value: cellData.value?.value as SheetTableCellDataValue
    }
    updateCells(cellEditData, true, params.notifyCb)
  }
  params.api.stopEditing(!save)
  modalRef.value?.hide()
}

defineExpose({ show })
</script>

<template>
  <BModal
      id="sodar-ss-ontology-edit-modal"
      ref="ontologyEditModal"
      v-model="showModal"
      size="xl"
      centered no-footer no-animation no-close-on-backdrop no-close-on-esc
      teleport-disabled>
    <template #header>
      <ModalHeader
          :modal-ref="modalRef"
          :title="modalTitle"
          :hide-close-button="true">
        <template v-slot:extend>
          <BInputGroup class="sodar-header-input-group justify-content-end">
            <BButton
                variant="secondary"
                id="sodar-ss-ontology-btn-clip-copy"
                title="Copy terms to clipboard"
                @click="copyValue()"
                :disabled="cellData?.value.length === 0">
              <i class="iconify" data-icon="mdi:clipboard-text-multiple"></i>
            </BButton>
            <!-- NOTE: Using regular input because BFormInput fails here -->
            <input
                id="sodar-ss-ontology-input-clip-paste"
                v-model="pasteData"
                @input="onPasteInput()"
                placeholder="Paste"
                title="Paste and replace terms" />
          </BInputGroup>
        </template>
      </ModalHeader>
    </template>
    <div id="sodar-ss-ontology-edit-content">
      <div v-if="cellData"
          class="w-100"
          id="sodar-ss-ontology-modal-ui">
        <!-- Ontology term search -->
        <div v-if="searchOntologies.length > 0">
          <BRow>
            <BCol class="col-md-3 pl-0 pr-2">
              <BFormInput
                  id="sodar-ss-ontology-input-search"
                  v-model="searchInput"
                  placeholder="Search for term"
                  @update:model-value="onSearchUpdate()"
                  :disabled="editIdx !== null"
                  autofocus />
            </BCol>
            <BCol class="col-md-2 px-0">
              <BFormSelect
                  v-model="queryLimit"
                  id="sodar-ss-ontology-select-limit"
                  @change="onSearchParamUpdate()"
                  :disabled="!enableSearch() || searchOntologies.length === 1">
                <BFormSelectOption
                    v-if="searchOntologies.length > 1"
                    value="">
                  {{ getLimitLabel() }}
                </BFormSelectOption>
                <BFormSelectOption
                    v-for="(o, oIdx) in searchOntologies"
                    :key="oIdx"
                    :value="o">
                  {{ o }}
                </BFormSelectOption>
              </BFormSelect>
            </BCol>
            <BCol class="col-md-3 pl-3 text-nowrap">
              <div id="sodar-ss-ontology-order">
                <BFormCheckbox
                    id="sodar-ss-ontology-order-check"
                    v-model="queryOrder"
                    @change="onSearchParamUpdate()"
                    :disabled="queryLimit !== ''">
                  Sort by ontology
                </BFormCheckbox>
              </div>
            </BCol>
          </BRow>
          <!-- NOTE: Using regular select here for now, see #2456 -->
          <select
              id="sodar-ss-ontology-select-term"
              size="8"
              :disabled="!enableSearch()">
            <option
                v-for="(term, termIdx) in termOptions"
                :key="termIdx"
                class="sodar-ss-ontology-select-term-option px-2"
                @dblclick="onTermOptionClick(term)">
              [{{ term.term_id }}] {{ term.name }} <span v-if="term.is_obsolete">&lt;OBSOLETE&gt;</span>
            </option>
          </select>
        </div>
        <!-- Alerts -->
        <div v-else
             class="alert alert-warning sodar-ss-ontology-alert pl-3"
             id="sodar-ss-ontology-alert-no-imports">
          No valid imported ontologies for this column found! Only manual
          ontology value entry is available. Ontologies can be imported using
          the <code>ontologyaccess</code> app.
        </div>
        <div v-if="responseDetail"
             :class="'alert sodar-ss-ontology-alert alert-' +
                     responseDetailType"
             id="sodar-ss-ontology-alert-res-detail">
          {{ responseDetail }}
        </div>
        <div v-else-if="!enableInsert()"
             class="alert alert-warning sodar-ss-ontology-alert pl-3"
             id="sodar-ss-ontology-alert-no-list">
          Multiple terms not allowed in this column, current entry will be
          overwritten.
        </div>
        <div v-else
             id="sodar-ss-alert-placeholder sodar-ss-ontology-alert">
        </div>
        <table
            class="table sodar-card-table"
            id="sodar-ss-ontology-term-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Ontology</th>
              <th>Accession</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(term, termIdx) in cellData.value"
                :key="termIdx"
                class="sodar-ss-ontology-term-item">
              <!-- Content cells for display -->
              <td v-if="!term.editing"
                  :class="'sodar-ss-ontology-term-display ' +
                          'sodar-ss-ontology-term-name ' +
                          getTermNameClass(term)">
                {{ term.name }}
                <i v-if="term.obsolete"
                   class="iconify text-danger
                          sodar-ss-ontology-icon-obsolete"
                   data-icon="mdi:alert"
                   title="This term is obsolete">
                </i>
                <i v-else-if="term.unknown"
                   class="iconify text-warning
                          sodar-ss-ontology-icon-unknown"
                   data-icon="mdi:alert"
                   title="Term name not found in given ontologies">
                </i>
              </td>
              <td v-if="!term.editing"
                  :class="'sodar-ss-ontology-term-display ' +
                          'sodar-ss-ontology-term-obo ' +
                          getOntologyNameClass(term)">
                {{ term.ontology_name }}
                <i v-if="!term.ontology_name"
                   class="iconify text-danger
                          sodar-ss-ontology-icon-obo-empty"
                   data-icon="mdi:alert"
                   title="No ontology name given">
                </i>
                <i v-else-if="!sodarOntologies ||
                              !(term.ontology_name in sodarOntologies)"
                   class="iconify text-danger
                          sodar-ss-ontology-icon-obo-not-found"
                   data-icon="mdi:alert"
                   title="Ontology not found in SODAR. Please ask for an
                          administrator to import the ontology for term and
                          URL lookup.">
                </i>
              </td>
              <td v-if="!term.editing"
                  class="sodar-ss-ontology-term-display
                         sodar-ss-ontology-term-acc">
                <div class="sodar-ss-ontology-url">
                  <a :href="term.accession" target="_blank">
                    {{ term.accession }}
                  </a>
                </div>
              </td>
              <!-- Content cells for editing -->
              <td v-if="term.editing"
                  class="sodar-ss-ontology-term-edit">
                <BFormInput
                  class="sodar-ss-ontology-row-input"
                  v-model.trim="cellData.value[termIdx]!.name" />
              </td>
              <td v-if="term.editing"
                  class="sodar-ss-ontology-term-edit">
                <BFormInput
                  :class="'sodar-ss-ontology-row-input ' +
                          getOntologyNameInputClass(true)"
                  v-model.trim="cellData.value[termIdx]!.ontology_name"
                  @update:model-value="onOntologyNameInput(
                                         $event as string, true)" />
              </td>
              <td v-if="term.editing"
                  class="sodar-ss-ontology-term-edit">
                <BFormInput
                  class="sodar-ss-ontology-row-input"
                  v-model.trim="cellData.value[termIdx]!.accession" />
              </td>
              <!-- Control cell -->
              <td class="text-right">
                <BButton
                    v-if="editConfig && editConfig.allow_list"
                    variant="primary"
                    class="sodar-list-btn sodar-ss-row-btn
                           sodar-ss-ontology-btn-move
                           sodar-ss-ontology-btn-move-up mr-1"
                    title="Move term backwards in list"
                    :disabled="!enableMove(termIdx, true)"
                    @click="onTermMoveClick(termIdx, true)">
                  <i class="iconify" data-icon="mdi:arrow-up-thick"></i>
                </BButton>
                <BButton
                    v-if="editConfig && editConfig.allow_list"
                    variant="primary"
                    class="sodar-list-btn sodar-ss-row-btn
                           sodar-ss-ontology-btn-move
                           sodar-ss-ontology-btn-move-down mr-1"
                    title="Move term forward in list"
                    :disabled="!enableMove(termIdx, false)"
                    @click="onTermMoveClick(termIdx, false)">
                  <i class="iconify" data-icon="mdi:arrow-down-thick"></i>
                </BButton>
                <BButton
                    v-if="term.editing"
                    variant="primary"
                    class="sodar-list-btn sodar-ss-row-btn
                           sodar-ss-ontology-btn-stop mr-1"
                    title="Stop editing term"
                    @click="onTermEditClick(termIdx)"
                    :disabled="!enableEditSave(termIdx) || !editDataValid">
                  <i class="iconify" data-icon="mdi:check-bold"></i>
                </BButton>
                <BButton
                    v-else
                    variant="primary"
                    class="sodar-list-btn sodar-ss-row-btn
                           sodar-ss-ontology-btn-edit mr-1"
                    title="Edit term"
                    @click="onTermEditClick(termIdx)"
                    :disabled="!enableEdit()">
                  <i class="iconify" data-icon="mdi:lead-pencil"></i>
                </BButton>
                <BButton
                    variant="danger"
                    class="sodar-list-btn sodar-ss-row-btn
                           sodar-ss-ontology-btn-delete"
                    title="Delete term"
                    :disabled="!enableDelete(termIdx)"
                    @click="onTermDeleteClick(termIdx)">
                  <i class="iconify" data-icon="mdi:close-thick"></i>
                </BButton>
              </td>
            </tr>
            <!-- Insert row -->
            <tr v-if="enableInsert()"
                id="sodar-ss-ontology-insert-row">
              <td>
                <BFormInput
                    class="sodar-ss-ontology-row-input"
                    v-model.trim="insertValue.name"
                    :disabled="!enableInsertInputs()" />
              </td>
              <td>
                <BFormInput
                    :class="'sodar-ss-ontology-row-input' +
                            getOntologyNameInputClass(false)"
                    v-model.trim="insertValue.ontology_name"
                    @update:model-value="onOntologyNameInput(
                                         $event as string, false)"
                    :disabled="!enableInsertInputs()" />
              </td>
              <td>
                <BFormInput
                    class="sodar-ss-ontology-row-input"
                    v-model.trim="insertValue.accession"
                    :disabled="!enableInsertInputs()" />
              </td>
              <td class="text-right">
                <BButton
                    variant="primary"
                    class="sodar-list-btn sodar-ss-row-btn"
                    id="sodar-ss-ontology-btn-insert"
                    title="Insert ontology term"
                    @click="onTermInsertClick()"
                    :disabled="!enableInsertSave() || !insertDataValid">
                  <i class="iconify" data-icon="mdi:plus-thick"></i>
                </BButton>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    <div id="sodar-ss-ontology-edit-update-container">
      <!-- Update/cancel buttons -->
      <BButtonGroup
          class="pull-right"
          id="sodar-ss-ontology-btn-group">
        <BButton
            variant="secondary"
            id="sodar-ss-ontology-btn-cancel"
            @click="hideModal(false)">
          <i class="iconify" data-icon="mdi:close-thick"></i> Cancel
        </BButton>
        <BButton
            variant="primary"
            id="sodar-ss-ontology-btn-update"
            :disabled="!enableUpdate()"
            @click="hideModal(true)">
          <i class="iconify" data-icon="mdi:check-bold"></i> Update
        </BButton>
      </BButtonGroup>
    </div>
  </BModal>
</template>

<style scoped>
div#sodar-ss-ontology-modal-ui {
  min-height: 550px !important;
}
div#sodar-ss-ontology-order {
  white-space: nowrap !important;
  padding-top: 7px;
}
table#sodar-ss-ontology-term-table tbody tr td:not(:last-child) {
  padding-top: 14px; /* Hack for padding vs button */
}
table#sodar-ss-ontology-term-table tbody tr td:nth-child(1) {
  width: 450px;
}
table#sodar-ss-ontology-term-table tbody tr td:nth-child(2) {
  width: 150px;
}
table#sodar-ss-ontology-term-table tbody tr td:nth-child(3) {
  max-width: 275px;
}
table#sodar-ss-ontology-term-table tbody tr td:nth-child(4) {
  white-space: nowrap !important;
  width: 150px;
}
tr.sodar-ss-ontology-term-item td {
  height: 54px !important;
}
div.sodar-ss-ontology-url {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  word-wrap: anywhere;
  min-width: 75px;
}
tr#sodar-ss-ontology-insert-row td {
  vertical-align: middle;
}
/* HACK: Maybe consider refactoring :) */
.sodar-ss-ontology-row-input {
  margin-top: -2px;
  margin-left: -6px;
  padding-left: 5px;
  height: 28px;
}
#sodar-ss-ontology-input-search,
#sodar-ss-ontology-select-limit,
#sodar-ss-ontology-select-term {
  margin-bottom: 8px;
}
#sodar-ss-ontology-select-limit {
  width: 100% !important;
  height: 38px;
  border: 1px solid #CED4DA;
  border-radius: 4px;
  padding-left: 5px;
  padding-right: 5px;
}
#sodar-ss-ontology-select-term {
  width: 100% !important;
  height: 200px;
  border: 1px solid #CED4DA;
  border-radius: 4px;
}
.sodar-ss-ontology-select-term-option {
  color: #495057;
  /* NOTE: Bootstrap py-* classes don't work well here, BS4/BS5 conflict? */
  padding-top: 2px;
  padding-bottom: 2px;
}
div.sodar-ss-ontology-alert {
  margin-bottom: 0;
}
div#sodar-ss-alert-placeholder {
  height: 50px;
}
tr#sodar-ss-ontology-insert-row td:last-child {
  padding-top: 14px;
}
#sodar-ss-ontology-btn-clip-copy {
  padding-left: 8px;
  padding-right: 8px;
  border-top-right-radius: 0 !important;
  border-bottom-right-radius: 0 !important;
}
#sodar-ss-ontology-input-clip-paste {
  max-width: 60px;
  border: 1px solid #CED4DA;
  border-top-right-radius: 4px;
  border-bottom-right-radius: 4px;
  padding-left: 8px;
  padding-right: 5px;
}
#sodar-ss-ontology-input-clip-paste:focus {
  outline: none;
}
</style>
