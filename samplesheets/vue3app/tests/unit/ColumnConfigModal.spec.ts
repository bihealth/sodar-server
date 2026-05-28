import { nextTick, type TemplateRef } from 'vue'
import { beforeEach, describe, expect, test, vi } from 'vitest'
import { config, flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { createBootstrap } from 'bootstrap-vue-next/plugins/createBootstrap'
import { type Column, type GridApi } from 'ag-grid-community'

import ColumnConfigModal from '@/components/modals/ColumnConfigModal.vue'
import { useAppStore } from '@/stores/appStore.ts'
import { useEditStore } from '@/stores/editStore.ts'
import { useTableStore } from '@/stores/tableStore.ts'
import {
  type EditConfigRequestBody,
  type GenericResponseBody,
  type HeaderEditRendererParams,
  type SheetTableCellDataValue,
  type SheetTableOntologyRef,
  type SodarContext,
  type StudyEditContext
} from '@/types.ts'
import {
  DB_OBJ_CLASS_MATERIAL,
  DB_OBJ_CLASS_PROCESS,
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
  EDIT_ITEM_TYPE_DATA,
  EDIT_ITEM_TYPE_MATERIAL,
  EDIT_ITEM_TYPE_SAMPLE,
  EDIT_ITEM_TYPE_SOURCE,
  EDIT_FORMAT_DATE,
  EDIT_FORMAT_EXT,
  EDIT_FORMAT_DOUBLE,
  EDIT_FORMAT_INTEGER,
  EDIT_FORMAT_ONTOLOGY,
  EDIT_FORMAT_PROTOCOL,
  EDIT_FORMAT_SELECT,
  EDIT_FORMAT_STRING,
  EDIT_HEADER_TYPE_CHAR,
  EDIT_HEADER_TYPE_NAME,
  EDIT_HEADER_TYPE_PERFORM_DATE,
  EDIT_HEADER_TYPE_PERFORMER,
  EDIT_HEADER_TYPE_PROTOCOL,
  EDIT_REGEX,
  OBO_HEADER_HP,
  OBO_HEADER_OMIM,
  OBO_HEADER_ORDO,
  OBO_ID_HP,
  OBO_ID_OMIM,
  OBO_ID_ORDO,
} from '@/constants.ts'

import { copy } from '../testUtils.ts'
import { sodarContext } from '../data/sodarContext.ts'
import studyTablesEdit from '../data/studyTablesEdit.json'
import {
  ASSAY_UUID,
  OBO_ID_NCBITAXON,
  OBO_ID_UBERON,
  PROJECT_UUID,
  STUDY_UUID,
  TMP_UUID,
  TMP_UUID2
} from '../testConstants.ts'

// Name column is used for default params
const defaultParams = {
  assayMode: false,
  assayUuid: null,
  canEditConfig: true,
  colType: EDIT_COL_TYPE_NAME,
  configFieldIdx: 0,
  configNodeIdx: 0,
  editConfigField: {
    default: '',
    editable: true,
    format: EDIT_FORMAT_STRING,
    name: 'Name',
    regex: '',
    type: EDIT_HEADER_TYPE_NAME
  },
  editable: true,
  headerType: EDIT_HEADER_TYPE_NAME,
  itemType: EDIT_ITEM_TYPE_SOURCE,
  modalRef: {} as unknown as TemplateRef,
  objCls: DB_OBJ_CLASS_MATERIAL,
}
let params: HeaderEditRendererParams

const defaultReqBody: EditConfigRequestBody = {
  fields: [{
    action: EDIT_CONFIG_ACTION_UPDATE,
    assay: null,
    config: {
      default: '',
      editable: true,
      format: EDIT_FORMAT_STRING,
      name: 'Name',
      regex: '',
      type: 'name',
    },
    'field_idx': 0,
    'node_idx': 0,
    'study': STUDY_UUID
  }]
}
let reqBody: EditConfigRequestBody

const defaultResBody: GenericResponseBody = { detail: 'ok' }
let resBody: GenericResponseBody
const url = '/samplesheets/ajax/config/update/' + PROJECT_UUID

const ontologyCount = Object.keys(
  studyTablesEdit.edit_context.sodar_ontologies).length
const ontologyTerm: SheetTableOntologyRef = {
  name: 'Homo sapiens',
  ontology_name: 'NCBITAXON',
  accession: 'https://purl.obolibrary.org/obo/NCBITaxon_9606'
}
const ontologyTerm2: SheetTableOntologyRef = {
  name: 'Homo sapiens neanderthalensis',
  ontology_name: 'NCBITAXON',
  accession: 'https://purl.obolibrary.org/obo/NCBITaxon_63221',
}

const protocolName: string = studyTablesEdit.edit_context.protocols[0]!.name
const protocolUuid: string = studyTablesEdit.edit_context.protocols[0]!.uuid

// Selectors
const bodyBasicSel = '#sodar-ss-col-config-tbody-basic'
const bodyContactSel = '#sodar-ss-col-config-tbody-contact'
const bodyDateSel = '#sodar-ss-col-config-tbody-date'
const bodyExtSel = '#sodar-ss-col-config-tbody-ext'
const bodyNameSel = '#sodar-ss-col-config-tbody-name'
const bodyOntologySel = '#sodar-ss-col-config-tbody-ontology'
const bodyProtocolSel = '#sodar-ss-col-config-tbody-protocol'

const ontAllowTableSel = '#sodar-ss-col-config-table-ontology-allow'
const ontDefaultTableSel = '#sodar-ss-col-config-table-ontology-default'
const allowListCheckSel = '#sodar-ss-col-config-check-allow-list'
const defaultInputSel = '#sodar-ss-col-config-input-default'
const defaultSelectSel = '#sodar-ss-col-config-select-default'
const defaultOptionSel = '.sodar-ss-col-config-option-default'
const editableCheckSel = '#sodar-ss-col-config-check-editable'

const msgNameSel = '#sodar-ss-col-config-msg-name'

const trDefaultFillSel = '#sodar-ss-col-config-tr-default-fill'
const trDefaultValSel = '#sodar-ss-col-config-tr-default-val'
const trRangeSel = '#sodar-ss-col-config-tr-range'
const trRegexSel = '#sodar-ss-col-config-tr-regex'
const trSelectSel = '#sodar-ss-col-config-tr-select'
const trUnitSel = '#sodar-ss-col-config-tr-unit'
const trUnitDefaultSel = '#sodar-ss-col-config-tr-unit-default'
const trOntAllowSel = '.sodar-ss-col-config-tr-ontology-allowed'
const trOntInsertSel = '#sodar-ss-col-config-tr-ontology-insert'
const trOntDefaultEmptySel = '#sodar-ss-col-config-tr-ontology-default-empty'
const trOntDefaultTermSel = '.sodar-ss-col-config-tr-ontology-default'

const formatSelectSel = '#sodar-ss-col-config-select-format'
const formatOptionSel = '.sodar-ss-col-config-option-format'
const rangeMaxInputSel = '#sodar-ss-col-config-input-range-max'
const rangeMinInputSel = '#sodar-ss-col-config-input-range-min'
const regexInputSel = '#sodar-ss-col-config-input-regex'
const unitInputSel = '#sodar-ss-col-config-input-unit'
const unitDefaultInputSel = '#sodar-ss-col-config-input-unit-default'
const unitDefaultOptSel = '.sodar-ss-col-config-option-unit-default'
const valueOptInputSel = '#sodar-ss-col-config-input-options'
const valueFillCheckSel = '#sodar-ss-col-config-check-fill'
const ontDefaultDeleteSel = '#sodar-ss-col-config-btn-ontology-default-delete'
const ontDefaultInputSel = '#sodar-ss-col-config-input-ontology-default'
const ontDeleteBtnSel = '.sodar-ss-col-config-btn-ontology-delete'
const ontInsertBtnSel = '#sodar-ss-col-config-btn-ontology-insert'
const ontInsertSelectSel = '#sodar-ss-col-config-select-ontology-insert'
const ontInsertOptionSel = '.sodar-ss-col-config-option-ontology-insert'
const ontMoveBtnSel = '.sodar-ss-col-config-btn-ontology-move'
const ontMoveDownBtnSel = '.sodar-ss-col-config-btn-ontology-move-down'
const ontMoveUpBtnSel = '.sodar-ss-col-config-btn-ontology-move-up'

const alertOntAllSel = '#sodar-ss-col-config-alert-all'
const copyBtnSel = '#sodar-ss-col-config-btn-clip-copy'
const pasteInputSel = '#sodar-ss-col-config-input-clip-paste'
const updateBtnSel = '#sodar-ss-col-config-btn-update'
const cancelBtnSel = '#sodar-ss-col-config-btn-cancel'

// Global setup
config.global.plugins = [createBootstrap()]

// Mock clipboard (NOTE: has to be done in module root)
const mockCopy = vi.fn()
vi.mock('@vueuse/core', async () => {
  const actual = await vi.importActual('@vueuse/core')
  return { ...actual, useClipboard: () => ({ copy: mockCopy }) }
})

describe('ColumnConfigModal.vue', () => {
  async function clickUpdate (wrapper: VueWrapper): Promise<void> {
    return wrapper.find(updateBtnSel).trigger('click')
  }

  function expectFetch () {
    expect(fetch).toHaveBeenCalledWith(
      url, expect.objectContaining({ body: JSON.stringify(reqBody) }))
  }

  function getMockGridApi (nodes?: Array<object>): GridApi {
    let forEachNode
    if (nodes) {
      forEachNode = vi.fn((callback) => {
        nodes.forEach(node => callback(node))
      })
    } else forEachNode = vi.fn()
    return {
      forEachNode: forEachNode,
      getColumn: vi.fn(),
      refreshCells: vi.fn()
    } as unknown as GridApi
  }

  function setOntologyInput (allowList?: boolean, ontologies?: Array<string>) {
    params.colType = EDIT_COL_TYPE_ONTOLOGY
    params.editConfigField.allow_list = allowList || false
    params.editConfigField.format = EDIT_FORMAT_ONTOLOGY
    params.editConfigField.ontologies = ontologies || []
    params.editConfigField.type = EDIT_HEADER_TYPE_CHAR
    params.headerType = EDIT_HEADER_TYPE_CHAR
  }

  function setProtocolInput (setDefault: boolean | undefined) {
    params.colType = EDIT_COL_TYPE_PROTOCOL
    params.editConfigField.format = EDIT_FORMAT_PROTOCOL
    params.editConfigField.type = EDIT_HEADER_TYPE_PROTOCOL
    params.headerType = EDIT_HEADER_TYPE_PROTOCOL
    params.objCls = DB_OBJ_CLASS_PROCESS
    if (setDefault !== false) params.editConfigField.default = protocolUuid
  }

  function setBasicCharInput (format: string) {
    params.colType = null
    params.editConfigField.format = format
    params.editConfigField.type = EDIT_HEADER_TYPE_CHAR
    params.headerType = EDIT_HEADER_TYPE_CHAR
  }

  beforeEach(() => {
    vi.resetAllMocks()

    setActivePinia(createPinia())
    const appStore = useAppStore()
    appStore.currentStudyUuid = STUDY_UUID
    appStore.projectUuid = PROJECT_UUID
    appStore.sodarContext = copy(sodarContext) as SodarContext

    const editStore = useEditStore()
    editStore.editContext = copy(studyTablesEdit.edit_context) as StudyEditContext
    editStore.editDataUpdated = false

    const tableStore = useTableStore()
    tableStore.gridApi.study = getMockGridApi()
    tableStore.gridApi.assays[ASSAY_UUID] = getMockGridApi()

    params = copy(defaultParams) as HeaderEditRendererParams
    params.column = { getColId: () => { return 'col0' }} as unknown as Column
    reqBody = copy(defaultReqBody) as EditConfigRequestBody
    resBody = copy(defaultResBody) as GenericResponseBody
  })

  async function showModal (): Promise<VueWrapper> {
    global.fetch = vi.fn(() => Promise.resolve({
      json: () => Promise.resolve(resBody), status: 200
    } as Response))
    const wrapper = mount(ColumnConfigModal)
    wrapper.vm.show(params)
    await nextTick() // Must wait for all reactive vals to update
    return wrapper
  }

  test('render source name field', async () => {
    const wrapper = await showModal()
    expect(wrapper.find('.modal-title').text()).toBe(
      defaultParams.editConfigField.name)
    expect(wrapper.find('#sodar-ss-col-config-content').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-col-config-table').exists()).toBe(true)
    expect(wrapper.find(copyBtnSel).attributes().disabled).toBeDefined()
    expect(wrapper.find(pasteInputSel).attributes().disabled).toBeDefined()
    expect(wrapper.find(editableCheckSel).exists()).toBe(true)

    expect(wrapper.find(bodyNameSel).exists()).toBe(true)
    expect(wrapper.find(bodyProtocolSel).exists()).toBe(false)
    expect(wrapper.find(bodyContactSel).exists()).toBe(false)
    expect(wrapper.find(bodyDateSel).exists()).toBe(false)
    expect(wrapper.find(bodyOntologySel).exists()).toBe(false)
    expect(wrapper.find(bodyExtSel).exists()).toBe(false)
    expect(wrapper.find(bodyBasicSel).exists()).toBe(false)
    expect(wrapper.find(ontAllowTableSel).exists()).toBe(false)
    expect(wrapper.find(ontDefaultTableSel).exists()).toBe(false)

    expect(wrapper.find(defaultInputSel).exists()).toBe(false)
    expect(wrapper.find(defaultSelectSel).exists()).toBe(false)
    expect(wrapper.find(msgNameSel).exists()).toBe(true)
  })

  test('render sample name field', async () => {
    params.itemType = EDIT_ITEM_TYPE_SAMPLE
    const wrapper = await showModal()
    expect(wrapper.find(copyBtnSel).attributes().disabled).toBeDefined()
    expect(wrapper.find(pasteInputSel).attributes().disabled).toBeDefined()
    expect(wrapper.find(editableCheckSel).exists()).toBe(true)
    expect(wrapper.find(bodyNameSel).exists()).toBe(true)
    // Default suffix field should be visible as text input
    const defaultInput = wrapper.find(defaultInputSel)
    expect(defaultInput.exists()).toBe(true)
    expect(defaultInput.attributes().value).toBe('')
    expect(wrapper.find(msgNameSel).exists()).toBe(true)
    expect(wrapper.find(defaultSelectSel).exists()).toBe(false)
  })

  test('render sample name field with default', async () => {
    params.itemType = EDIT_ITEM_TYPE_SAMPLE
    params.editConfigField.default = '-N1'
    const wrapper = await showModal()
    const defaultInput = wrapper.find(defaultInputSel)
    expect(defaultInput.exists()).toBe(true)
    expect(defaultInput.attributes().value).toBe('-N1')
  })

  test('render material name field', async () => {
    params.itemType = EDIT_ITEM_TYPE_MATERIAL
    const wrapper = await showModal()
    expect(wrapper.find(copyBtnSel).attributes().disabled).toBeDefined()
    expect(wrapper.find(pasteInputSel).attributes().disabled).toBeDefined()
    expect(wrapper.find(editableCheckSel).exists()).toBe(true)
    expect(wrapper.find(bodyNameSel).exists()).toBe(true)
    expect(wrapper.find(defaultInputSel).exists()).toBe(true)
    expect(wrapper.find(msgNameSel).exists()).toBe(true)
  })

  test('render data name field', async () => {
    params.colType = EDIT_COL_TYPE_LINK
    params.itemType = EDIT_ITEM_TYPE_DATA
    const wrapper = await showModal()
    expect(wrapper.find(copyBtnSel).attributes().disabled).toBeDefined()
    expect(wrapper.find(pasteInputSel).attributes().disabled).toBeDefined()
    expect(wrapper.find(editableCheckSel).exists()).toBe(true)
    expect(wrapper.find(bodyNameSel).exists()).toBe(true)
    // Default should not be visible
    expect(wrapper.find(defaultInputSel).exists()).toBe(false)
    expect(wrapper.find(msgNameSel).exists()).toBe(true)
  })

  test('update editable', async () => {
    const editStore = useEditStore()
    const tableStore = useTableStore()
    expect(editStore.editDataUpdated).toBe(false)
    expect(tableStore.gridApi.study!.refreshCells).not.toHaveBeenCalled()
    expect(tableStore.gridApi.assays[
      ASSAY_UUID]!.refreshCells).not.toHaveBeenCalled()

    const wrapper = await showModal()
    expect(fetch).not.toHaveBeenCalled()
    await wrapper.find(editableCheckSel).trigger('click')
    await clickUpdate(wrapper)

    reqBody.fields[0]!.config.editable = false
    expectFetch()
    expect(editStore.editDataUpdated).toBe(true)
    const refreshParams = { columns: ['col0'], force: true }
    expect(tableStore.gridApi.study!.refreshCells).toHaveBeenCalledWith(
      refreshParams)
    expect(tableStore.gridApi.assays[
      ASSAY_UUID]!.refreshCells).toHaveBeenCalledWith(refreshParams)
  })

  test('cancel with unchanged editable value', async () => {
    const editStore = useEditStore()
    const tableStore = useTableStore()
    expect(editStore.editDataUpdated).toBe(false)
    expect(tableStore.gridApi.study!.refreshCells).not.toHaveBeenCalled()
    expect(tableStore.gridApi.assays[
      ASSAY_UUID]!.refreshCells).not.toHaveBeenCalled()

    const wrapper = await showModal()
    expect(fetch).not.toHaveBeenCalled()
    // No editable button click
    await wrapper.find(cancelBtnSel).trigger('click')

    expect(fetch).not.toHaveBeenCalled()
    expect(editStore.editDataUpdated).toBe(false)
    expect(tableStore.gridApi.study!.refreshCells).not.toHaveBeenCalled()
    expect(tableStore.gridApi.assays[
      ASSAY_UUID]!.refreshCells).not.toHaveBeenCalled()
  })

  test('cancel with changed editable value', async () => {
    const editStore = useEditStore()
    const tableStore = useTableStore()
    expect(editStore.editDataUpdated).toBe(false)
    expect(tableStore.gridApi.study!.refreshCells).not.toHaveBeenCalled()
    expect(tableStore.gridApi.assays[
      ASSAY_UUID]!.refreshCells).not.toHaveBeenCalled()

    const wrapper = await showModal()
    expect(fetch).not.toHaveBeenCalled()
    await wrapper.find(editableCheckSel).trigger('click')
    await wrapper.find(cancelBtnSel).trigger('click')

    expect(fetch).not.toHaveBeenCalled()
    expect(editStore.editDataUpdated).toBe(false)
    expect(tableStore.gridApi.study!.refreshCells).not.toHaveBeenCalled()
    expect(tableStore.gridApi.assays[
      ASSAY_UUID]!.refreshCells).not.toHaveBeenCalled()
  })

  test('update name field default', async () => {
    params.itemType = EDIT_ITEM_TYPE_SAMPLE
    const wrapper = await showModal()
    expect(fetch).not.toHaveBeenCalled()
    await wrapper.find(defaultInputSel).setValue('-T1')
    await clickUpdate(wrapper)
    reqBody.fields[0]!.config.default = '-T1'
    expectFetch()
  })

  test('render protocol field', async () => {
    setProtocolInput(false)
    const wrapper = await showModal()
    expect(wrapper.find(copyBtnSel).attributes().disabled).toBeDefined()
    expect(wrapper.find(pasteInputSel).attributes().disabled).toBeDefined()
    expect(wrapper.find(editableCheckSel).exists()).toBe(true)

    expect(wrapper.find(bodyNameSel).exists()).toBe(false)
    expect(wrapper.find(bodyProtocolSel).exists()).toBe(true)
    expect(wrapper.find(bodyContactSel).exists()).toBe(false)
    expect(wrapper.find(bodyDateSel).exists()).toBe(false)
    expect(wrapper.find(bodyOntologySel).exists()).toBe(false)
    expect(wrapper.find(bodyExtSel).exists()).toBe(false)
    expect(wrapper.find(bodyBasicSel).exists()).toBe(false)
    expect(wrapper.find(ontAllowTableSel).exists()).toBe(false)
    expect(wrapper.find(ontDefaultTableSel).exists()).toBe(false)

    expect(wrapper.find(defaultInputSel).exists()).toBe(false)
    expect(wrapper.find(defaultSelectSel).exists()).toBe(true)
    const options = wrapper.findAll(defaultOptionSel)
    expect(options.length).toBe(4) // 3 + 1 for empty
    // Empty should be selected
    expect(options[0]?.text()).toBe('-')
    expect(options[0]?.attributes().selected).toBeDefined()
  })

  test('render protocol field with default', async () => {
    setProtocolInput(true)
    const wrapper = await showModal()
    const options = wrapper.findAll(defaultOptionSel)
    // First protocol should be selected
    expect(options[1]?.text()).toBe(protocolName)
    expect(options[1]?.attributes().selected).toBeDefined()
  })

  test('update protocol value from empty', async () => {
    setProtocolInput(false)
    const wrapper = await showModal()
    const select = wrapper.find(defaultSelectSel)
    await select.setValue(protocolUuid)
    await clickUpdate(wrapper)
    reqBody.fields[0]!.config.default = protocolUuid
    reqBody.fields[0]!.config.format = EDIT_FORMAT_PROTOCOL
    reqBody.fields[0]!.config.type = EDIT_HEADER_TYPE_PROTOCOL
    expectFetch()
  })

  test('update protocol value to empty', async () => {
    setProtocolInput(true)
    const wrapper = await showModal()
    const select = wrapper.find(defaultSelectSel)
    await select.setValue('')
    await clickUpdate(wrapper)
    reqBody.fields[0]!.config.default = ''
    reqBody.fields[0]!.config.format = EDIT_FORMAT_PROTOCOL
    reqBody.fields[0]!.config.type = EDIT_HEADER_TYPE_PROTOCOL
    expectFetch()
  })

  test('render contact field', async () => {
    params.colType = EDIT_COL_TYPE_CONTACT
    params.editConfigField = {
      name: 'Performer',
      type: EDIT_HEADER_TYPE_PERFORMER
    }
    params.headerType = EDIT_HEADER_TYPE_PERFORMER
    const wrapper = await showModal()
    expect(wrapper.find(copyBtnSel).attributes().disabled).toBeDefined()
    expect(wrapper.find(pasteInputSel).attributes().disabled).toBeDefined()
    expect(wrapper.find(editableCheckSel).exists()).toBe(true)

    expect(wrapper.find(bodyNameSel).exists()).toBe(false)
    expect(wrapper.find(bodyProtocolSel).exists()).toBe(false)
    expect(wrapper.find(bodyContactSel).exists()).toBe(true)
    expect(wrapper.find(bodyDateSel).exists()).toBe(false)
    expect(wrapper.find(bodyOntologySel).exists()).toBe(false)
    expect(wrapper.find(bodyExtSel).exists()).toBe(false)
    expect(wrapper.find(bodyBasicSel).exists()).toBe(false)
    expect(wrapper.find(ontAllowTableSel).exists()).toBe(false)
    expect(wrapper.find(ontDefaultTableSel).exists()).toBe(false)
  })

  test('render date field', async () => {
    params.colType = EDIT_COL_TYPE_DATE
    params.editConfigField = {
      format: EDIT_FORMAT_DATE,
      name: 'Perform date',
      type: EDIT_HEADER_TYPE_PERFORM_DATE
    }
    params.headerType = EDIT_HEADER_TYPE_PERFORM_DATE
    const wrapper = await showModal()
    expect(wrapper.find(copyBtnSel).attributes().disabled).toBeDefined()
    expect(wrapper.find(pasteInputSel).attributes().disabled).toBeDefined()
    expect(wrapper.find(editableCheckSel).exists()).toBe(true)
    expect(wrapper.find(bodyNameSel).exists()).toBe(false)
    expect(wrapper.find(bodyProtocolSel).exists()).toBe(false)
    expect(wrapper.find(bodyContactSel).exists()).toBe(false)
    expect(wrapper.find(bodyDateSel).exists()).toBe(true)
    expect(wrapper.find(bodyOntologySel).exists()).toBe(false)
    expect(wrapper.find(bodyExtSel).exists()).toBe(false)
    expect(wrapper.find(bodyBasicSel).exists()).toBe(false)
    expect(wrapper.find(ontAllowTableSel).exists()).toBe(false)
    expect(wrapper.find(ontDefaultTableSel).exists()).toBe(false)
  })

  test('render ontology field with default settings', async () => {
    setOntologyInput()
    const wrapper = await showModal()
    expect(wrapper.find(copyBtnSel).attributes().disabled).not.toBeDefined()
    expect(wrapper.find(pasteInputSel).attributes().disabled).not.toBeDefined()
    expect(wrapper.find(editableCheckSel).exists()).toBe(true)
    expect(wrapper.find(bodyNameSel).exists()).toBe(false)
    expect(wrapper.find(bodyProtocolSel).exists()).toBe(false)
    expect(wrapper.find(bodyContactSel).exists()).toBe(false)
    expect(wrapper.find(bodyDateSel).exists()).toBe(false)
    expect(wrapper.find(bodyOntologySel).exists()).toBe(true)
    expect(wrapper.find(bodyExtSel).exists()).toBe(false)
    expect(wrapper.find(bodyBasicSel).exists()).toBe(false)

    expect(wrapper.find(
      ontDefaultDeleteSel).attributes().disabled).toBeDefined()

    expect(wrapper.find(
      allowListCheckSel).attributes().disabled).not.toBeDefined()
    expect(wrapper.find(ontAllowTableSel).exists()).toBe(true)
    expect(wrapper.find(trOntInsertSel).exists()).toBe(true)
    expect(wrapper.findAll(trOntAllowSel).length).toBe(0)
    expect(wrapper.find(alertOntAllSel).exists()).toBe(true)

    expect(wrapper.find(ontDefaultTableSel).exists()).toBe(true)
    expect(wrapper.find(trOntDefaultEmptySel).exists()).toBe(true)
    expect(wrapper.find(trOntDefaultTermSel).exists()).toBe(false)
  })

  test('render ontology field with existing ontology', async () => {
    setOntologyInput()
    params.editConfigField.ontologies = [OBO_ID_NCBITAXON]

    const wrapper = await showModal()
    expect(wrapper.find(
      allowListCheckSel).attributes().disabled).not.toBeDefined()

    const allowed = wrapper.findAll(trOntAllowSel)
    expect(allowed.length).toBe(1)
    expect(allowed[0]?.text()).toBe(OBO_ID_NCBITAXON)

    const options = wrapper.findAll(ontInsertOptionSel)
    // Should be one less than ontology length + one for "select ontology"
    expect(options.length).toBe(ontologyCount)

    const moveButtons = wrapper.findAll(ontMoveBtnSel)
    expect(moveButtons.length).toBe(2)
    for (let i = 0; i < 2; i ++) {
      // Move buttons should be disabled
      expect(moveButtons[i]?.attributes().disabled).toBeDefined()
    }

    expect(wrapper.find(alertOntAllSel).exists()).toBe(false)
  })

  test('render ontology field with multiple existing ontologies', async () => {
    setOntologyInput()
    params.editConfigField.ontologies = [
      OBO_ID_NCBITAXON, OBO_ID_ORDO, OBO_ID_UBERON]

    const wrapper = await showModal()
    expect(wrapper.find(
      allowListCheckSel).attributes().disabled).not.toBeDefined()

    const allowed = wrapper.findAll(trOntAllowSel)
    expect(allowed.length).toBe(3)
    expect(allowed[0]?.text()).toBe(OBO_ID_NCBITAXON)

    const options = wrapper.findAll(ontInsertOptionSel)
    expect(options.length).toBe(ontologyCount - 2)

    const upButtons = wrapper.findAll(ontMoveUpBtnSel)
    expect(upButtons[0]?.attributes().disabled).toBeDefined()
    expect(upButtons[1]?.attributes().disabled).not.toBeDefined()
    expect(upButtons[2]?.attributes().disabled).not.toBeDefined()

    const downButtons = wrapper.findAll(ontMoveDownBtnSel)
    expect(downButtons[0]?.attributes().disabled).not.toBeDefined()
    expect(downButtons[1]?.attributes().disabled).not.toBeDefined()
    expect(downButtons[2]?.attributes().disabled).toBeDefined()

    expect(wrapper.find(alertOntAllSel).exists()).toBe(false)
  })

  test('render ontology default with default value', async () => {
    setOntologyInput()
    params.editConfigField.default = [ontologyTerm]
    const wrapper = await showModal()
    expect(wrapper.find(
      ontDefaultDeleteSel).attributes().disabled).not.toBeDefined()
    expect(wrapper.find(trOntDefaultEmptySel).exists()).toBe(false)
    const defaultTerms = wrapper.findAll(trOntDefaultTermSel)
    expect(defaultTerms.length).toBe(1)
    expect(defaultTerms![0]!.find('td').text()).toBe(ontologyTerm.name)
  })

  test('render ontology default with multiple default values', async () => {
    setOntologyInput()
    params.editConfigField.default = [ontologyTerm, ontologyTerm2]
    const wrapper = await showModal()
    expect(wrapper.find(trOntDefaultEmptySel).exists()).toBe(false)
    expect(wrapper.findAll(trOntDefaultTermSel).length).toBe(2)
  })

  test('render ontology field with HP preset', async () => {
    setOntologyInput()
    params.editConfigField.name = OBO_HEADER_HP
    params.editConfigField.ontologies = [] // No initial setting

    const wrapper = await showModal()
    // Allow list should be disabled
    expect(wrapper.find(allowListCheckSel).attributes().disabled).toBeDefined()

    // HP should be the only allowed preset
    const allowed = wrapper.findAll(trOntAllowSel)
    expect(allowed.length).toBe(1)
    expect(allowed[0]?.text()).toBe(OBO_ID_HP)

    // All buttons should be disabled
    expect(wrapper.find(ontMoveUpBtnSel).attributes().disabled).toBeDefined()
    expect(wrapper.find(ontMoveDownBtnSel).attributes().disabled).toBeDefined()
    expect(wrapper.find(ontDeleteBtnSel).attributes().disabled).toBeDefined()

    // Insert and alert should not exist
    expect(wrapper.find(trOntInsertSel).exists()).toBe(false)
    expect(wrapper.find(alertOntAllSel).exists()).toBe(false)
  })

  test('render ontology field with OMIM preset', async () => {
    setOntologyInput()
    params.editConfigField.name = OBO_HEADER_OMIM
    params.editConfigField.ontologies = []
    const wrapper = await showModal()
    expect(wrapper.find(allowListCheckSel).attributes().disabled).toBeDefined()
    const allowed = wrapper.findAll(trOntAllowSel)
    expect(allowed.length).toBe(1)
    expect(allowed[0]?.text()).toBe(OBO_ID_OMIM)
    expect(wrapper.find(ontMoveUpBtnSel).attributes().disabled).toBeDefined()
    expect(wrapper.find(ontMoveDownBtnSel).attributes().disabled).toBeDefined()
    expect(wrapper.find(ontDeleteBtnSel).attributes().disabled).toBeDefined()
    expect(wrapper.find(trOntInsertSel).exists()).toBe(false)
    expect(wrapper.find(alertOntAllSel).exists()).toBe(false)
  })

  test('render ontology field with ORDO preset', async () => {
    setOntologyInput()
    params.editConfigField.name = OBO_HEADER_ORDO
    params.editConfigField.ontologies = []
    const wrapper = await showModal()
    expect(wrapper.find(allowListCheckSel).attributes().disabled).toBeDefined()
    const allowed = wrapper.findAll(trOntAllowSel)
    expect(allowed.length).toBe(1)
    expect(allowed[0]?.text()).toBe(OBO_ID_ORDO)
    expect(wrapper.find(ontMoveUpBtnSel).attributes().disabled).toBeDefined()
    expect(wrapper.find(ontMoveDownBtnSel).attributes().disabled).toBeDefined()
    expect(wrapper.find(ontDeleteBtnSel).attributes().disabled).toBeDefined()
    expect(wrapper.find(trOntInsertSel).exists()).toBe(false)
    expect(wrapper.find(alertOntAllSel).exists()).toBe(false)
  })

  test('update ontology field with HP preset', async () => {
    setOntologyInput()
    params.editConfigField.name = OBO_HEADER_HP
    params.editConfigField.ontologies = []
    const wrapper = await showModal()
    await clickUpdate(wrapper)
    reqBody.fields[0]!.config.allow_list = true // List allowed
    reqBody.fields[0]!.config.format = EDIT_FORMAT_ONTOLOGY
    reqBody.fields[0]!.config.name = OBO_HEADER_HP
    reqBody.fields[0]!.config.ontologies = [OBO_ID_HP]
    reqBody.fields[0]!.config.type = EDIT_HEADER_TYPE_CHAR
    expectFetch()
  })

  test('update ontology field with OMIM preset', async () => {
    setOntologyInput()
    params.editConfigField.name = OBO_HEADER_OMIM
    params.editConfigField.ontologies = []
    const wrapper = await showModal()
    await clickUpdate(wrapper)
    reqBody.fields[0]!.config.allow_list = false // List not allowed
    reqBody.fields[0]!.config.format = EDIT_FORMAT_ONTOLOGY
    reqBody.fields[0]!.config.name = OBO_HEADER_OMIM
    reqBody.fields[0]!.config.ontologies = [OBO_ID_OMIM]
    reqBody.fields[0]!.config.type = EDIT_HEADER_TYPE_CHAR
    expectFetch()
  })

  test('update ontology field with ORDO preset', async () => {
    setOntologyInput()
    params.editConfigField.name = OBO_HEADER_ORDO
    params.editConfigField.ontologies = []
    const wrapper = await showModal()
    await clickUpdate(wrapper)
    reqBody.fields[0]!.config.allow_list = false // List not allowed
    reqBody.fields[0]!.config.format = EDIT_FORMAT_ONTOLOGY
    reqBody.fields[0]!.config.name = OBO_HEADER_ORDO
    reqBody.fields[0]!.config.ontologies = [OBO_ID_ORDO]
    reqBody.fields[0]!.config.type = EDIT_HEADER_TYPE_CHAR
    expectFetch()
  })

  test('update ontology field with allow_list=true', async () => {
    setOntologyInput()
    const wrapper = await showModal()
    await wrapper.find(allowListCheckSel).trigger('click')
    await clickUpdate(wrapper)
    reqBody.fields[0]!.config.allow_list = true // Should be changed
    reqBody.fields[0]!.config.format = EDIT_FORMAT_ONTOLOGY
    reqBody.fields[0]!.config.ontologies = []
    reqBody.fields[0]!.config.type = EDIT_HEADER_TYPE_CHAR
    expectFetch()
  })

  test('update ontology field with allowed ontology insert', async () => {
    setOntologyInput()
    const wrapper = await showModal()
    await wrapper.find(ontInsertSelectSel).setValue(OBO_ID_NCBITAXON)
    await wrapper.find(ontInsertBtnSel).trigger('click')
    await clickUpdate(wrapper)
    reqBody.fields[0]!.config.allow_list = false
    reqBody.fields[0]!.config.format = EDIT_FORMAT_ONTOLOGY
    reqBody.fields[0]!.config.ontologies = [OBO_ID_NCBITAXON] // Add ontology
    reqBody.fields[0]!.config.type = EDIT_HEADER_TYPE_CHAR
    expectFetch()
  })

  test('update ontology field with insert and existing ontology', async () => {
    setOntologyInput()
    params.editConfigField.ontologies = [OBO_ID_UBERON]
    const wrapper = await showModal()
    await wrapper.find(ontInsertSelectSel).setValue(OBO_ID_NCBITAXON)
    await wrapper.find(ontInsertBtnSel).trigger('click')
    await clickUpdate(wrapper)
    reqBody.fields[0]!.config.allow_list = false
    reqBody.fields[0]!.config.format = EDIT_FORMAT_ONTOLOGY
    // Both ontologies should exist in the order of addition
    reqBody.fields[0]!.config.ontologies = [OBO_ID_UBERON, OBO_ID_NCBITAXON]
    reqBody.fields[0]!.config.type = EDIT_HEADER_TYPE_CHAR
    expectFetch()
  })

  test('update ontology field with ontology move down', async () => {
    setOntologyInput()
    params.editConfigField.ontologies = [
      OBO_ID_NCBITAXON, OBO_ID_ORDO, OBO_ID_UBERON]
    const wrapper = await showModal()
    await wrapper.findAll(ontMoveDownBtnSel)[0]!.trigger('click')
    await clickUpdate(wrapper)
    reqBody.fields[0]!.config.allow_list = false
    reqBody.fields[0]!.config.format = EDIT_FORMAT_ONTOLOGY
    // Order should be changed
    reqBody.fields[0]!.config.ontologies = [
      OBO_ID_ORDO, OBO_ID_NCBITAXON, OBO_ID_UBERON]
    reqBody.fields[0]!.config.type = EDIT_HEADER_TYPE_CHAR
    expectFetch()
  })

  test('update ontology field with ontology move up', async () => {
    setOntologyInput()
    params.editConfigField.ontologies = [
      OBO_ID_NCBITAXON, OBO_ID_ORDO, OBO_ID_UBERON]
    const wrapper = await showModal()
    await wrapper.findAll(ontMoveUpBtnSel)[1]!.trigger('click')
    await clickUpdate(wrapper)
    reqBody.fields[0]!.config.allow_list = false
    reqBody.fields[0]!.config.format = EDIT_FORMAT_ONTOLOGY
    // Order should be changed
    reqBody.fields[0]!.config.ontologies = [
      OBO_ID_ORDO, OBO_ID_NCBITAXON, OBO_ID_UBERON]
    reqBody.fields[0]!.config.type = EDIT_HEADER_TYPE_CHAR
    expectFetch()
  })

  test('update ontology field with allowed ontology delete', async () => {
    setOntologyInput()
    params.editConfigField.ontologies = [OBO_ID_UBERON]
    const wrapper = await showModal()
    await wrapper.find(ontDeleteBtnSel).trigger('click')
    await clickUpdate(wrapper)
    reqBody.fields[0]!.config.allow_list = false
    reqBody.fields[0]!.config.format = EDIT_FORMAT_ONTOLOGY
    reqBody.fields[0]!.config.ontologies = [] // List should be empty
    reqBody.fields[0]!.config.type = EDIT_HEADER_TYPE_CHAR
    expectFetch()
  })

  test('update ontology field default', async () => {
    setOntologyInput()
    const wrapper = await showModal()
    await wrapper.find(
      ontDefaultInputSel).setValue(JSON.stringify(ontologyTerm))
    await clickUpdate(wrapper)
    reqBody.fields[0]!.config.allow_list = false
    reqBody.fields[0]!.config.default = [ontologyTerm]
    reqBody.fields[0]!.config.format = EDIT_FORMAT_ONTOLOGY
    reqBody.fields[0]!.config.ontologies = []
    reqBody.fields[0]!.config.type = EDIT_HEADER_TYPE_CHAR
    expectFetch()
  })

  test('update ontology field default with single term as list', async () => {
    setOntologyInput()
    const wrapper = await showModal()
    await wrapper.find(
      ontDefaultInputSel).setValue(JSON.stringify([ontologyTerm]))
    await clickUpdate(wrapper)
    reqBody.fields[0]!.config.allow_list = false
    reqBody.fields[0]!.config.default = [ontologyTerm]
    reqBody.fields[0]!.config.format = EDIT_FORMAT_ONTOLOGY
    reqBody.fields[0]!.config.ontologies = []
    reqBody.fields[0]!.config.type = EDIT_HEADER_TYPE_CHAR
    expectFetch()
  })

  test('update ontology default with existing value', async () => {
    setOntologyInput()
    params.editConfigField.default = [ontologyTerm]
    const wrapper = await showModal()
    await wrapper.find(
      ontDefaultInputSel).setValue(JSON.stringify(ontologyTerm2))
    await clickUpdate(wrapper)
    reqBody.fields[0]!.config.allow_list = false
    reqBody.fields[0]!.config.default = [ontologyTerm2] // Should be updated
    reqBody.fields[0]!.config.format = EDIT_FORMAT_ONTOLOGY
    reqBody.fields[0]!.config.ontologies = []
    reqBody.fields[0]!.config.type = EDIT_HEADER_TYPE_CHAR
    expectFetch()
  })

  test('update ontology default with multiple values', async () => {
    setOntologyInput()
    params.editConfigField.allow_list = true
    const wrapper = await showModal()
    await wrapper.find(
      ontDefaultInputSel).setValue(
        JSON.stringify([ontologyTerm, ontologyTerm2]))
    await clickUpdate(wrapper)
    reqBody.fields[0]!.config.allow_list = true
    reqBody.fields[0]!.config.default = [ontologyTerm, ontologyTerm2]
    reqBody.fields[0]!.config.format = EDIT_FORMAT_ONTOLOGY
    reqBody.fields[0]!.config.ontologies = []
    reqBody.fields[0]!.config.type = EDIT_HEADER_TYPE_CHAR
    expectFetch()
  })

  test('update ontology default with allow_list=false', async () => {
    setOntologyInput()
    expect(params.editConfigField.allow_list).toBe(false)
    const wrapper = await showModal()
    await wrapper.find(
      ontDefaultInputSel).setValue(
        JSON.stringify([ontologyTerm, ontologyTerm2]))
    await clickUpdate(wrapper)
    reqBody.fields[0]!.config.allow_list = false
    reqBody.fields[0]!.config.default = '' // Should be empty
    reqBody.fields[0]!.config.format = EDIT_FORMAT_ONTOLOGY
    reqBody.fields[0]!.config.ontologies = []
    reqBody.fields[0]!.config.type = EDIT_HEADER_TYPE_CHAR
    expectFetch()
  })

  test('update ontology default with invalid JSON', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => undefined)
    setOntologyInput()
    const wrapper = await showModal()
    await wrapper.find(
      ontDefaultInputSel).setValue('{"invalid: "json')
    await clickUpdate(wrapper)
    reqBody.fields[0]!.config.allow_list = false
    reqBody.fields[0]!.config.default = '' // Should be empty
    reqBody.fields[0]!.config.format = EDIT_FORMAT_ONTOLOGY
    reqBody.fields[0]!.config.ontologies = []
    reqBody.fields[0]!.config.type = EDIT_HEADER_TYPE_CHAR
    expectFetch()
  })

  test('update ontology default with invalid term', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => undefined)
    const term = copy(ontologyTerm) as SheetTableOntologyRef
    term.name = '' // Empty name is not allowed
    setOntologyInput()
    const wrapper = await showModal()
    await wrapper.find(ontDefaultInputSel).setValue(JSON.stringify(term))
    await clickUpdate(wrapper)
    reqBody.fields[0]!.config.allow_list = false
    reqBody.fields[0]!.config.default = '' // Should be empty
    reqBody.fields[0]!.config.format = EDIT_FORMAT_ONTOLOGY
    reqBody.fields[0]!.config.ontologies = []
    reqBody.fields[0]!.config.type = EDIT_HEADER_TYPE_CHAR
    expectFetch()
  })

  test('update ontology field with deleted default', async () => {
    setOntologyInput()
    params.editConfigField.default = [ontologyTerm]
    const wrapper = await showModal()
    await wrapper.find(ontDefaultDeleteSel).trigger('click')
    await clickUpdate(wrapper)
    reqBody.fields[0]!.config.allow_list = false
    reqBody.fields[0]!.config.default = '' // Should be empty
    reqBody.fields[0]!.config.format = EDIT_FORMAT_ONTOLOGY
    reqBody.fields[0]!.config.ontologies = []
    reqBody.fields[0]!.config.type = EDIT_HEADER_TYPE_CHAR
    expectFetch()
  })

  test('render external links field', async () => {
    params.colType = EDIT_COL_TYPE_EXT_LINKS
    params.editConfigField = {
      format: EDIT_FORMAT_EXT,
      name: 'External links',
      type: EDIT_HEADER_TYPE_CHAR
    }
    params.headerType = EDIT_HEADER_TYPE_CHAR
    const wrapper = await showModal()
    expect(wrapper.find(copyBtnSel).attributes().disabled).toBeDefined()
    expect(wrapper.find(pasteInputSel).attributes().disabled).toBeDefined()
    expect(wrapper.find(editableCheckSel).exists()).toBe(true)
    expect(wrapper.find(bodyNameSel).exists()).toBe(false)
    expect(wrapper.find(bodyProtocolSel).exists()).toBe(false)
    expect(wrapper.find(bodyContactSel).exists()).toBe(false)
    expect(wrapper.find(bodyDateSel).exists()).toBe(false)
    expect(wrapper.find(bodyExtSel).exists()).toBe(true)
    expect(wrapper.find(bodyBasicSel).exists()).toBe(false)
    expect(wrapper.find(ontAllowTableSel).exists()).toBe(false)
  })

  test('render basic string field', async () => {
    setBasicCharInput(EDIT_FORMAT_STRING)
    const wrapper = await showModal()
    expect(wrapper.find(copyBtnSel).attributes().disabled).not.toBeDefined()
    expect(wrapper.find(pasteInputSel).attributes().disabled).not.toBeDefined()
    expect(wrapper.find(editableCheckSel).exists()).toBe(true)
    expect(wrapper.find(bodyNameSel).exists()).toBe(false)
    expect(wrapper.find(bodyProtocolSel).exists()).toBe(false)
    expect(wrapper.find(bodyContactSel).exists()).toBe(false)
    expect(wrapper.find(bodyDateSel).exists()).toBe(false)
    expect(wrapper.find(bodyExtSel).exists()).toBe(false)
    expect(wrapper.find(bodyBasicSel).exists()).toBe(true)
    expect(wrapper.find(ontAllowTableSel).exists()).toBe(false)

    expect(wrapper.find(trSelectSel).exists()).toBe(false)
    expect(wrapper.find(trRangeSel).exists()).toBe(false)
    expect(wrapper.find(trRegexSel).exists()).toBe(true)
    expect(wrapper.find(trDefaultValSel).exists()).toBe(true)
    expect(wrapper.find(trDefaultFillSel).exists()).toBe(true)
    expect(wrapper.find(trUnitSel).exists()).toBe(false)
    expect(wrapper.find(trUnitDefaultSel).exists()).toBe(false)

    expect(wrapper.find(formatSelectSel).exists()).toBe(true)
    const options = wrapper.findAll(formatOptionSel)
    expect(options.length).toBe(4)
    expect(options[0]?.text()).toBe(EDIT_FORMAT_STRING)
    expect(options[0]?.attributes().selected).toBeDefined()
  })

  test('update basic field format to integer', async () => {
    setBasicCharInput(EDIT_FORMAT_STRING)
    const wrapper = await showModal()
    await wrapper.find(formatSelectSel).setValue(EDIT_FORMAT_INTEGER)
    await clickUpdate(wrapper)
    reqBody.fields[0]!.config.format = EDIT_FORMAT_INTEGER
    reqBody.fields[0]!.config.type = EDIT_HEADER_TYPE_CHAR
    expectFetch()
  })

  test('render basic select field without options', async () => {
    setBasicCharInput(EDIT_FORMAT_SELECT)
    const wrapper = await showModal()
    expect(wrapper.find(trSelectSel).exists()).toBe(true)
    expect(wrapper.find(formatSelectSel).exists()).toBe(true)
    const input = wrapper.find(valueOptInputSel)
    expect(input.exists()).toBe(true)
    expect(input.text()).toBe('')
  })

  test('render basic select field with options', async () => {
    setBasicCharInput(EDIT_FORMAT_SELECT)
    params.editConfigField.options = ['opt1', 'opt2']
    const wrapper = await showModal()
    const input = wrapper.find(valueOptInputSel)
    expect(input.attributes().value).toBe('opt1\nopt2')
    expect(input.classes()).not.toContain('text-danger')
    expect(wrapper.find(updateBtnSel).attributes().disabled).not.toBeDefined()
  })

  test('update basic select options', async () => {
    setBasicCharInput(EDIT_FORMAT_SELECT)
    params.editConfigField.options = ['opt1', 'opt2']
    const wrapper = await showModal()
    await wrapper.find(valueOptInputSel).setValue('opt1\nopt1.5\nopt2')
    await clickUpdate(wrapper)

    reqBody.fields[0]!.config.format = EDIT_FORMAT_SELECT
    delete reqBody.fields[0]!.config.regex
    reqBody.fields[0]!.config.type = EDIT_HEADER_TYPE_CHAR
    reqBody.fields[0]!.config.options = ['opt1', 'opt1.5', 'opt2']
    expectFetch()
  })

  test('update basic select options with invalid value', async () => {
    setBasicCharInput(EDIT_FORMAT_SELECT)
    const wrapper = await showModal()
    const input = wrapper.find(valueOptInputSel)
    // Extra newline
    await wrapper.find(valueOptInputSel).setValue('opt1\nopt2\n')
    // Danger class should be present and update button disabled
    expect(input.classes()).toContain('text-danger')
    expect(wrapper.find(updateBtnSel).attributes().disabled).toBeDefined()
  })

  test('update basic select options with single option', async () => {
    setBasicCharInput(EDIT_FORMAT_SELECT)
    const wrapper = await showModal()
    const input = wrapper.find(valueOptInputSel)
    await wrapper.find(valueOptInputSel).setValue('opt1')
    expect(input.classes()).toContain('text-danger')
    expect(wrapper.find(updateBtnSel).attributes().disabled).toBeDefined()
  })

  test('update basic field format from select to string', async () => {
    setBasicCharInput(EDIT_FORMAT_SELECT)
    params.editConfigField.options = ['opt1', 'opt2']
    const wrapper = await showModal()

    await wrapper.find(formatSelectSel).setValue(EDIT_FORMAT_STRING)
    await clickUpdate(wrapper)
    reqBody.fields[0]!.config.format = EDIT_FORMAT_STRING
    reqBody.fields[0]!.config.type = EDIT_HEADER_TYPE_CHAR
    expect(reqBody.fields[0]!.config.options).toBe(undefined)
    expectFetch()
  })

  test('update basic field format from string to select', async () => {
    setBasicCharInput(EDIT_FORMAT_STRING)
    const wrapper = await showModal()
    await wrapper.find(formatSelectSel).setValue(EDIT_FORMAT_SELECT)
    // No select options are provided, updating should be disabled
    expect(wrapper.find(valueOptInputSel).classes()).toContain('text-danger')
    expect(wrapper.find(updateBtnSel).attributes().disabled).toBeDefined()
  })

  test('update basic field format to select with options', async () => {
    setBasicCharInput(EDIT_FORMAT_STRING)
    const wrapper = await showModal()

    await wrapper.find(formatSelectSel).setValue(EDIT_FORMAT_SELECT)
    const optInput = wrapper.find(valueOptInputSel)
    await optInput.setValue('opt1\nopt2')
    expect(optInput.classes()).not.toContain('text-danger')
    await clickUpdate(wrapper)
    reqBody.fields[0]!.config.format = EDIT_FORMAT_SELECT
    delete reqBody.fields[0]!.config.regex
    reqBody.fields[0]!.config.type = EDIT_HEADER_TYPE_CHAR
    reqBody.fields[0]!.config.options = ['opt1', 'opt2']
    expectFetch()
  })

  test('render basic integer field', async () => {
    setBasicCharInput(EDIT_FORMAT_INTEGER)
    const wrapper = await showModal()
    expect(wrapper.find(bodyBasicSel).exists()).toBe(true)
    expect(wrapper.find(trSelectSel).exists()).toBe(false)
    expect(wrapper.find(trRangeSel).exists()).toBe(true)
    expect(wrapper.find(trRegexSel).exists()).toBe(true)
    expect(wrapper.find(trDefaultValSel).exists()).toBe(true)
    expect(wrapper.find(trDefaultFillSel).exists()).toBe(true)
    expect(wrapper.find(trUnitSel).exists()).toBe(false) // No unit
    expect(wrapper.find(trUnitDefaultSel).exists()).toBe(false)
    expect(wrapper.find(rangeMinInputSel).attributes().value).toBe('')
    expect(wrapper.find(rangeMaxInputSel).attributes().value).toBe('')
  })

  test('render basic double field', async () => {
    setBasicCharInput(EDIT_FORMAT_DOUBLE)
    const wrapper = await showModal()
    expect(wrapper.find(bodyBasicSel).exists()).toBe(true)
    expect(wrapper.find(trSelectSel).exists()).toBe(false)
    expect(wrapper.find(trRangeSel).exists()).toBe(true)
    expect(wrapper.find(trRegexSel).exists()).toBe(true)
    expect(wrapper.find(trDefaultValSel).exists()).toBe(true)
    expect(wrapper.find(trDefaultFillSel).exists()).toBe(true)
    expect(wrapper.find(trUnitSel).exists()).toBe(false) // No unit
    expect(wrapper.find(trUnitDefaultSel).exists()).toBe(false)
    expect(wrapper.find(rangeMinInputSel).attributes().value).toBe('')
    expect(wrapper.find(rangeMaxInputSel).attributes().value).toBe('')
  })

  test('render basic integer field with range', async () => {
    setBasicCharInput(EDIT_FORMAT_INTEGER)
    params.editConfigField.range = ['42', '170']
    const wrapper = await showModal()
    expect(wrapper.find(rangeMinInputSel).attributes().value).toBe('42')
    expect(wrapper.find(rangeMaxInputSel).attributes().value).toBe('170')
    expect(wrapper.find(rangeMaxInputSel).attributes().value).toBe('170')
    expect(wrapper.find(
      rangeMinInputSel).classes()).not.toContain('text-danger')
    expect(wrapper.find(
      rangeMaxInputSel).classes()).not.toContain('text-danger')
    expect(wrapper.find(updateBtnSel).attributes().disabled).not.toBeDefined()
  })

  test('update range with set value', async () => {
    setBasicCharInput(EDIT_FORMAT_INTEGER)
    params.editConfigField.range = ['0', '100']
    const wrapper = await showModal()

    await wrapper.find(rangeMinInputSel).setValue('42')
    await wrapper.find(rangeMaxInputSel).setValue('170')
    expect(wrapper.find(
      rangeMinInputSel).classes()).not.toContain('text-danger')
    expect(wrapper.find(
      rangeMaxInputSel).classes()).not.toContain('text-danger')
    expect(wrapper.find(updateBtnSel).attributes().disabled).not.toBeDefined()
    await clickUpdate(wrapper)

    reqBody.fields[0]!.config.format = EDIT_FORMAT_INTEGER
    reqBody.fields[0]!.config.type = EDIT_HEADER_TYPE_CHAR
    reqBody.fields[0]!.config.range = ['42', '170']
    expectFetch()
  })

  test('update range with empty value', async () => {
    setBasicCharInput(EDIT_FORMAT_INTEGER)
    params.editConfigField.range = ['0', '100']
    const wrapper = await showModal()

    await wrapper.find(rangeMinInputSel).setValue('')
    await wrapper.find(rangeMaxInputSel).setValue('')
    await clickUpdate(wrapper)

    reqBody.fields[0]!.config.format = EDIT_FORMAT_INTEGER
    reqBody.fields[0]!.config.type = EDIT_HEADER_TYPE_CHAR
    // Range should be removed
    expect(reqBody.fields[0]!.config.range).toBe(undefined)
    expectFetch()
  })

  test('update range with empty min value', async () => {
    setBasicCharInput(EDIT_FORMAT_INTEGER)
    params.editConfigField.range = ['42', '170']
    const wrapper = await showModal()
    const inputMin = wrapper.find(rangeMinInputSel)
    const inputMax = wrapper.find(rangeMaxInputSel)
    await inputMin.setValue('')
    await inputMax.setValue('170')
    // Text color should be updated and update button disabled
    expect(inputMin.classes()).toContain('text-danger')
    expect(inputMax.classes()).toContain('text-danger')
    expect(wrapper.find(updateBtnSel).attributes().disabled).toBeDefined()
  })

  test('update range with empty max value', async () => {
    setBasicCharInput(EDIT_FORMAT_INTEGER)
    params.editConfigField.range = ['42', '170']
    const wrapper = await showModal()
    const inputMin = wrapper.find(rangeMinInputSel)
    const inputMax = wrapper.find(rangeMaxInputSel)
    await inputMin.setValue('42')
    await inputMax.setValue('')
    expect(inputMin.classes()).toContain('text-danger')
    expect(inputMax.classes()).toContain('text-danger')
    expect(wrapper.find(updateBtnSel).attributes().disabled).toBeDefined()
  })

  test('update range with invalid min value', async () => {
    setBasicCharInput(EDIT_FORMAT_INTEGER)
    params.editConfigField.range = ['42', '170']
    const wrapper = await showModal()
    const inputMin = wrapper.find(rangeMinInputSel)
    const inputMax = wrapper.find(rangeMaxInputSel)
    await inputMin.setValue('xyz')
    await inputMax.setValue('170')
    expect(inputMin.classes()).toContain('text-danger')
    expect(inputMax.classes()).toContain('text-danger')
    expect(wrapper.find(updateBtnSel).attributes().disabled).toBeDefined()
  })

  test('update range with invalid max value', async () => {
    setBasicCharInput(EDIT_FORMAT_INTEGER)
    params.editConfigField.range = ['42', '170']
    const wrapper = await showModal()
    const inputMin = wrapper.find(rangeMinInputSel)
    const inputMax = wrapper.find(rangeMaxInputSel)
    await inputMin.setValue('42')
    await inputMax.setValue('xyz')
    expect(inputMin.classes()).toContain('text-danger')
    expect(inputMax.classes()).toContain('text-danger')
    expect(wrapper.find(updateBtnSel).attributes().disabled).toBeDefined()
  })

  test('update range with equal min and max values', async () => {
    setBasicCharInput(EDIT_FORMAT_INTEGER)
    params.editConfigField.range = ['42', '170']
    const wrapper = await showModal()
    const inputMin = wrapper.find(rangeMinInputSel)
    const inputMax = wrapper.find(rangeMaxInputSel)
    await inputMin.setValue('42')
    await inputMax.setValue('42')
    expect(inputMin.classes()).toContain('text-danger')
    expect(inputMax.classes()).toContain('text-danger')
    expect(wrapper.find(updateBtnSel).attributes().disabled).toBeDefined()
  })

  test('update range with greater max than min value', async () => {
    setBasicCharInput(EDIT_FORMAT_INTEGER)
    params.editConfigField.range = ['42', '170']
    const wrapper = await showModal()
    const inputMin = wrapper.find(rangeMinInputSel)
    const inputMax = wrapper.find(rangeMaxInputSel)
    await inputMin.setValue('43')
    await inputMax.setValue('42')
    expect(inputMin.classes()).toContain('text-danger')
    expect(inputMax.classes()).toContain('text-danger')
    expect(wrapper.find(updateBtnSel).attributes().disabled).toBeDefined()
  })

  test('update range with regex and valid values', async () => {
    setBasicCharInput(EDIT_FORMAT_INTEGER)
    params.editConfigField.range = ['42', '170']
    const wrapper = await showModal()
    await (wrapper.find(regexInputSel)).setValue('^3+$')
    const inputMin = wrapper.find(rangeMinInputSel)
    const inputMax = wrapper.find(rangeMaxInputSel)
    await inputMin.setValue('3')
    await inputMax.setValue('33')
    expect(inputMin.classes()).not.toContain('text-danger')
    expect(inputMax.classes()).not.toContain('text-danger')
    expect(wrapper.find(updateBtnSel).attributes().disabled).not.toBeDefined()
  })

  test('update range with regex and invalid values', async () => {
    setBasicCharInput(EDIT_FORMAT_INTEGER)
    params.editConfigField.range = ['42', '170']
    const wrapper = await showModal()
    await (wrapper.find(regexInputSel)).setValue('^3+$')
    const inputMin = wrapper.find(rangeMinInputSel)
    const inputMax = wrapper.find(rangeMaxInputSel)
    await inputMin.setValue('4') // Should not be accepted
    await inputMax.setValue('33')
    expect(inputMin.classes()).toContain('text-danger')
    expect(inputMax.classes()).toContain('text-danger')
    expect(wrapper.find(updateBtnSel).attributes().disabled).toBeDefined()
  })

  test('update range with invalid regex and valid values', async () => {
    setBasicCharInput(EDIT_FORMAT_INTEGER)
    params.editConfigField.range = ['3', '33']
    const wrapper = await showModal()
    const regexInput = wrapper.find(regexInputSel)
    await (regexInput).setValue('^+3$') // This is invalid
    expect(regexInput.classes()).toContain('text-danger')
    // Min/max should still be enabled
    expect(wrapper.find(
      rangeMinInputSel).classes()).not.toContain('text-danger')
    expect(
      wrapper.find(rangeMaxInputSel).classes()).not.toContain('text-danger')
    expect(wrapper.find(updateBtnSel).attributes().disabled).toBeDefined()
  })

  test('render basic field with regex', async () => {
    setBasicCharInput(EDIT_FORMAT_STRING)
    params.editConfigField.regex = EDIT_REGEX.dataName!.toString()
    const wrapper = await showModal()
    const input = wrapper.find(regexInputSel)
    expect(input.attributes().value).toBe(EDIT_REGEX.dataName!.toString())
    expect(input.classes()).not.toContain('text-danger')
    expect(wrapper.find(updateBtnSel).attributes().disabled).not.toBeDefined()
  })

  test('update basic field regex', async () => {
    setBasicCharInput(EDIT_FORMAT_STRING)
    const wrapper = await showModal()
    await wrapper.find(regexInputSel).setValue(EDIT_REGEX.dataName!.toString())
    await clickUpdate(wrapper)
    reqBody.fields[0]!.config.format = EDIT_FORMAT_STRING
    reqBody.fields[0]!.config.type = EDIT_HEADER_TYPE_CHAR
    reqBody.fields[0]!.config.regex = EDIT_REGEX.dataName!.toString()
    expectFetch()
  })

  test('update basic field regex with invalid value', async () => {
    setBasicCharInput(EDIT_FORMAT_STRING)
    const wrapper = await showModal()
    const input = wrapper.find(regexInputSel)
    await input.setValue('^+3$')
    expect(input.classes()).toContain('text-danger')
    expect(wrapper.find(updateBtnSel).attributes().disabled).toBeDefined()
  })

  test('update basic field default with fill=false', async () => {
    setBasicCharInput(EDIT_FORMAT_STRING)
    const wrapper = await showModal()
    await wrapper.find(defaultInputSel).setValue('default')
    await clickUpdate(wrapper)
    reqBody.fields[0]!.config.format = EDIT_FORMAT_STRING
    reqBody.fields[0]!.config.type = EDIT_HEADER_TYPE_CHAR
    reqBody.fields[0]!.config.default = 'default'
    expectFetch()
  })

  test('update basic field default with fill=true', async () => {
    const tableStore = useTableStore()
    const mockSetVal = vi.fn()
    const mockSetVal2 = vi.fn()
    const mockNodes = [
      {
        data: { 'col0': { value: '0814', uuid: TMP_UUID } },
        setDataValue: mockSetVal
      },
      {
        data: { 'col0': { value: '', uuid: TMP_UUID2 } },
        setDataValue: mockSetVal2
      },
    ]
    tableStore.gridApi.study = getMockGridApi(mockNodes)
    setBasicCharInput(EDIT_FORMAT_STRING)

    const wrapper = await showModal()
    await wrapper.find(defaultInputSel).setValue('default')
    await wrapper.find(valueFillCheckSel).setValue(true)
    expect(mockSetVal).not.toHaveBeenCalled()
    expect(mockSetVal2).not.toHaveBeenCalled()

    await clickUpdate(wrapper)
    reqBody.fields[0]!.config.format = EDIT_FORMAT_STRING
    reqBody.fields[0]!.config.type = EDIT_HEADER_TYPE_CHAR
    reqBody.fields[0]!.config.default = 'default'
    expectFetch()
    await flushPromises()
    expect(mockSetVal).not.toHaveBeenCalled() // Value was already filled
    expect(mockSetVal2).toHaveBeenCalledWith(
      'col0', { value: 'default', uuid: TMP_UUID2 })
  })

  test('update basic field default with regex and valid value', async () => {
    setBasicCharInput(EDIT_FORMAT_STRING)
    const wrapper = await showModal()
    await wrapper.find(regexInputSel).setValue('^\\D+$')
    const defaultInput = wrapper.find(defaultInputSel)
    await defaultInput.setValue('default')
    expect(defaultInput.classes()).not.toContain('text-danger')
    expect(wrapper.find(
      valueFillCheckSel).attributes().disabled).not.toBeDefined()
    expect(wrapper.find(updateBtnSel).attributes().disabled).not.toBeDefined()
  })

  test('update basic field default with regex and invalid value', async () => {
    setBasicCharInput(EDIT_FORMAT_STRING)
    const wrapper = await showModal()
    await wrapper.find(regexInputSel).setValue('^\\D+$')
    const defaultInput = wrapper.find(defaultInputSel)
    await defaultInput.setValue('default0') // Digits not allowed
    expect(defaultInput.classes()).toContain('text-danger')
    expect(wrapper.find(valueFillCheckSel).attributes().disabled).toBeDefined()
    expect(wrapper.find(updateBtnSel).attributes().disabled).toBeDefined()
  })

  test('render integer field with unit', async () => {
    setBasicCharInput(EDIT_FORMAT_INTEGER)
    params.colType = EDIT_COL_TYPE_UNIT
    const wrapper = await showModal()
    expect(wrapper.find(bodyBasicSel).exists()).toBe(true)
    expect(wrapper.find(trSelectSel).exists()).toBe(false)
    expect(wrapper.find(trRangeSel).exists()).toBe(true)
    expect(wrapper.find(trRegexSel).exists()).toBe(true)
    expect(wrapper.find(trDefaultValSel).exists()).toBe(true)
    expect(wrapper.find(trDefaultFillSel).exists()).toBe(true)
    expect(wrapper.find(trUnitSel).exists()).toBe(true) // Unit is present
    expect(wrapper.find(trUnitDefaultSel).exists()).toBe(true)
    expect(wrapper.find(unitInputSel).attributes().value).toBe('')
    const unitOptions = wrapper.findAll(unitDefaultOptSel)
    // Empty should be selected
    expect(unitOptions[0]?.text()).toBe('-')
    expect(unitOptions[0]?.attributes().selected).toBeDefined()
  })

  test('render integer field with unit and filled options', async () => {
    setBasicCharInput(EDIT_FORMAT_INTEGER)
    params.colType = EDIT_COL_TYPE_UNIT
    params.editConfigField.unit = ['unit1', 'unit2']
    const wrapper = await showModal()
    expect(wrapper.find(unitInputSel).attributes().value).toBe('unit1\nunit2')
  })

  test('update integer field unit', async () => {
    setBasicCharInput(EDIT_FORMAT_INTEGER)
    params.colType = EDIT_COL_TYPE_UNIT
    const wrapper = await showModal()
    await wrapper.find(unitInputSel).setValue('unit1\nunit2')
    await clickUpdate(wrapper)
    reqBody.fields[0]!.config.format = EDIT_FORMAT_INTEGER
    reqBody.fields[0]!.config.type = EDIT_HEADER_TYPE_CHAR
    reqBody.fields[0]!.config.unit = ['unit1', 'unit2']
    expectFetch()
  })

  test('render integer field with default unit', async () => {
    setBasicCharInput(EDIT_FORMAT_INTEGER)
    params.colType = EDIT_COL_TYPE_UNIT
    params.editConfigField.unit = ['unit1', 'unit2']
    params.editConfigField.unit_default = 'unit2'
    const wrapper = await showModal()
    expect(wrapper.find(unitInputSel).attributes().value).toBe('unit1\nunit2')
    const unitOptions = wrapper.findAll(unitDefaultOptSel)
    // Unit should be selected
    expect(unitOptions[2]?.text()).toBe('unit2')
    expect(unitOptions[2]?.attributes().selected).toBeDefined()
  })

  test('update default unit', async () => {
    setBasicCharInput(EDIT_FORMAT_INTEGER)
    params.colType = EDIT_COL_TYPE_UNIT
    params.editConfigField.unit = ['unit1', 'unit2']
    const wrapper = await showModal()
    await wrapper.find(unitDefaultInputSel).setValue('unit2')
    await clickUpdate(wrapper)
    reqBody.fields[0]!.config.format = EDIT_FORMAT_INTEGER
    reqBody.fields[0]!.config.type = EDIT_HEADER_TYPE_CHAR
    reqBody.fields[0]!.config.unit = ['unit1', 'unit2']
    reqBody.fields[0]!.config.unit_default = 'unit2'
    expectFetch()
  })

  test('update default unit to no unit', async () => {
    setBasicCharInput(EDIT_FORMAT_INTEGER)
    params.colType = EDIT_COL_TYPE_UNIT
    params.editConfigField.unit = ['unit1', 'unit2']
    params.editConfigField.unit_default = 'unit2'
    const wrapper = await showModal()
    await wrapper.find(unitDefaultInputSel).setValue('')
    await clickUpdate(wrapper)
    reqBody.fields[0]!.config.format = EDIT_FORMAT_INTEGER
    reqBody.fields[0]!.config.type = EDIT_HEADER_TYPE_CHAR
    reqBody.fields[0]!.config.unit = ['unit1', 'unit2']
    reqBody.fields[0]!.config.unit_default = ''
    expectFetch()
  })

  test('force external link field formatting', async () => {
    params.colType = EDIT_COL_TYPE_EXT_LINKS
    params.editConfigField.format = '' // No format
    params.editConfigField.type = EDIT_HEADER_TYPE_CHAR
    params.headerType = EDIT_HEADER_TYPE_CHAR
    const wrapper = await showModal()
    await clickUpdate(wrapper)
    // Format should be updated
    reqBody.fields[0]!.config.format = EDIT_FORMAT_EXT
    reqBody.fields[0]!.config.type = EDIT_HEADER_TYPE_CHAR
    expectFetch()
  })

  test('force numeric field formatting', async () => {
    params.colType = EDIT_COL_TYPE_NUMERIC
    params.editConfigField.format = ''
    params.editConfigField.type = EDIT_HEADER_TYPE_CHAR
    params.headerType = EDIT_HEADER_TYPE_CHAR
    const wrapper = await showModal()
    await clickUpdate(wrapper)
    // Format should be updated
    reqBody.fields[0]!.config.format = EDIT_FORMAT_INTEGER
    reqBody.fields[0]!.config.type = EDIT_HEADER_TYPE_CHAR
    expect(reqBody.fields[0]!.config.unit).toBe(undefined)
    expectFetch()
  })

  test('force numeric field formatting with unit', async () => {
    params.colType = EDIT_COL_TYPE_UNIT
    params.editConfigField.format = ''
    params.editConfigField.type = EDIT_HEADER_TYPE_CHAR
    params.headerType = EDIT_HEADER_TYPE_CHAR
    const wrapper = await showModal()
    await clickUpdate(wrapper)
    // Format should be updated
    reqBody.fields[0]!.config.format = EDIT_FORMAT_INTEGER
    reqBody.fields[0]!.config.type = EDIT_HEADER_TYPE_CHAR
    // Unit should still be undefined as we don't have options
    expect(reqBody.fields[0]!.config.unit).toBe(undefined)
    expectFetch()
  })

  test('force numeric field with unit and filled units', async () => {
    const tableStore = useTableStore()
    params.colType = EDIT_COL_TYPE_UNIT
    params.editConfigField.format = ''
    params.editConfigField.type = EDIT_HEADER_TYPE_CHAR
    params.headerType = EDIT_HEADER_TYPE_CHAR

    const mockNodes = [
      {
        data: { 'col0': { value: '1', unit: 'unit1', uuid: TMP_UUID } },
        setDataValue: vi.fn()
      },
      {
        data: { 'col0': { value: '2', unit: 'unit2', uuid: TMP_UUID2 } },
        setDataValue: vi.fn()
      },
    ]
    tableStore.gridApi.study = getMockGridApi(mockNodes)

    const wrapper = await showModal()
    await clickUpdate(wrapper)
    // Format should be updated
    reqBody.fields[0]!.config.format = EDIT_FORMAT_INTEGER
    reqBody.fields[0]!.config.type = EDIT_HEADER_TYPE_CHAR
    // Unit should be auto-filled
    reqBody.fields[0]!.config.unit = ['unit1', 'unit2']
    expectFetch()
  })

  test('force numeric field with unit and filled units', async () => {
    const tableStore = useTableStore()
    params.colType = EDIT_COL_TYPE_UNIT
    params.editConfigField.format = EDIT_FORMAT_INTEGER
    params.editConfigField.type = EDIT_HEADER_TYPE_CHAR
    params.headerType = EDIT_HEADER_TYPE_CHAR

    const mockNodes = [
      {
        data: { 'col0': { value: '1', uuid: TMP_UUID } },
        setDataValue: vi.fn()
      },
      {
        data: { 'col0': { value: '2.5', uuid: TMP_UUID2 } },
        setDataValue: vi.fn()
      },
    ]
    tableStore.gridApi.study = getMockGridApi(mockNodes)

    const wrapper = await showModal()
    await clickUpdate(wrapper)
    // Format should be updated
    reqBody.fields[0]!.config.format = EDIT_FORMAT_DOUBLE
    reqBody.fields[0]!.config.type = EDIT_HEADER_TYPE_CHAR
    expectFetch()
  })

  test('force date field formatting', async () => {
    params.colType = EDIT_COL_TYPE_DATE
    params.editConfigField.format = ''
    params.editConfigField.type = EDIT_HEADER_TYPE_CHAR
    params.headerType = EDIT_HEADER_TYPE_CHAR
    const wrapper = await showModal()
    await clickUpdate(wrapper)
    // Format should be updated
    reqBody.fields[0]!.config.format = EDIT_FORMAT_DATE
    reqBody.fields[0]!.config.type = EDIT_HEADER_TYPE_CHAR
    expectFetch()
  })

  test('clipboard copy string config', async () => {
    setBasicCharInput(EDIT_FORMAT_STRING)
    const wrapper = await showModal()
    await wrapper.find(copyBtnSel).trigger('click')
    const res = {
      default: '',
      editable: true,
      format: EDIT_FORMAT_STRING,
      regex: '',
    }
    expect(mockCopy).toHaveBeenCalledWith(JSON.stringify(res))
  })

  test('clipboard copy string config and default', async () => {
    setBasicCharInput(EDIT_FORMAT_STRING)
    const wrapper = await showModal()
    await wrapper.find(defaultInputSel).setValue('default')
    await wrapper.find(copyBtnSel).trigger('click')
    const res = {
      default: 'default', // Default should be added
      editable: true,
      format: EDIT_FORMAT_STRING,
      regex: '',
    }
    expect(mockCopy).toHaveBeenCalledWith(JSON.stringify(res))
  })

  test('clipboard copy string config and regex', async () => {
    setBasicCharInput(EDIT_FORMAT_STRING)
    const wrapper = await showModal()
    await wrapper.find(regexInputSel).setValue('^\\D+$')
    await wrapper.find(copyBtnSel).trigger('click')
    const res = {
      default: '',
      editable: true,
      format: EDIT_FORMAT_STRING,
      regex: '^\\D+$', // Regex should be added
    }
    expect(mockCopy).toHaveBeenCalledWith(JSON.stringify(res))
  })

  test('clipboard copy integer config', async () => {
    setBasicCharInput(EDIT_FORMAT_INTEGER)
    const wrapper = await showModal()
    await wrapper.find(copyBtnSel).trigger('click')
    const res = {
      default: '',
      editable: true,
      format: EDIT_FORMAT_INTEGER,
      regex: '',
    }
    expect(mockCopy).toHaveBeenCalledWith(JSON.stringify(res))
  })

  test('clipboard copy unit config without options', async () => {
    setBasicCharInput(EDIT_FORMAT_INTEGER)
    params.colType = EDIT_COL_TYPE_UNIT
    const wrapper = await showModal()
    await wrapper.find(copyBtnSel).trigger('click')
    const res = {
      default: '',
      editable: true,
      format: EDIT_FORMAT_INTEGER,
      regex: '',
    } // Unit should not be included
    expect(mockCopy).toHaveBeenCalledWith(JSON.stringify(res))
  })

  test('clipboard copy unit config with options', async () => {
    setBasicCharInput(EDIT_FORMAT_INTEGER)
    params.colType = EDIT_COL_TYPE_UNIT
    const wrapper = await showModal()
    await wrapper.find(unitInputSel).setValue('unit1\nunit2')
    await wrapper.find(copyBtnSel).trigger('click')
    const res = {
      default: '',
      editable: true,
      format: EDIT_FORMAT_INTEGER,
      regex: '',
      unit: ['unit1', 'unit2'] // Unit should be included
    }
    expect(mockCopy).toHaveBeenCalledWith(JSON.stringify(res))
  })

  test('clipboard copy integer config with range', async () => {
    setBasicCharInput(EDIT_FORMAT_INTEGER)
    const wrapper = await showModal()
    await wrapper.find(rangeMinInputSel).setValue('42')
    await wrapper.find(rangeMaxInputSel).setValue('170')
    await wrapper.find(copyBtnSel).trigger('click')
    const res = {
      default: '',
      editable: true,
      format: EDIT_FORMAT_INTEGER,
      regex: '',
      range: ['42', '170'],
    }
    expect(mockCopy).toHaveBeenCalledWith(JSON.stringify(res))
  })

  test('clipboard copy select config without options', async () => {
    setBasicCharInput(EDIT_FORMAT_SELECT)
    const wrapper = await showModal()
    await wrapper.find(copyBtnSel).trigger('click')
    const res = {
      default: '',
      editable: true,
      format: EDIT_FORMAT_SELECT,
      options: [],
    } // Options as empty list, no regex
    expect(mockCopy).toHaveBeenCalledWith(JSON.stringify(res))
  })

  test('clipboard copy select config with options', async () => {
    setBasicCharInput(EDIT_FORMAT_SELECT)
    const wrapper = await showModal()
    await wrapper.find(valueOptInputSel).setValue('opt1\nopt2')
    await wrapper.find(copyBtnSel).trigger('click')
    const res = {
      default: '',
      editable: true,
      format: EDIT_FORMAT_SELECT,
      options: ['opt1', 'opt2'], // Options filled
    }
    expect(mockCopy).toHaveBeenCalledWith(JSON.stringify(res))
  })

  test('clipboard copy ontology config', async () => {
    setOntologyInput()
    const wrapper = await showModal()
    await wrapper.find(copyBtnSel).trigger('click')
    const res = {
      default: '',
      editable: true,
      format: EDIT_FORMAT_ONTOLOGY,
      regex: '',
      allow_list: false, // Allow list and ontologies should be included
      ontologies: []
    }
    expect(mockCopy).toHaveBeenCalledWith(JSON.stringify(res))
  })

  test('clipboard copy ontology config with ontologies', async () => {
    setOntologyInput()
    params.editConfigField.ontologies = [OBO_ID_NCBITAXON, OBO_ID_UBERON]
    const wrapper = await showModal()
    await wrapper.find(copyBtnSel).trigger('click')
    const res = {
      default: '',
      editable: true,
      format: EDIT_FORMAT_ONTOLOGY,
      regex: '',
      allow_list: false,
      ontologies: [OBO_ID_NCBITAXON, OBO_ID_UBERON]
    }
    expect(mockCopy).toHaveBeenCalledWith(JSON.stringify(res))
  })

  test('clipboard paste string config with default and regex', async () => {
    setBasicCharInput(EDIT_FORMAT_STRING)
    const wrapper = await showModal()
    const input = {
      default: 'default',
      editable: true,
      format: EDIT_FORMAT_STRING,
      regex: '^\\D+$'
    }
    await wrapper.find(pasteInputSel).setValue(JSON.stringify(input))
    await clickUpdate(wrapper)
    reqBody.fields[0]!.config.default = 'default'
    reqBody.fields[0]!.config.regex = '^\\D+$'
    reqBody.fields[0]!.config.type = EDIT_HEADER_TYPE_CHAR
    expectFetch()
  })

  test('clipboard paste integer config', async () => {
    setBasicCharInput(EDIT_FORMAT_STRING) // Start with basic string config
    const wrapper = await showModal()
    const input = {
      default: '',
      editable: true,
      format: EDIT_FORMAT_INTEGER,
      regex: '',
    }
    await wrapper.find(pasteInputSel).setValue(JSON.stringify(input))
    await clickUpdate(wrapper)
    reqBody.fields[0]!.config.format = EDIT_FORMAT_INTEGER
    reqBody.fields[0]!.config.type = EDIT_HEADER_TYPE_CHAR
    expectFetch()
  })

  test('clipboard paste integer config', async () => {
    setBasicCharInput(EDIT_FORMAT_STRING)
    const wrapper = await showModal()
    const input = {
      default: '',
      editable: true,
      format: EDIT_FORMAT_INTEGER,
      range: ['42', '170'],
      regex: '',
    }
    await wrapper.find(pasteInputSel).setValue(JSON.stringify(input))
    await clickUpdate(wrapper)
    reqBody.fields[0]!.config.format = EDIT_FORMAT_INTEGER
    reqBody.fields[0]!.config.range = ['42', '170'] // Range should be added
    reqBody.fields[0]!.config.type = EDIT_HEADER_TYPE_CHAR
    expectFetch()
  })

  test('clipboard paste select config', async () => {
    setBasicCharInput(EDIT_FORMAT_STRING)
    const wrapper = await showModal()
    const input = {
      default: '',
      editable: true,
      format: EDIT_FORMAT_SELECT,
      options: ['opt1', 'opt2'],
    }
    await wrapper.find(pasteInputSel).setValue(JSON.stringify(input))
    await clickUpdate(wrapper)
    reqBody.fields[0]!.config.format = EDIT_FORMAT_SELECT
    reqBody.fields[0]!.config.options = ['opt1', 'opt2'] // Should be added
    delete reqBody.fields[0]!.config.regex
    reqBody.fields[0]!.config.type = EDIT_HEADER_TYPE_CHAR
    expectFetch()
  })

  test('clipboard paste removing range', async () => {
    setBasicCharInput(EDIT_FORMAT_INTEGER)
    params.editConfigField.range = ['42', '170']
    const wrapper = await showModal()
    const input = {
      default: '',
      editable: true,
      format: EDIT_FORMAT_STRING,
      regex: ''
    }
    await wrapper.find(pasteInputSel).setValue(JSON.stringify(input))
    await clickUpdate(wrapper)
    expect(reqBody.fields[0]!.config.range).toBe(undefined)
    reqBody.fields[0]!.config.type = EDIT_HEADER_TYPE_CHAR
    expectFetch()
  })

  test('clipboard paste removing select options', async () => {
    setBasicCharInput(EDIT_FORMAT_SELECT)
    params.editConfigField.options = ['opt1', 'opt2']
    const wrapper = await showModal()
    const input = {
      default: '',
      editable: true,
      format: EDIT_FORMAT_STRING,
      regex: ''
    }
    await wrapper.find(pasteInputSel).setValue(JSON.stringify(input))
    await clickUpdate(wrapper)
    expect(reqBody.fields[0]!.config.options).toBe(undefined)
    reqBody.fields[0]!.config.type = EDIT_HEADER_TYPE_CHAR
    expectFetch()
  })

  test('clipboard paste unit config', async () => {
    setBasicCharInput(EDIT_FORMAT_INTEGER)
    params.colType = EDIT_COL_TYPE_UNIT
    const wrapper = await showModal()
    const input = {
      default: '',
      editable: true,
      format: EDIT_FORMAT_INTEGER,
      regex: '',
      unit: ['unit1', 'unit2'],
      unit_default: 'unit1'
    }
    await wrapper.find(pasteInputSel).setValue(JSON.stringify(input))
    await clickUpdate(wrapper)
    expect(reqBody.fields[0]!.config.options).toBe(undefined)
    reqBody.fields[0]!.config.format = EDIT_FORMAT_INTEGER
    reqBody.fields[0]!.config.type = EDIT_HEADER_TYPE_CHAR
    reqBody.fields[0]!.config.unit = ['unit1', 'unit2']
    reqBody.fields[0]!.config.unit_default = 'unit1'
    expectFetch()
  })

  test('clipboard paste ontology config', async () => {
    setOntologyInput()
    const wrapper = await showModal()
    const input = {
      allow_list: true,
      default: [ontologyTerm],
      editable: true,
      format: EDIT_FORMAT_ONTOLOGY,
      ontologies: [OBO_ID_NCBITAXON, OBO_ID_UBERON],
      regex: '',
    }
    await wrapper.find(pasteInputSel).setValue(JSON.stringify(input))
    await clickUpdate(wrapper)
    expect(reqBody.fields[0]!.config.options).toBe(undefined)
    reqBody.fields[0]!.config.allow_list = true
    reqBody.fields[0]!.config.default = [ontologyTerm] as SheetTableCellDataValue
    reqBody.fields[0]!.config.format = EDIT_FORMAT_ONTOLOGY
    reqBody.fields[0]!.config.type = EDIT_HEADER_TYPE_CHAR
    reqBody.fields[0]!.config.ontologies = [OBO_ID_NCBITAXON, OBO_ID_UBERON]
    expectFetch()
  })

  // TODO: Figure out how to assert checkbox states
  // TODO: Support/test other contact types than performer?
})
