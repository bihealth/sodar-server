<script setup lang="ts">
import { nextTick, ref, useTemplateRef } from 'vue'
import {
  BButtonGroup,
  BButton,
  BFormCheckbox,
  BFormInput,
  BFormSelect,
  BFormSelectOption,
  BFormTextarea,
  BInputGroup,
  BModal
} from 'bootstrap-vue-next'
import { type ColDef, type GridApi } from 'ag-grid-community'
import { useClipboard } from '@vueuse/core'

import InfoIcon from '@/components/InfoIcon.vue'
import ModalHeader from '@/components/modals/ModalHeader.vue'
import ColumnConfigModalSeparator from '@/components/modals/ColumnConfigModalSeparator.vue'
import { useAppStore } from '@/stores/appStore.ts'
import { useEditStore } from '@/stores/editStore.ts'
import { useTableStore } from '@/stores/tableStore.ts'
import { updateCells } from '@/utils/editUtils.ts'
import {
  type CellEditData,
  type EditConfigRequestBody,
  type GenericResponseBody,
  type HeaderEditRendererParams,
  type SheetTableCellDataValue,
  type SheetTableOntologyRef,
  type StudyEditConfigNodeField
} from '@/types.ts'
import {
  EDIT_CONFIG_ACTION_UPDATE,
  EDIT_COL_TYPE_CONTACT,
  EDIT_COL_TYPE_DATE,
  EDIT_COL_TYPE_EXT_LINKS,
  EDIT_COL_TYPE_LINK,
  EDIT_COL_TYPE_NAME,
  EDIT_COL_TYPE_NUMERIC,
  EDIT_COL_TYPE_ONTOLOGY,
  EDIT_COL_TYPE_PROTOCOL,
  EDIT_COL_TYPE_UNIT,
  EDIT_FORMAT_DATE,
  EDIT_FORMAT_DOUBLE,
  EDIT_FORMAT_EXT,
  EDIT_FORMAT_INTEGER,
  EDIT_FORMAT_ONTOLOGY,
  EDIT_FORMAT_SELECT,
  EDIT_FORMAT_STRING,
  EDIT_HEADER_TYPE_EXTRACT_LABEL,
  EDIT_ITEM_TYPE_SOURCE,
  EDIT_REGEX,
  OBO_ID_HP,
  OBO_ID_OMIM,
  OBO_ID_ORDO,
  OBO_HEADER_HP,
  OBO_HEADER_OMIM,
  OBO_HEADER_ORDO,
  VARIANT_DANGER,
  VARIANT_SUCCESS,
} from '@/constants.ts'

// Constants -------------------------------------------------------------------

const CONFIG_COPY_KEYS: Array<string> = [
  'allow_list',
  'default',
  'editable',
  'format',
  'ontologies',
  'regex',
  'unit_default',
]
const DISABLE_COPY_COLS: Array<string> = [
  EDIT_COL_TYPE_CONTACT,
  EDIT_COL_TYPE_DATE,
  EDIT_COL_TYPE_EXT_LINKS,
  EDIT_COL_TYPE_LINK,
  EDIT_COL_TYPE_NAME,
  EDIT_COL_TYPE_PROTOCOL
]
const FORMAT_OPTIONS_DEFAULT: Array<string> = [
  EDIT_FORMAT_STRING,
  EDIT_FORMAT_INTEGER,
  EDIT_FORMAT_DOUBLE,
  EDIT_FORMAT_SELECT
]
const FORMAT_OPTIONS_UNIT: Array<string> = [
  EDIT_FORMAT_INTEGER,
  EDIT_FORMAT_DOUBLE
]
const NUM_COL_TYPES: Array<string> = [
  EDIT_COL_TYPE_NUMERIC,
  EDIT_COL_TYPE_UNIT
]
const NUM_FORMATS: Array<string> = [
  EDIT_FORMAT_DOUBLE,
  EDIT_FORMAT_INTEGER
]
const VALIDATE_TARGET_DEFAULT: string = 'default'
const VALIDATE_TARGET_RANGE: string = 'range'
const VALIDATE_TARGET_REGEX: string = 'regex'
const VALIDATE_TARGET_SELECT: string = 'select'

// Interfaces ------------------------------------------------------------------

interface ValidState {
  [VALIDATE_TARGET_DEFAULT]: boolean
  [VALIDATE_TARGET_RANGE]: boolean
  [VALIDATE_TARGET_REGEX]: boolean
  [VALIDATE_TARGET_SELECT]: boolean
}

// External Data ---------------------------------------------------------------

const clipboard = useClipboard()
const appStore = useAppStore()
const editStore = useEditStore()
const tableStore = useTableStore()
const modalRef = useTemplateRef('columnConfigModal')

// Refs ------------------------------------------------------------------------

const classDefault = ref<string>('')
const colType = ref<string | null>(null)
const config = ref<StudyEditConfigNodeField | null>(null)
const configPasteInput = ref<string>('')
const defaultFill = ref<boolean>(false)
const defaultFillEnable = ref<boolean>(false)
const formatOptions = ref<Array<string>>([])
const itemType = ref<string | undefined>(undefined)
const modalTitle = ref<string>('')
const ontologyDefaultInput = ref<string>('')
const ontologyInsert = ref<string>('')
const ontologyPreset = ref<boolean>(false) // Formerly specialOntologyCol
const ontologySelect = ref<Array<string>>([]) // formerly selectOntologies
const rangeMax = ref<string>('')
const rangeMin = ref<string>('')
const showModal = ref<boolean>(false)
const unitEnable = ref<boolean>(false)
const unitOptions = ref<string>('')
const validState = ref<ValidState>({
  [VALIDATE_TARGET_DEFAULT]: true,
  [VALIDATE_TARGET_RANGE]: true,
  [VALIDATE_TARGET_REGEX]: true,
  [VALIDATE_TARGET_SELECT]: true,
}) // Formerly inputValid
const valueOptions = ref<string>('')

// Internal Vars ---------------------------------------------------------------

let gridApis: Array<GridApi>
let fieldId: string = ''
let ogColType: string // Original column type before editing
let params: HeaderEditRendererParams
const updateUrl = '/samplesheets/ajax/config/update/' + appStore.projectUuid

// Helpers ---------------------------------------------------------------------

// Formerly cleanupFieldConfig()
function cleanupConfig (c: StudyEditConfigNodeField): StudyEditConfigNodeField {
  // Update config for select field
  if (c.format === EDIT_FORMAT_SELECT) {
    delete c.regex
    if (valueOptions.value.length > 0) {
      c.options = valueOptions.value.split('\n')
    } else c.options = []
  } else delete c.options
  // Remove range and unit if not integer/double
  if (c.format && !NUM_FORMATS.includes(c.format)) {
    delete c.range
    delete c.unit
    delete c.unit_default
  } else {
    // Set up range in return data
    if (rangeMin.value && rangeMax.value) {
      c.range = [rangeMin.value, rangeMax.value]
    } else delete c.range
    if (!unitEnable.value || unitOptions.value.length === 0) {
      delete c.unit
    } else c.unit = unitOptions.value.split('\n')
  }
  // Remove ontologies if not ontology format
  if (c.format !== EDIT_FORMAT_ONTOLOGY) {
    delete c.ontologies
  }
  return c
}

function copyConfig () {
  const copyConfig = JSON.parse(JSON.stringify(config.value))
  delete copyConfig.name
  delete copyConfig.type
  cleanupConfig(copyConfig)
  clipboard.copy(JSON.stringify(copyConfig))
  if (params.notifyCb) {
    params.notifyCb('Configuration copied into clipboard', VARIANT_SUCCESS)
  }
}

function enableCopy (): boolean {
  return !(DISABLE_COPY_COLS.includes(colType.value as string))
}

function enableOntologyMove (idx: number, up: boolean): boolean {
  return (
    (config.value?.ontologies &&
    config.value?.ontologies.length > 1) &&
    ((idx > 0 && up) ||
    (idx !== config.value?.ontologies.length - 1 && !up))) as boolean
}

function enableUpdate (): boolean {
  return Object.values(validState.value).every(x => x === true)
}

function getFormValidClass (target: string): string {
  return validState.value[target] ? '' : 'text-danger'
}

function getRegex (): RegExp | null {
  if(!config.value?.regex || config.value?.regex.length === 0) {
    if (config.value?.format === EDIT_FORMAT_INTEGER) {
      return EDIT_REGEX.integer as RegExp
    } else if (config.value?.format === EDIT_FORMAT_DOUBLE) {
      return EDIT_REGEX.double as RegExp
    }
  } else if (validState.value[VALIDATE_TARGET_REGEX]) {
    return RegExp(config.value.regex)
  }
  return null
}

function onConfigPaste () {
  let c
  let valid: boolean = true

  // Parse input
  try {
    c = JSON.parse(configPasteInput.value)
  } catch (error) {
    if (params.notifyCb) params.notifyCb('Invalid JSON', VARIANT_DANGER)
    console.error('Invalid JSON: ' + error)
    valid = false
  }

  // Reject paste if invalid data or incompatible format
  if (valid && (!('format' in c) || !('editable' in c))) {
    if (params.notifyCb) params.notifyCb('Invalid data', VARIANT_DANGER)
    console.error('Invalid data: ' + configPasteInput.value)
    valid = false
  } else if (
      (colType.value === EDIT_COL_TYPE_ONTOLOGY &&
        c.format !== EDIT_FORMAT_ONTOLOGY) ||
      (colType.value !== EDIT_COL_TYPE_ONTOLOGY &&
        c.format === EDIT_FORMAT_ONTOLOGY) ||
      (colType.value === EDIT_COL_TYPE_UNIT &&
        (!NUM_FORMATS.includes(c.format))) ||
      (colType.value !== EDIT_COL_TYPE_UNIT && c.format.unit)) {
    if (params.notifyCb) params.notifyCb('Invalid data', VARIANT_DANGER)
    console.error(
      `Invalid format for column type "${colType.value}": ${c.format}`)
    valid = false
  }

  // Copy data from pasted content if valid
  if (valid) {
    // Update config keys directly
    for (const i in CONFIG_COPY_KEYS) {
      const k: string = CONFIG_COPY_KEYS[i] as string
      if (k in c) {
        // @ts-expect-error Timeboxing, fix later
        config.value![k] = c[k]
      } else if (k === 'range') { // Range is a special case
        config.value!.range = ['', '']
      } else if (['options', 'unit'].includes(k)) {
        // @ts-expect-error Timeboxing, fix later
        config.value![k] = []
      }
    }
    // Update other config values via UI
    if ('options' in c) valueOptions.value = c.options.join('\n')
    if ('unit' in c) unitOptions.value = c.unit.join('\n')
    if ('range' in c) {
      rangeMin.value = c.range[0]
      rangeMax.value = c.range[1]
    }
  }
  if (params.notifyCb) params.notifyCb('Configuration pasted', VARIANT_SUCCESS)
  validate() // Validate after paste
  // Clear input
  nextTick().then(() => {
    configPasteInput.value = ''
  })
}

function onOntologyDefaultInput () {
  // Empty input = nothing to do
  if (!ontologyDefaultInput.value) return
  let p: Array<SheetTableOntologyRef> = []
  let valid: boolean = true
  // Parse input
  try {
    p = JSON.parse(ontologyDefaultInput.value)
  } catch (error) {
    if (params.notifyCb) params.notifyCb('Invalid JSON', VARIANT_DANGER)
    console.error('Invalid JSON: ' + error)
    valid = false
  }
  // Cleanup and validate
  if (valid) {
    if (!Array.isArray(p)) p = [p]
    for (let i = 0; i < p.length; i++) {
      const t = p[i] as SheetTableOntologyRef
      if (!('name' in t) ||
          t.name.length === 0 ||
          !('ontology_name' in t) ||
          !('accession' in t)) {
        valid = false
        if (params.notifyCb) params.notifyCb('Invalid format', VARIANT_DANGER)
        console.error('Invalid term: ' + JSON.stringify(t))
        valid = false
      }
    }
  }
  if (valid) {
    if (p.length > 1 && !config.value?.allow_list) {
      if (params.notifyCb) params.notifyCb('List not allowed', VARIANT_DANGER)
      valid = false
    }
  }
  // Update config if valid
  if (valid) {
    config.value!.default = p
    if (params.notifyCb) params.notifyCb('Default updated', VARIANT_SUCCESS)
  }
  // Clear input
  nextTick().then(() => {
    ontologyDefaultInput.value = ''
  })
}

function onOntologyDelete (ontology: string, idx: number) {
  config.value!.ontologies!.splice(idx, 1)
  ontologySelect.value.push(ontology)
  ontologySelect.value.sort()
}

function onOntologyMove (idx: number, up: boolean) {
  let otherIdx: number
  if (up) otherIdx = idx - 1
  else otherIdx = idx + 1
  const tmpVal = config.value!.ontologies![idx]
  config.value!.ontologies![idx] = config.value!.ontologies![otherIdx] as string
  config.value!.ontologies![otherIdx as number] = tmpVal as string
}

function onOntologyInsert () {
  if (config.value?.ontologies === undefined) config.value!.ontologies = []
  config.value!.ontologies.push(ontologyInsert.value)
  ontologySelect.value.splice(
    ontologySelect.value.indexOf(ontologyInsert.value), 1)
  ontologyInsert.value = ''
}

// Update related cells for all grids
function refreshGridCells () {
  for (const api of gridApis) {
    api.forEachNode(function (rowNode) {
      if ('newRow' in rowNode.data.col0 && fieldId in rowNode.data) {
        const newValue = rowNode.data[fieldId]
        if ([
            EDIT_COL_TYPE_NAME,
            EDIT_COL_TYPE_LINK,
            EDIT_COL_TYPE_PROTOCOL].includes(colType.value as string)) {
          newValue.editable = true
        } else if ('newInit' in newValue && !newValue.newInit) {
          newValue.editable = config.value!.editable
        }
        rowNode.setDataValue(fieldId, newValue)
      }
    })
    // TODO: Ensure this works with changed cells (see vueapp comment)
    api.refreshCells({ columns: [fieldId], force: true })
    // TODO: If not, call the following
    // api.redrawRows()
  }
}

function resetModalState (p: HeaderEditRendererParams) {
  params = p

  // Set up general refs
  itemType.value = p.itemType
  colType.value = p.colType || ''
  configPasteInput.value = ''
  modalTitle.value = p.editConfigField.name

  // Deep copy config into editable ref
  config.value = JSON.parse(
    JSON.stringify(p.editConfigField)) as StudyEditConfigNodeField

  // Set range
  if (p.editConfigField.range && p.editConfigField.range.length == 2) {
    rangeMin.value = p.editConfigField.range[0]
    rangeMax.value = p.editConfigField.range[1]
  }

  // Set default fill
  defaultFill.value = false
  toggleDefaultFill()

  // Set format options
  if (colType.value == EDIT_COL_TYPE_UNIT) {
    formatOptions.value = FORMAT_OPTIONS_UNIT
  } else formatOptions.value = FORMAT_OPTIONS_DEFAULT

  // Set unit
  unitOptions.value = ''
  if (p.colType == EDIT_COL_TYPE_UNIT) {
    unitEnable.value = true
    if (p.editConfigField.unit) {
      unitOptions.value = p.editConfigField.unit.join('\n')
    }
  } else unitEnable.value = false

  // Set options
  if (p.editConfigField.options) {
    valueOptions.value = p.editConfigField.options.join('\n')
  } else valueOptions.value = ''

  // Set ontology refs
  ontologyDefaultInput.value = ''
  ontologyInsert.value = ''
  ontologyPreset.value = false
  ontologySelect.value = []
  if (p.colType == EDIT_COL_TYPE_ONTOLOGY) {
    const oKeys = Object.keys(editStore.editContext!.sodar_ontologies)
    for (let i = 0; i < oKeys.length; i++) {
      if (!config.value.ontologies?.includes(oKeys[i] as string)) {
        ontologySelect.value.push(oKeys[i] as string)
      }
    }
    ontologySelect.value.sort()
  }

  // Reset valid state
  validState.value = {
    [VALIDATE_TARGET_DEFAULT]: true,
    [VALIDATE_TARGET_RANGE]: true,
    [VALIDATE_TARGET_REGEX]: true,
    [VALIDATE_TARGET_SELECT]: true,
  }

  // Set up internal vars
  gridApis = tableStore.getGridApis()
  fieldId = p.column?.getColId() as string
  ogColType = p.colType || ''
}

// Set initial config based on params and column
// NOTE: To be called after resetModalState()
function setInitialConfig () {
  // TODO: Do we need to support newConfig? (see old implementation)
  const headerName: string = params.editConfigField.name.toLowerCase()

  // Force format for preset ontologies (formerly specialOntologyCol)
  if ([OBO_HEADER_HP, OBO_HEADER_OMIM, OBO_HEADER_ORDO].includes(headerName)) {
    ontologyPreset.value = true
    if (headerName === OBO_HEADER_HP) {
      config.value!.ontologies = [OBO_ID_HP]
      config.value!.allow_list = true
    } else if (headerName === OBO_HEADER_OMIM) {
      config.value!.ontologies = [OBO_ID_OMIM]
      config.value!.allow_list = false
    } else if (headerName === OBO_HEADER_ORDO) {
      config.value!.ontologies = [OBO_ID_ORDO]
      config.value!.allow_list = false
    }
  } else if (colType.value === EDIT_COL_TYPE_ONTOLOGY &&
      config.value?.format !== EDIT_FORMAT_ONTOLOGY) {
    // TODO: TBD: Is this still needed? Can we even reach this anymore?
    config.value!.format = EDIT_FORMAT_ONTOLOGY
    config.value!.ontologies = []
  } else if (colType.value == EDIT_COL_TYPE_EXT_LINKS) {
    config.value!.format = EDIT_FORMAT_EXT
  } else if (![EDIT_COL_TYPE_NAME, EDIT_COL_TYPE_LINK].includes(
      colType.value as string)) {
    // Skip forcing for name columns
    // Set up correct numeric format
    if (NUM_COL_TYPES.includes(colType.value as string)) {
      let unitsAdded: boolean = false
      config.value!.format = EDIT_FORMAT_INTEGER // Double-checked later
      if (colType.value === EDIT_COL_TYPE_UNIT) {
        config.value!.unit = []
      }
      // Iterate rows and force into double
      for (const api of gridApis) {
        api.forEachNode(function (rowNode) {
          const cell = rowNode.data[fieldId]
          if (config.value?.format != EDIT_FORMAT_DOUBLE &&
              ['.', ','].some(e => cell.value.includes(e))) {
            config.value!.format = EDIT_FORMAT_DOUBLE
          }
          // TODO: TBD: Enable guessing range? (see old implementation)
          // Add missing units to config
          if (colType.value == EDIT_COL_TYPE_UNIT &&
              cell.unit &&
              !config.value?.unit?.includes(cell.unit)) {
            config.value!.unit!.push(cell.unit)
            if (!unitsAdded) unitsAdded = true
          }
        })
      }
      // Enable unit and unit options if units were added
      if (unitsAdded) {
        unitEnable.value = true
        unitOptions.value = config.value!.unit!.join('\n')
      }
    } else if (colType.value === EDIT_COL_TYPE_DATE) {
      // Force date format
      config.value!.format = EDIT_FORMAT_DATE
    }
  }
}

function toggleDefaultFill () {
  if (config.value?.default) {
    defaultFillEnable.value = true
    validate(VALIDATE_TARGET_DEFAULT)
  } else {
    defaultFill.value = false  // No default fill if we don't have default
    defaultFillEnable.value = false
  }
}

// Update column definitions for all grids
function updateColDefs () {
  for (const api of gridApis) {
    // Get column definition
    const col = api.getColumn(fieldId)
    if (!col) continue // Column not in grid, nothing to do for this one
    const colDef: ColDef = col.getColDef()

    // Update config and column type for column definition
    // TODO: Simplify?
    colDef.cellEditorParams.editConfigField = config.value
    colDef.cellRendererParams.colType = colType.value
    colDef.cellRendererParams.fieldEditable = config.value!.editable
    colDef.editable = config.value!.editable
    colDef.headerComponentParams.colType = colType.value
    // Update config field in all grids
    cleanupConfig(colDef.headerComponentParams.editConfigField)
    Object.assign(colDef.headerComponentParams.editConfigField, config.value)

    // Update alignment
    let colAlign = 'left'
    if (NUM_COL_TYPES.includes(colType.value as string)) colAlign = 'right'
    colDef.cellEditorParams.colAlign = colAlign
  }
}

async function updateConfig () {
  const updateBody: EditConfigRequestBody = {
    fields: [{
      action: EDIT_CONFIG_ACTION_UPDATE,
      assay: params.assayUuid,
      config: config.value as StudyEditConfigNodeField,
      field_idx: params.configFieldIdx,
      node_idx: params.configNodeIdx,
      study: appStore.currentStudyUuid,
    }]
  }
  const response = await fetch(updateUrl, {
    method: 'POST',
    body: JSON.stringify(updateBody),
    credentials: 'same-origin',
    headers: {
      Accept: 'application/json',
      'Content-type': 'application/json',
      'X-CSRFToken': appStore.sodarContext!.csrf_token
    }
  })
  const resBody: GenericResponseBody = await response.json()

  if (resBody.detail === 'ok') {
    // Update grids to match current updates
    updateGrids()
    if (params.notifyCb) {
      const msg: string = `Updated column "${modalTitle.value}"`
      params.notifyCb(msg, VARIANT_SUCCESS)
    }
  } else {
    const msg: string = `Failed to update column "${modalTitle.value}":
                         ${resBody.detail}`
    if (params.notifyCb) params.notifyCb(msg, VARIANT_DANGER)
    console.error(msg)
  }
}

function updateGrids () { // Formerly handleUpdate()
  const c = config.value as StudyEditConfigNodeField
  let refreshCalled: boolean = false

  // Determine current colType
  // NOTE: If unit exists in headers, colType will not be changed
  if (NUM_FORMATS.includes(c.format as string) &&
      ogColType !== EDIT_COL_TYPE_UNIT) {
    colType.value = EDIT_COL_TYPE_NUMERIC
  } else if (!colType.value) colType.value = null // TODO: Is this still needed?

  // Update colDefs in all grids
  // NOTE: updateColType() should no longer be needed (see #2446)
  updateColDefs()

  // Cell modifications
  const fillValues: boolean = defaultFill.value &&
    config.value?.default !== undefined
  const removeUnit: boolean = colType.value !== EDIT_COL_TYPE_UNIT &&
    ogColType === EDIT_COL_TYPE_UNIT

  if (fillValues || removeUnit) {
    let api: GridApi
    if (!params.assayUuid) api = tableStore.gridApi.study as GridApi
    else api = tableStore.gridApi.assays[params.assayUuid] as GridApi
    const cellEditData: Array<CellEditData> = []

    api.forEachNode(function (rowNode) {
      const gridCell = rowNode.data[fieldId]
      // Create update data for cells with empty value or removable unit
      if (!gridCell.value || (removeUnit && gridCell.unit)) {
        let newValue: SheetTableCellDataValue
        if (fillValues && !gridCell.value) {
          newValue = config.value!.default as string
        } else newValue = gridCell.value

        let newUnit: string | undefined
        if (removeUnit) newUnit = config.value!.unit_default

        cellEditData.push({
          fieldId: fieldId,
          headerName: params.editConfigField.name,
          headerType: params.headerType,
          itemType: params.itemType,
          objCls: params.objCls,
          ogUnit: gridCell.unit,
          ogValue: gridCell.value,
          unit: newUnit,
          uuid: gridCell.uuid,
          uuidRef: gridCell.uuidRef,
          value: newValue,
        })
      }
    })

    if (cellEditData.length > 0) {
      updateCells(cellEditData, true, params.notifyCb)
      refreshCalled = true
    }
  }

  // Update related cells if we haven't done it yet
  if (!refreshCalled) refreshGridCells()
  editStore.editDataUpdated = true
}

function validate (target?: string) {
  // Regex
  if ((!target || target == VALIDATE_TARGET_REGEX) && config.value?.regex) {
    try {
      RegExp(config.value.regex)
      validState.value[VALIDATE_TARGET_REGEX] = true
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
    } catch (error) {
      validState.value[VALIDATE_TARGET_REGEX] = false
    }
  }
  // Store regex for further validation
  const regex: RegExp | null = getRegex()
  // Select
  if ((!target || target === VALIDATE_TARGET_SELECT) &&
      config.value?.format === EDIT_FORMAT_SELECT) {
    const valSplit: Array<string> = valueOptions.value.split('\n')
    validState.value[VALIDATE_TARGET_SELECT] = (
      valSplit.length >= 2 && !valSplit.includes(''))
  }
  // Range
  if ((!target || target === VALIDATE_TARGET_RANGE) && config.value?.range) {
    let rangeValid: boolean = true
    const rMin = rangeMin.value
    const rMax = rangeMax.value
    // Validate min/max fields against regex
    if (regex && (!regex.test(rMin) || !regex.test(rMax))) {
      rangeValid = false
    }
    // Validate actual range
    if (rangeValid && (
        (rMin.length > 0 && rMax.length === 0) ||
        (rMin.length === 0 && rMax.length > 0) ||
        parseFloat(rMin) >= parseFloat(rMax))) {
      rangeValid = false
    }
    validState.value[VALIDATE_TARGET_RANGE] = rangeValid
  }
  if (!target ||
      [VALIDATE_TARGET_DEFAULT, VALIDATE_TARGET_RANGE].includes(target)) {
    let defaultValid: boolean
    let fillEnable: boolean
    if (config.value?.default && config.value.default.length > 0) {
      const df: number = parseFloat(config.value?.default as string || '0')
      if ((!regex ||
          (validState.value[VALIDATE_TARGET_REGEX] &&
            regex.test(config.value?.default as string))) && (
              NUM_FORMATS.includes(config.value?.format as string) ||
          (!config.value?.range || !config.value?.range![0]) || (
              df >= parseFloat(config.value?.range[0]) &&
              df <= parseFloat(config.value?.range[1])))) {
        defaultValid = true
        fillEnable = true
      } else {
        defaultValid = false
        fillEnable = false
      }
    } else {
      defaultValid = true
      fillEnable = config.value?.default?.length !== 0
    }
    validState.value[VALIDATE_TARGET_DEFAULT] = defaultValid
    defaultFillEnable.value = fillEnable
  }
}

// API and Life Cycle ----------------------------------------------------------

function show (p: HeaderEditRendererParams) {
  // console.log('DEBUG: show() called')
  // console.dir(p)
  resetModalState(p)
  setInitialConfig()
  // Show modal once setup is complete
  showModal.value = true
}
defineExpose({ show })

function hide (update: boolean) {
  if (update && config.value) {
    config.value = cleanupConfig(config.value)
    try {
      updateConfig()
    } catch (error) {
      const msg: string = `Error updating field config: ${error}`
      console.error(msg)
      if (params.notifyCb) params.notifyCb(msg, VARIANT_DANGER)
    }
  }
  modalRef.value?.hide()
}
</script>

<template>
  <BModal
      id="sodar-ss-modal-col-config-modal"
      ref="columnConfigModal"
      v-model="showModal"
      size="md"
      centered no-footer no-animation teleport-disabled>
    <template #header>
      <ModalHeader
          :modal-ref="modalRef"
          :title="modalTitle"
          :hide-close-button="true">
        <template v-slot:extend>
          <BInputGroup class="sodar-header-input-group justify-content-end">
            <BButton
                variant="secondary"
                id="sodar-ss-col-config-btn-clip-copy"
                title="Copy configuration to clipboard"
                @click="copyConfig()"
                :disabled="!enableCopy()">
              <i class="iconify" data-icon="mdi:clipboard-text-multiple"></i>
            </BButton>
            <input
                v-model="configPasteInput"
                id="sodar-ss-col-config-input-clip-paste"
                placeholder="Paste"
                title="Paste and replace configuration"
                @update:model-value="onConfigPaste()"
                :disabled="!enableCopy()" />
          </BInputGroup>
        </template>
      </ModalHeader>
    </template>
    <div id="sodar-ss-col-config-content">
      <table
          v-if="config"
          class="table table-borderless w-100"
          id="sodar-ss-col-config-table">
        <tbody>
          <!-- Editable (common for all types) -->
          <tr>
            <td>Editable</td>
            <td>
              <BFormCheckbox
                  id="sodar-ss-col-config-check-editable"
                  :checked="config.editable"
                  @click="config.editable = !config.editable"
                  plain />
            </td>
          </tr>
        </tbody>
        <!-- Name table body -->
        <tbody
            v-if="['NAME', 'LINK_FILE'].includes(colType as string)"
            id="sodar-ss-col-config-tbody-name">
          <tr v-if="colType === EDIT_COL_TYPE_NAME &&
                    itemType !== EDIT_ITEM_TYPE_SOURCE"
              id="sodar-ss-col-config-tr-detail-suffix">
            <td>
              Default Suffix
              <InfoIcon
                  body="Prefill with the name of previous node plus a suffix if
                       set" />
            </td>
            <td>
              <BFormInput
                  v-model="config.default as string"
                  :class="classDefault"
                  id="sodar-ss-col-config-input-default">
              </BFormInput>
            </td>
          </tr>
          <tr>
            <td colspan="2"
                class="sodar-ss-td-info text-danger"
                id="sodar-ss-col-config-msg-name">
              <strong>Warning:</strong> If you are storing project sample data
              in iRODS, renaming certain materials or processes may cause
              related iRODS links to stop working! When in doubt, please
              contact a project owner/delegate or your SODAR instance support.
            </td>
          </tr>
        </tbody>
        <!-- Protocol table body -->
        <tbody
            v-else-if="colType === EDIT_COL_TYPE_PROTOCOL"
            id="sodar-ss-col-config-tbody-protocol">
          <tr>
            <td>Default Value</td>
            <td>
              <BFormSelect
                  v-model="config.default"
                  class="custom-select"
                  id="sodar-ss-col-config-select-default">
                <BFormSelectOption
                    class="sodar-ss-col-config-option-default"
                    value="">
                  -
                </BFormSelectOption>
                <BFormSelectOption
                    v-for="(option, idx) in editStore.editContext?.protocols"
                    :key="idx"
                    class="sodar-ss-col-config-option-default"
                    :value="option.uuid">
                  {{ option.name }}
                </BFormSelectOption>
              </BFormSelect>
            </td>
          </tr>
          <!-- Add protocol editing here once implemented -->
        </tbody>
        <!-- Contact table body -->
        <tbody
            v-else-if="colType === EDIT_COL_TYPE_CONTACT"
            id="sodar-ss-col-config-tbody-contact">
          <ColumnConfigModalSeparator />
          <tr>
            <td colspan="2" class="sodar-ss-td-info">
              Enter the contact info as <code>Name &lt;email@domain.com&gt;</code>
              for linking. Popup editor is forthcoming.
            </td>
          </tr>
        </tbody>
        <!-- Date table body -->
        <tbody
            v-else-if="colType === EDIT_COL_TYPE_DATE"
            id="sodar-ss-col-config-tbody-date">
          <ColumnConfigModalSeparator />
          <tr>
            <td colspan="2" class="sodar-ss-td-info">
              Enter the date as <code>YYYY-MM-DD</code>.
            </td>
          </tr>
        </tbody>
        <!-- Ontology table body -->
        <tbody
            v-else-if="colType === EDIT_COL_TYPE_ONTOLOGY"
            id="sodar-ss-col-config-tbody-ontology">
          <tr>
            <td>Allow List</td>
            <td id="sodar-ss-col-config-td-allow-list">
              <BFormCheckbox
                  id="sodar-ss-col-config-check-allow-list"
                  title="Allow entering a list of ontology terms if enabled"
                  :checked="config.allow_list"
                  :disabled="ontologyPreset"
                  @click="config.allow_list = !config.allow_list"
                  plain />
            </td>
          </tr>
          <tr>
            <td>Default Value</td>
            <td class="text-nowrap">
              <BInputGroup
                  class="sodar-header-input-group">
                <BFormInput
                    v-model="ontologyDefaultInput"
                    id="sodar-ss-col-config-input-ontology-default"
                    class="sodar-ss-col-config-input-paste"
                    placeholder="Paste"
                    title="Paste ontology terms JSON here"
                    @update:model-value="onOntologyDefaultInput()" />
                <BButton
                    variant="danger"
                    class="sodar-ss-row-btn px-1"
                    id="sodar-ss-col-config-btn-ontology-default-delete"
                    title="Clear default ontology terms"
                    @click="config.default = ''"
                    :disabled="!config.default">
                  <i class="iconify" data-icon="mdi:close-thick"></i>
                </BButton>
              </BInputGroup>
            </td>
          </tr>
        </tbody>
        <!-- External links table body -->
        <tbody
            v-else-if="colType === EDIT_COL_TYPE_EXT_LINKS"
            id="sodar-ss-col-config-tbody-ext">
          <ColumnConfigModalSeparator />
          <tr>
            <td colspan="2" class="sodar-ss-td-info">
              Enter IDs as <code>id-type:id</code> separated by <code>;</code>
              (semicolon).
            </td>
          </tr>
        </tbody>
        <!-- Basic field table body -->
        <tbody
            v-else
            id="sodar-ss-col-config-tbody-basic">
          <!-- Format controls (hide for extract label) -->
          <tr v-if="params.headerType !== EDIT_HEADER_TYPE_EXTRACT_LABEL"
              id="sodar-ss-col-config-tr-format">
            <td>Format</td>
            <td>
              <BFormSelect
                  v-model="config.format"
                  class="custom-select"
                  id="sodar-ss-col-config-select-format"
                  @change="validate()">
                <BFormSelectOption
                    v-for="(option, idx) in formatOptions"
                    :key="idx"
                    class="sodar-ss-col-config-option-format"
                    :value="option"
                    :selected="option === config.format">
                  {{ option }}
                </BFormSelectOption>
              </BFormSelect>
            </td>
          </tr>
          <ColumnConfigModalSeparator />
          <!-- Select controls -->
          <tr v-if="config.format === EDIT_FORMAT_SELECT"
              id="sodar-ss-col-config-tr-select">
            <td class="align-top pt-3">
              Options
              <InfoIcon body="Separate options by newline" />
            </td>
            <td>
              <BFormTextarea
                  v-model="valueOptions"
                  :class="getFormValidClass(VALIDATE_TARGET_SELECT)"
                  id="sodar-ss-col-config-input-options"
                  rows="4"
                  @input="validate(VALIDATE_TARGET_SELECT)" />
            </td>
          </tr>
          <!-- Range controls -->
          <tr v-if="NUM_FORMATS.includes(config.format as string)"
              id="sodar-ss-col-config-tr-range">
            <td>Range</td>
            <td>
              <div class="row">
                <div class="col p-0">
                  <BFormInput
                      v-model="rangeMin"
                      :class="'text-right ' +
                              getFormValidClass(VALIDATE_TARGET_RANGE)"
                      id="sodar-ss-col-config-input-range-min"
                      placeholder="Min"
                      @input="validate(VALIDATE_TARGET_RANGE)" />
                </div>
                <div class="col col-1 text-center pt-1 px-1">-</div>
                <div class="col p-0">
                  <BFormInput
                      v-model="rangeMax"
                      :class="'text-right ' +
                              getFormValidClass(VALIDATE_TARGET_RANGE)"
                      id="sodar-ss-col-config-input-range-max"
                      placeholder="Max"
                      @input="validate(VALIDATE_TARGET_RANGE)" />
                </div>
              </div>
            </td>
          </tr>
          <!-- Regex controls -->
          <tr v-if="config.format !== EDIT_FORMAT_SELECT"
              id="sodar-ss-col-config-tr-regex">
            <td>Regex</td>
            <td>
              <BFormInput
                  v-model="config.regex"
                  :class="getFormValidClass(VALIDATE_TARGET_REGEX)"
                  id="sodar-ss-col-config-input-regex"
                  @input="validate()" />
            </td>
          </tr>
          <!-- Default value controls -->
          <tr id="sodar-ss-col-config-tr-default-val">
            <td>Default Value</td>
            <td>
              <!-- String/integer/double default -->
              <!-- NOTE: validate() called in toggleDefaultFill() -->
              <BFormInput
                  v-if="config.format !== EDIT_FORMAT_SELECT"
                  v-model="config.default as string"
                  :class="getFormValidClass(VALIDATE_TARGET_DEFAULT)"
                  id="sodar-ss-col-config-input-default"
                  @update:model-value="toggleDefaultFill()" />
              <!-- Selection default -->
              <BFormSelect
                  v-else
                  v-model="config.default"
                  class="custom-select"
                  id="sodar-ss-col-config-input-default"
                  @update:model-value="toggleDefaultFill()"
                  :disabled="!valueOptions">
                <BFormSelectOption :value="null">-</BFormSelectOption>
                <BFormSelectOption
                    v-for="(option, idx) in valueOptions.split('\n')"
                    :key="idx"
                    :value="option">
                  {{ option }}
                </BFormSelectOption>
              </BFormSelect>
            </td>
          </tr>
          <!-- Default fill controls -->
          <tr id="sodar-ss-col-config-tr-default-fill">
            <td>Default Fill</td>
            <td>
              <BFormCheckbox
                  v-model="defaultFill"
                  id="sodar-ss-col-config-check-fill"
                  title="Fill empty column values with default value on update"
                  :disabled="!defaultFillEnable"
                  plain />
            </td>
          </tr>
          <!-- TODO: Add unit enable/disable controls (see #889) -->
          <!-- Unit controls -->
          <tr v-if="unitEnable && NUM_FORMATS.includes(config.format as string)"
              id="sodar-ss-col-config-tr-unit">
            <td class="align-top pt-3">
              Unit
              <InfoIcon body="Separate options by newline" />
            </td>
            <td>
              <BFormTextarea
                  v-model="unitOptions"
                  id="sodar-ss-col-config-input-unit"
                  rows="4" />
            </td>
          </tr>
          <!-- Default unit controls -->
          <tr v-if="unitEnable && NUM_FORMATS.includes(config.format as string)"
              id="sodar-ss-col-config-tr-unit-default">
            <td>Default Unit</td>
            <td>
              <BFormSelect
                  v-model="config.unit_default"
                  class="custom-select"
                  id="sodar-ss-col-config-input-unit-default"
                  :disabled="!unitOptions">
                <BFormSelectOption
                  value=""
                  class="sodar-ss-col-config-option-unit-default"
                  :selected="!config.unit_default">
                  -
                </BFormSelectOption>
                <BFormSelectOption
                    v-for="(option, idx) in unitOptions.split('\n')"
                    :key="idx"
                    :value="option"
                    class="sodar-ss-col-config-option-unit-default">
                  {{ option }}
                </BFormSelectOption>
              </BFormSelect>
            </td>
          </tr>
        </tbody>
      </table>
      <!-- Ontology allowed ontologies table -->
      <table
          v-if="colType === EDIT_COL_TYPE_ONTOLOGY"
          class="table sodar-card-table mt-3"
          id="sodar-ss-col-config-table-ontology-allow">
        <thead>
          <tr>
            <th colspan="2">
              Allowed Ontologies
              <InfoIcon
                  body="Allowed ontologies for this column. If not set,
                        allow terms from any ontology." />
            </th>
          </tr>
        </thead>
        <tbody>
          <!-- Existing allowed ontologies -->
          <tr v-for="(ontology, oIdx) in config?.ontologies"
              :key="oIdx"
              class="sodar-ss-col-config-tr-ontology-allowed">
            <td class="sodar-ss-col-config-td-ontology-name">
              {{ ontology }}
            </td>
            <td class="text-right">
              <BButton
                  variant="primary"
                  class="sodar-list-btn sodar-ss-row-btn
                         sodar-ss-col-config-btn-ontology-move
                         sodar-ss-col-config-btn-ontology-move-up mr-1"
                  title="Move ontology backwards in list"
                  @click="onOntologyMove(oIdx, true)"
                  :disabled="!enableOntologyMove(oIdx, true)">
                <i class="iconify" data-icon="mdi:arrow-up-bold"></i>
              </BButton>
              <BButton
                  variant="primary"
                  class="sodar-list-btn sodar-ss-row-btn
                         sodar-ss-col-config-btn-ontology-move
                         sodar-ss-col-config-btn-ontology-move-down mr-1"
                  title="Move ontology forward in list"
                  @click="onOntologyMove(oIdx, false)"
                  :disabled="!enableOntologyMove(oIdx, false)">
                <i class="iconify" data-icon="mdi:arrow-down-bold"></i>
              </BButton>
              <BButton
                  variant="danger"
                  class="sodar-list-btn sodar-ss-row-btn
                         sodar-ss-col-config-btn-ontology-delete"
                  title="Delete ontology"
                  @click="onOntologyDelete(ontology, oIdx)"
                  :disabled="ontologyPreset">
                <i class="iconify" data-icon="mdi:close-thick"></i>
              </BButton>
            </td>
          </tr>
          <!-- Insert allowed ontology -->
          <tr v-if="!ontologyPreset"
              id="sodar-ss-col-config-tr-ontology-insert">
            <td>
              <BFormSelect
                  v-model="ontologyInsert"
                  class="custom-select"
                  id="sodar-ss-col-config-select-ontology-insert"
                  :disabled="!ontologySelect">
                <BFormSelectOption
                    v-if="ontologySelect.length > 0"
                    class="sodar-ss-col-config-option-ontology-insert"
                    value="">
                  Select ontology
                </BFormSelectOption>
                <BFormSelectOption
                    v-for="(ontology, idx) in ontologySelect"
                    :key="idx"
                    :value="ontology"
                    class="sodar-ss-col-config-option-ontology-insert">
                  {{ ontology }}
                </BFormSelectOption>
              </BFormSelect>
            </td>
            <td class="text-right pt-3">
              <BButton
                  variant="primary"
                  class="sodar-list-btn sodar-ss-row-btn"
                  id="sodar-ss-col-config-btn-ontology-insert"
                  title="Insert ontology"
                  @click="onOntologyInsert"
                  :disabled="!ontologyInsert">
                <i class="iconify" data-icon="mdi:plus-thick"></i>
              </BButton>
            </td>
          </tr>
          <!-- All ontologies allowed alert -->
          <tr v-if="!ontologyPreset &&
                    (!config?.ontologies || config?.ontologies.length === 0)">
            <td colspan="2">
              <div class="alert alert-info mb-0"
                   id="sodar-ss-col-config-alert-all">
                Allowing all available ontologies for this column.
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      <!-- Ontology default value table -->
      <table
          v-if="colType === EDIT_COL_TYPE_ONTOLOGY"
          class="table sodar-card-table mt-3"
          id="sodar-ss-col-config-table-ontology-default">
        <thead>
          <tr>
            <th colspan="2">Default Value</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="!config?.default"
              id="sodar-ss-col-config-tr-ontology-default-empty">
            <td class="text-muted">N/A</td>
          </tr>
          <tr v-for="(term, tIdx) in config?.default"
              :key="tIdx"
              class="sodar-ss-col-config-tr-ontology-default">
            <td>
              <a :href="(term as SheetTableOntologyRef).accession"
                 target="_blank">
                {{ (term as SheetTableOntologyRef).name }}
              </a>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <div id="sodar-ss-col-config-controls">
      <BButtonGroup
          class="pull-right"
          id="sodar-ss-col-config-btn-group">
        <BButton
            variant="secondary"
            id="sodar-ss-col-config-btn-cancel"
            @click="hide(false)">
          <i class="iconify" data-icon="mdi:close-thick"></i> Cancel
        </BButton>
        <BButton
            variant="primary"
            id="sodar-ss-col-config-btn-update"
            ref="updateBtn"
            :disabled="!enableUpdate()"
            @click="hide(true)">
          <i class="iconify" data-icon="mdi:check-bold"></i> Update
        </BButton>
      </BButtonGroup>
    </div>
  </BModal>
</template>

<style scoped>
div#sodar-ss-col-config-content {
  min-height: 620px !important;
}
#sodar-ss-col-config-btn-clip-copy {
  padding-left: 8px;
  padding-right: 8px;
  border-top-right-radius: 0 !important;
  border-bottom-right-radius: 0 !important;
}
#sodar-ss-col-config-input-clip-paste {
  max-height: 30px;
  max-width: 60px;
  border: 1px solid #CED4DA;
  border-top-right-radius: 4px;
  border-bottom-right-radius: 4px;
  padding-left: 8px;
  padding-right: 5px;
}
.sodar-ss-col-config-input-paste {
  width: 70px;
}
#sodar-ss-col-config-input-ontology-default {
  max-width: 80px !important;
}
#sodar-ss-col-config-btn-ontology-default-delete {
  border-top-left-radius: 0 !important;
  border-bottom-left-radius: 0 !important;
}
table#sodar-ss-col-config-table tbody td:first-child {
  width: 100px;
  max-width: 250px;
  vertical-align: middle;
  white-space: nowrap;
}
#sodar-ss-col-config-btn-group {
  padding-right: 12px;
}
td.sodar-ss-td-info {
  white-space: normal !important;
}
table#sodar-ss-col-post-ontology tbody td:nth-child(2) {
  white-space: nowrap !important;
  width: 120px;
}
table#sodar-ss-col-post-ontology tbody tr td {
  vertical-align: middle;
  height: 63px;
}
</style>
