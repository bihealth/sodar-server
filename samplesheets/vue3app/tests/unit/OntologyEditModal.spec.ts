import { nextTick } from 'vue'
import { beforeEach, describe, expect, test, vi } from 'vitest'
import { config, mount, type VueWrapper } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { createBootstrap } from 'bootstrap-vue-next/plugins/createBootstrap'
import { type Column, type GridApi } from 'ag-grid-community'

import OntologyEditModal from '@/components/modals/OntologyEditModal.vue'
import { useAppStore } from '@/stores/appStore.ts'
import { useEditStore } from '@/stores/editStore.ts'
import { useTableStore } from '@/stores/tableStore.ts'
import {
  type EditOntologyRef,
  type GenericResponseBody,
  type GridCellEditorParams,
  type OntologyTermResponseBody,
  type OntologyTermResponseRef,
  type SheetTableFieldHeader,
  type StudyEditContext,
} from '@/types.ts'

import studyTablesEdit from '../data/studyTablesEdit.json'
import { copy, waitMs, waitSelector } from '../testUtils.ts'
import {
  ASSAY_UUID,
  OBO_ID_NCBITAXON,
  OBO_ID_UBERON,
  OBO_ID_UNKNOWN,
  PROJECT_UUID,
  STUDY_UUID,
  TMP_UUID
} from '../testConstants.ts'

// Test Data -------------------------------------------------------------------

const inputTerm: EditOntologyRef = {
  name: 'Homo sapiens',
  accession: 'https://purl.bioontology.org/ontology/NCBITAXON/9606',
  ontology_name: 'NCBITAXON'
}
const inputTerm2: EditOntologyRef = {
  name: 'Homo sapiens neanderthalensis',
  accession: 'https://purl.obolibrary.org/obo/NCBITaxon_63221',
  ontology_name: 'NCBITAXON'
}
const inputTerm3: EditOntologyRef = {
  name: 'Ursus thibetanus',
  accession: 'https://purl.obolibrary.org/obo/NCBITaxon_9642',
  ontology_name: 'NCBITAXON'
}
const defaultParams = {
  assayMode: false,
  colAlign: 'left',
  colWidth: 125,
  editConfigField: {
    name: 'organism',
    type: 'characteristics',
    format: 'ontology',
    allow_list: false,
    ontologies: []
  },
  fieldHeader: copy(
    studyTablesEdit.tables.study.field_header[1] as SheetTableFieldHeader) as
    SheetTableFieldHeader,
  fieldId: 'col1',
  sampleColId: 'col7',
  tableUuid: STUDY_UUID,
  value: {
    value: [inputTerm],
    uuid: TMP_UUID
  },
}
let params: GridCellEditorParams

const defaultFetchRes: GenericResponseBody = { detail: 'ok' }
let fetchRes: GenericResponseBody | OntologyTermResponseBody = defaultFetchRes
let fetchStatus: number = 200

const queryTerm: OntologyTermResponseRef = {
  name: 'Test term',
  accession: 'https://purl.bioontology.org/ontology/NCBITAXON/1337',
  ontology_name: 'NCBITAXON',
  is_obsolete: false,
  term_id: 'NCBITaxon:1337'
}
const queryTerm2: OntologyTermResponseRef = {
  name: 'Test term 2',
  accession: 'https://purl.bioontology.org/ontology/NCBITAXON/1338',
  ontology_name: 'NCBITAXON',
  is_obsolete: false,
  term_id: 'NCBITaxon:1338'
}

// Mocks
const mockGridApi = {
  forEachNode: vi.fn(),
  refreshCells: vi.fn()
}

// Misc
const cellUpdateUrl: string = '/samplesheets/ajax/edit/cell/' + PROJECT_UUID
const queryUrlPrefix: string = '/ontology/ajax/obo/term/query'
const queryBody = {
  credentials: 'same-origin',
  headers: { 'Accept': 'application/json', 'Content-Type': 'application/json' },
  method: 'GET',
}
const queryDetail: string = 'Test detail'
const queryDetailType: string = 'info'

// Selector shortcuts
const clipCopySel = '#sodar-ss-ontology-btn-clip-copy'
const clipPasteSel = '#sodar-ss-ontology-input-clip-paste'
const searchInputSel = '#sodar-ss-ontology-input-search'
const searchLimitSel = '#sodar-ss-ontology-select-limit'
const searchOrderSel = '#sodar-ss-ontology-order-check'
const searchTermSel = '#sodar-ss-ontology-select-term'
const searchOptSel = '.sodar-ss-ontology-select-term-option'
const insertRowSel = '#sodar-ss-ontology-insert-row'
const termRowSel = '.sodar-ss-ontology-term-item'
const displayCellSel = '.sodar-ss-ontology-term-display'
const editCellSel = '.sodar-ss-ontology-term-edit'
const termNameSel = '.sodar-ss-ontology-term-name'
const termOboSel = '.sodar-ss-ontology-term-obo'
const termAccSel = '.sodar-ss-ontology-term-acc'
const termInputSel = '.sodar-ss-ontology-row-input'
const alertDetailSel = '#sodar-ss-ontology-alert-res-detail'
const alertNoImportSel = '#sodar-ss-ontology-alert-no-imports'
const alertNoListSel = '#sodar-ss-ontology-alert-no-list'
const iconObsoleteSel = '.sodar-ss-ontology-icon-obsolete'
const iconUnknownSel = '.sodar-ss-ontology-icon-unknown'
const iconOboEmptySel = '.sodar-ss-ontology-icon-obo-empty'
const iconOboNotFoundSel = '.sodar-ss-ontology-icon-obo-not-found'
const moveBtnSel = '.sodar-ss-ontology-btn-move'
const upBtnSel = '.sodar-ss-ontology-btn-move-up'
const downBtnSel = '.sodar-ss-ontology-btn-move-down'
const editBtnSel = '.sodar-ss-ontology-btn-edit'
const stopBtnSel = '.sodar-ss-ontology-btn-stop'
const delBtnSel = '.sodar-ss-ontology-btn-delete'
const insertBtnSel = '#sodar-ss-ontology-btn-insert'
const updateBtnSel = '#sodar-ss-ontology-btn-update'
const rowInputSel = '.sodar-ss-ontology-row-input'

// Global Setup ----------------------------------------------------------------

config.global.plugins = [createBootstrap()]

// Mock clipboard
const mockCopy = vi.fn()
vi.mock('@vueuse/core', async () => {
  const actual = await vi.importActual('@vueuse/core')
  return { ...actual, useClipboard: () => ({ copy: mockCopy }) }
})

// Replace useToast with mock
// TODO: Remove once the component is updated to use NotifyCb
vi.mock('bootstrap-vue-next', async () => {
  const actual = await vi.importActual('bootstrap-vue-next')
  return { ...actual, useToast: () => ({ create: vi.fn(), show: vi.fn() }) }
})

// Tests -----------------------------------------------------------------------

describe('OntologyEditModal.vue', () => {
  beforeEach(() => {
    // Update mocks
    vi.resetAllMocks()
    // Override fetchRes and/or fetchStatus before showModal() to test responses
    fetchRes = copy(defaultFetchRes)
    fetchStatus = 200

    // Set up stores
    setActivePinia(createPinia())
    const appStore = useAppStore()
    appStore.projectUuid = PROJECT_UUID
    const tableStore = useTableStore()
    tableStore.gridApi.study = mockGridApi as unknown as GridApi
    tableStore.gridApi.assays[ASSAY_UUID] = mockGridApi as unknown as GridApi
    const editStore = useEditStore()
    editStore.editContext = studyTablesEdit.edit_context as
      unknown as StudyEditContext

    // Set up params
    params = copy(defaultParams) as GridCellEditorParams
    params.api = {
      getColumns: () => { return [] },
      stopEditing: vi.fn()
    } as unknown as GridApi
    params.column = {
      getOriginalParent: vi.fn()
    } as unknown as Column
  })

  async function showModal (): Promise<VueWrapper> {
    global.fetch = vi.fn(() => Promise.resolve({
      json: () => Promise.resolve(fetchRes), status: fetchStatus} as Response)
    )
    const wrapper = mount(OntologyEditModal)
    wrapper.vm.show(params)
    await nextTick() // Must wait for all reactive vals to update
    await waitSelector(wrapper, '#sodar-ss-ontology-edit-content', 1)
    return wrapper
  }

  test('render component with default data', async () => {
    const wrapper = await showModal()
    expect(wrapper.find('#sodar-ss-ontology-edit-content').exists()).toBe(true)
    expect(wrapper.find('.modal-close').exists()).toBe(false)
    expect(wrapper.find('.modal-title').text()).toBe('Organism')
    expect(wrapper.find(updateBtnSel).attributes().disabled).toBeDefined()
  })

  test('render term search ui with default data', async () => {
    const wrapper = await showModal()
    expect(wrapper.find(searchInputSel).exists()).toBe(true)
    expect(wrapper.find(searchInputSel).attributes().disabled).not.toBeDefined()
    expect(wrapper.find(searchLimitSel).exists()).toBe(true)
    expect(wrapper.find(searchLimitSel).attributes().disabled).not.toBeDefined()
    const options = wrapper.find(searchLimitSel).findAll('option')
    expect(options.length).toBe(
      Object.values(studyTablesEdit.edit_context.sodar_ontologies).length + 1)
    expect(options[0]?.attributes().selected).toBeDefined()
    expect(wrapper.find(searchOrderSel).exists()).toBe(true)
    expect(wrapper.find(searchOrderSel).attributes().disabled).not.toBeDefined()
    expect(wrapper.find(searchTermSel).exists()).toBe(true)
    expect(wrapper.find(searchTermSel).attributes().disabled).not.toBeDefined()
  })

  test('render alerts with default data', async () => {
    const wrapper = await showModal()
    // No insert alert should be visible
    expect(wrapper.find(alertDetailSel).exists()).toBe(false)
    expect(wrapper.find(alertNoListSel).exists()).toBe(true)
  })

  test('render alerts with allow_list=false and no terms', async () => {
    params.value.value = []
    const wrapper = await showModal()
    // No alerts should be visible
    expect(wrapper.find(alertDetailSel).exists()).toBe(false)
    expect(wrapper.find(alertNoListSel).exists()).toBe(false)
  })

  test('render alerts with allow_list=true', async () => {
    params.editConfigField.allow_list = true
    const wrapper = await showModal()
    // No alerts should be visible
    expect(wrapper.find(alertDetailSel).exists()).toBe(false)
    expect(wrapper.find(alertNoListSel).exists()).toBe(false)
  })

  test('render term row with default data', async () => {
    const wrapper = await showModal()
    // Assert term row content
    const terms = wrapper.findAll(termRowSel)
    expect(terms.length).toBe(1)
    const termCols = terms[0]?.findAll('td')
    expect(termCols![0]!.text()).toBe(params.value.value[0].name)
    expect(termCols![0]!.classes()).not.toContain('text-danger')
    expect(termCols![1]!.text()).toBe(params.value.value[0].ontology_name)
    expect(termCols![1]!.classes()).not.toContain('text-danger')
    expect(termCols![2]!.find('a').text()).toBe(params.value.value[0].accession)
    // Assert term row button status
    expect(wrapper.find(moveBtnSel).exists()).toBe(false)
    expect(wrapper.find(editBtnSel).exists()).toBe(true)
    expect(wrapper.find(editBtnSel).attributes().disabled).not.toBeDefined()
    expect(wrapper.find(stopBtnSel).exists()).toBe(false)
    expect(wrapper.find(delBtnSel).exists()).toBe(true)
    expect(wrapper.find(delBtnSel).attributes().disabled).not.toBeDefined()
    // Assert insert row
    expect(wrapper.find(insertRowSel).exists()).toBe(false)
    // Assert no icons displayed
    expect(wrapper.find(iconObsoleteSel).exists()).toBe(false)
    expect(wrapper.find(iconUnknownSel).exists()).toBe(false)
  })

  test('render term row with obsolete term', async () => {
    params.value.value[0].obsolete = true
    const wrapper = await showModal()
    // Obsolete icon should be displayed
    expect(wrapper.find(iconObsoleteSel).exists()).toBe(true)
    expect(wrapper.find(iconUnknownSel).exists()).toBe(false)
    expect(wrapper.find(iconOboEmptySel).exists()).toBe(false)
    expect(wrapper.find(iconOboNotFoundSel).exists()).toBe(false)
    expect(wrapper.find(termNameSel).classes()).toContain('text-danger')
    expect(wrapper.find(termOboSel).classes()).not.toContain('text-danger')
  })

  test('render term row with unknown term', async () => {
    params.value.value[0].unknown = true
    const wrapper = await showModal()
    // Unknown icon should be displayed
    expect(wrapper.find(iconObsoleteSel).exists()).toBe(false)
    expect(wrapper.find(iconUnknownSel).exists()).toBe(true)
    expect(wrapper.find(iconOboEmptySel).exists()).toBe(false)
    expect(wrapper.find(iconOboNotFoundSel).exists()).toBe(false)
    expect(wrapper.find(termNameSel).classes()).toContain('text-danger')
    expect(wrapper.find(termOboSel).classes()).not.toContain('text-danger')
  })

  test('render term row with empty ontology name', async () => {
    params.value.value[0].ontology_name = ''
    const wrapper = await showModal()
    // Empty ontology name icon should be displayed
    expect(wrapper.find(iconObsoleteSel).exists()).toBe(false)
    expect(wrapper.find(iconUnknownSel).exists()).toBe(false)
    expect(wrapper.find(iconOboEmptySel).exists()).toBe(true)
    expect(wrapper.find(iconOboNotFoundSel).exists()).toBe(false)
    expect(wrapper.find(termNameSel).classes()).not.toContain('text-danger')
    expect(wrapper.find(termOboSel).classes()).toContain('text-danger')
  })

  test('render term row with unknown ontology name', async () => {
    params.value.value[0].ontology_name = OBO_ID_UNKNOWN
    const wrapper = await showModal()
    // Ontology name not found icon should be displayed
    expect(wrapper.find(iconObsoleteSel).exists()).toBe(false)
    expect(wrapper.find(iconUnknownSel).exists()).toBe(false)
    expect(wrapper.find(iconOboEmptySel).exists()).toBe(false)
    expect(wrapper.find(iconOboNotFoundSel).exists()).toBe(true)
    expect(wrapper.find(termNameSel).classes()).not.toContain('text-danger')
    expect(wrapper.find(termOboSel).classes()).toContain('text-danger')
  })

  test('render insert row with empty value', async () => {
    params.value.value = []
    const wrapper = await showModal()
    expect(wrapper.findAll(termRowSel).length).toBe(0)
    expect(wrapper.find(insertRowSel).exists()).toBe(true)
  })

  test('render insert row with allow_list=true', async () => {
    params.editConfigField.allow_list = true
    const wrapper = await showModal()
    expect(wrapper.findAll(termRowSel).length).toBe(1)
    expect(wrapper.find(insertRowSel).exists()).toBe(true)
  })

  test('render move buttons with allow_list and single term', async () => {
    params.editConfigField.allow_list = true
    const wrapper = await showModal()
    // Buttons should be visible but disabled
    const buttons = wrapper.findAll(moveBtnSel)
    expect(buttons.length).toBe(2)
    for (let i = 0; i < buttons.length; i++) {
      expect(buttons[i]?.attributes().disabled).toBeDefined()
    }
  })

  test('render move buttons with allow_list and multiple terms', async () => {
    params.editConfigField.allow_list = true
    // NOTE: Not a realistic example, but the modal doesn't know that :)
    params.value.value.push(inputTerm2, inputTerm3)
    const wrapper = await showModal()
    expect(wrapper.findAll(moveBtnSel).length).toBe(6)
    const terms = wrapper.findAll(termRowSel)
    expect(terms.length).toBe(3)
    // Up should be disabled for topmost term, down for bottommost term
    expect(terms[0]?.find(upBtnSel).attributes().disabled).toBeDefined()
    expect(terms[0]?.find(downBtnSel).attributes().disabled).not.toBeDefined()
    expect(terms[1]?.find(upBtnSel).attributes().disabled).not.toBeDefined()
    expect(terms[1]?.find(downBtnSel).attributes().disabled).not.toBeDefined()
    expect(terms[2]?.find(upBtnSel).attributes().disabled).not.toBeDefined()
    expect(terms[2]?.find(downBtnSel).attributes().disabled).toBeDefined()
  })

  test('move term down in list', async () => {
    params.editConfigField.allow_list = true
    params.value.value.push(inputTerm2, inputTerm3)
    const wrapper = await showModal()
    const terms = wrapper.findAll(termRowSel)

    // Assert initial order
    expect(terms[0]?.find(termNameSel).text()).toBe(inputTerm.name)
    expect(terms[1]?.find(termNameSel).text()).toBe(inputTerm2.name)
    expect(terms[2]?.find(termNameSel).text()).toBe(inputTerm3.name)
    expect(wrapper.find(updateBtnSel).attributes().disabled).toBeDefined()

    // Click on down button and assert resulting order
    // First alt term should now be in the bottom
    await terms[1]?.find(downBtnSel).trigger('click')
    expect(terms[0]?.find(termNameSel).text()).toBe(inputTerm.name)
    expect(terms[1]?.find(termNameSel).text()).toBe(inputTerm3.name)
    expect(terms[2]?.find(termNameSel).text()).toBe(inputTerm2.name)
    expect(wrapper.find(updateBtnSel).attributes().disabled).not.toBeDefined()
  })

  test('move term up in list', async () => {
    params.editConfigField.allow_list = true
    params.value.value.push(inputTerm2, inputTerm3)
    const wrapper = await showModal()
    const terms = wrapper.findAll(termRowSel)
    expect(terms[0]?.find(termNameSel).text()).toBe(inputTerm.name)
    expect(terms[1]?.find(termNameSel).text()).toBe(inputTerm2.name)
    expect(terms[2]?.find(termNameSel).text()).toBe(inputTerm3.name)
    expect(wrapper.find(updateBtnSel).attributes().disabled).toBeDefined()
    await terms[1]?.find(upBtnSel).trigger('click')
    expect(terms[0]?.find(termNameSel).text()).toBe(inputTerm2.name)
    expect(terms[1]?.find(termNameSel).text()).toBe(inputTerm.name)
    expect(terms[2]?.find(termNameSel).text()).toBe(inputTerm3.name)
    expect(wrapper.find(updateBtnSel).attributes().disabled).not.toBeDefined()
  })

  test('delete term with allow_list=false', async () => {
    const wrapper = await showModal()
    expect(wrapper.findAll(termRowSel).length).toBe(1)
    expect(wrapper.find(insertRowSel).exists()).toBe(false)
    expect(wrapper.find(updateBtnSel).attributes().disabled).toBeDefined()
    await wrapper.find(delBtnSel).trigger('click')
    expect(wrapper.findAll(termRowSel).length).toBe(0)
    expect(wrapper.find(insertRowSel).exists()).toBe(true)
    expect(wrapper.find(updateBtnSel).attributes().disabled).not.toBeDefined()
  })

  test('delete term with allow_list=true', async () => {
    params.editConfigField.allow_list = true
    const wrapper = await showModal()
    expect(wrapper.findAll(termRowSel).length).toBe(1)
    expect(wrapper.find(insertRowSel).exists()).toBe(true)
    expect(wrapper.find(updateBtnSel).attributes().disabled).toBeDefined()
    await wrapper.find(delBtnSel).trigger('click')
    expect(wrapper.findAll(termRowSel).length).toBe(0)
    expect(wrapper.find(insertRowSel).exists()).toBe(true)
    expect(wrapper.find(updateBtnSel).attributes().disabled).not.toBeDefined()
  })

  test('delete term with multiple values', async () => {
    params.editConfigField.allow_list = true
    params.value.value.push(inputTerm2, inputTerm3)

    const wrapper = await showModal()
    let terms = wrapper.findAll(termRowSel)
    expect(terms.length).toBe(3)
    expect(terms[0]?.find(termNameSel).text()).toBe(inputTerm.name)
    expect(terms[1]?.find(termNameSel).text()).toBe(inputTerm2.name)
    expect(terms[2]?.find(termNameSel).text()).toBe(inputTerm3.name)
    expect(wrapper.find(updateBtnSel).attributes().disabled).toBeDefined()

    await terms[1]?.find(delBtnSel).trigger('click')
    terms = wrapper.findAll(termRowSel)
    expect(terms.length).toBe(2)
    expect(terms[0]?.find(termNameSel).text()).toBe(inputTerm.name)
    expect(terms[1]?.find(termNameSel).text()).toBe(inputTerm3.name)
    expect(wrapper.find(updateBtnSel).attributes().disabled).not.toBeDefined()
  })

  test('update value after term move', async () => {
    params.editConfigField.allow_list = true
    params.value.value.push(inputTerm2, inputTerm3)

    const wrapper = await showModal()
    const terms = wrapper.findAll(termRowSel)
    const updateBtn = wrapper.find(updateBtnSel)
    expect(updateBtn.attributes().disabled).toBeDefined()
    expect(fetch).not.toHaveBeenCalled()

    await terms[1]?.find(downBtnSel).trigger('click')
    expect(updateBtn.attributes().disabled).not.toBeDefined()
    await updateBtn.trigger('click')
    const reqBody = {
      updated_cells: [{
        header_name: 'organism',
        header_type: 'characteristics',
        obj_cls: 'GenericMaterial',
        uuid: TMP_UUID,
        value: [inputTerm, inputTerm3, inputTerm2], // Updated order
      }],
      verify: true
    }
    expect(fetch).toHaveBeenCalledWith(
      cellUpdateUrl,
      expect.objectContaining({ body: JSON.stringify(reqBody) }))
  })

  test('update value after term delete', async () => {
    params.editConfigField.allow_list = true
    params.value.value.push(inputTerm2, inputTerm3)

    const wrapper = await showModal()
    const terms = wrapper.findAll(termRowSel)
    const updateBtn = wrapper.find(updateBtnSel)
    expect(updateBtn.attributes().disabled).toBeDefined()

    await terms[1]?.find(delBtnSel).trigger('click')
    expect(updateBtn.attributes().disabled).not.toBeDefined()
    await updateBtn.trigger('click')
    const reqBody = {
      updated_cells: [{
        header_name: 'organism',
        header_type: 'characteristics',
        obj_cls: 'GenericMaterial',
        uuid: TMP_UUID,
        value: [inputTerm, inputTerm3], // Second term missing
      }],
      verify: true
    }
    expect(fetch).toHaveBeenCalledWith(
      cellUpdateUrl,
      expect.objectContaining({ body: JSON.stringify(reqBody) }))
  })

  test('render ontology dropdown with single editConfig item', async () => {
    params.editConfigField.ontologies = [OBO_ID_NCBITAXON]
    const wrapper = await showModal()
    const select = wrapper.find(searchLimitSel)
    // Only one allowed ontology = dropdown should be disabled
    expect(select.attributes().disabled).toBeDefined()
    const options = select.findAll('option')
    expect(options.length).toBe(1)
    expect(options[0]?.text()).toBe(OBO_ID_NCBITAXON)
    expect(options[0]?.attributes().value).toBe(OBO_ID_NCBITAXON)
    // Ordering checkbox should be disabled
    expect(wrapper.find(searchOrderSel).attributes().disabled).toBeDefined()
  })

  test('render ontology dropdown with multiple editConfig items', async () => {
    params.editConfigField.ontologies = [OBO_ID_NCBITAXON, OBO_ID_UBERON]
    const wrapper = await showModal()
    const select = wrapper.find(searchLimitSel)
    // Multiple allowed ontologies = dropdown should be enabled
    expect(select.attributes().disabled).not.toBeDefined()
    const options = select.findAll('option')
    expect(options.length).toBe(3)
    expect(options[0]?.attributes().selected).toBeDefined()
    expect(options[1]?.attributes().value).toBe(OBO_ID_NCBITAXON)
    expect(options[1]?.attributes().selected).not.toBeDefined()
    expect(options[2]?.attributes().value).toBe(OBO_ID_UBERON)
    expect(options[2]?.attributes().selected).not.toBeDefined()
    // Ordering is allowed
    expect(wrapper.find(searchOrderSel).attributes().disabled).not.toBeDefined()
  })

  test('hide dropdown with single unknown editConfig item', async () => {
    params.editConfigField.ontologies = [OBO_ID_UNKNOWN]
    const wrapper = await showModal()
    expect(wrapper.find(searchLimitSel).exists()).toBe(false)
    expect(wrapper.find(alertNoImportSel).exists()).toBe(true) // Alert visible
  })

  test('render dropdown with single known editConfig item', async () => {
    params.editConfigField.ontologies = [OBO_ID_NCBITAXON, OBO_ID_UNKNOWN]
    const wrapper = await showModal()
    const select = wrapper.find(searchLimitSel)
    expect(select.attributes().disabled).toBeDefined()
    const options = select.findAll('option')
    expect(options.length).toBe(1)
    expect(options[0]?.attributes().value).toBe(OBO_ID_NCBITAXON)
    expect(wrapper.find(searchOrderSel).attributes().disabled).toBeDefined()
    // Alert should not be present
    expect(wrapper.find(alertNoImportSel).exists()).toBe(false)
  })

  test('render dropdown with known and unknown editConfig item', async () => {
    params.editConfigField.ontologies = [
      OBO_ID_NCBITAXON, OBO_ID_UBERON, OBO_ID_UNKNOWN
    ]
    const wrapper = await showModal()
    const select = wrapper.find(searchLimitSel)
    expect(select.attributes().disabled).not.toBeDefined()
    const options = select.findAll('option')
    expect(options.length).toBe(3)
    expect(options[1]?.attributes().value).toBe(OBO_ID_NCBITAXON)
    expect(options[2]?.attributes().value).toBe(OBO_ID_UBERON)
    expect(wrapper.find(searchOrderSel).attributes().disabled).not.toBeDefined()
  })

  test('query for terms without ontology limit', async () => {
    fetchRes = { terms: [] }
    const wrapper = await showModal()
    expect(fetch).not.toHaveBeenCalled()
    await wrapper.find(searchInputSel).setValue('test')
    await waitMs(500) // TODO: Better way to wait for delayed fetch() call?
    expect(fetch).toHaveBeenCalledWith(`${queryUrlPrefix}?s=test`, queryBody)
  })

  test('query for terms with single ontology limit', async () => {
    params.editConfigField.ontologies = [OBO_ID_NCBITAXON]
    fetchRes = { terms: [] }
    const wrapper = await showModal()
    await wrapper.find(searchInputSel).setValue('test')
    await waitMs(500)
    expect(fetch).toHaveBeenCalledWith(
      `${queryUrlPrefix}?s=test&o=${OBO_ID_NCBITAXON}`, queryBody)
  })

  test('query with multi-ontology limit without chosen option', async () => {
    params.editConfigField.ontologies = [OBO_ID_NCBITAXON, OBO_ID_UBERON]
    fetchRes = { terms: [] }
    const wrapper = await showModal()
    await wrapper.find(searchInputSel).setValue('test')
    await waitMs(500)
    expect(fetch).toHaveBeenCalledWith(
      `${queryUrlPrefix}?s=test&o=${OBO_ID_NCBITAXON}&o=${OBO_ID_UBERON}`,
      queryBody)
  })

  test('query with multi-ontology limit with chosen option', async () => {
    params.editConfigField.ontologies = [OBO_ID_NCBITAXON, OBO_ID_UBERON]
    fetchRes = { terms: [] }
    const wrapper = await showModal()
    await wrapper.find(searchLimitSel).setValue(OBO_ID_UBERON)
    await wrapper.find(searchInputSel).setValue('test')
    await waitMs(500)
    expect(fetch).toHaveBeenCalledWith(
      `${queryUrlPrefix}?s=test&o=${OBO_ID_UBERON}`, queryBody)
  })

  test('query with ordering and no ontology limit', async () => {
    fetchRes = { terms: [] }
    const wrapper = await showModal()
    await wrapper.find(searchOrderSel).setValue(true)
    await wrapper.find(searchInputSel).setValue('test')
    await waitMs(500)
    expect(fetch).toHaveBeenCalledWith(
      `${queryUrlPrefix}?s=test&order=1`, queryBody)
  })

  test('input query term with fewer than minimum characters', async () => {
    fetchRes = { terms: [] }
    const wrapper = await showModal()
    expect(fetch).not.toHaveBeenCalled()
    await wrapper.find(searchInputSel).setValue('te') // Minimum is 3
    await waitMs(500)
    expect(fetch).not.toHaveBeenCalled() // No call
  })

  test('update term select with query results', async () => {
    fetchRes = { terms: [queryTerm, queryTerm2] }

    const wrapper = await showModal()
    let terms = wrapper.findAll(searchOptSel)
    expect(terms.length).toBe(0)

    await wrapper.find(searchInputSel).setValue('test')
    await waitMs(500)
    expect(fetch).toHaveBeenCalled()

    terms = wrapper.findAll(searchOptSel)
    expect(terms.length).toBe(2)
    expect(terms[0]?.text()).toBe(`[${queryTerm.term_id}] ${queryTerm.name}`)
    expect(terms[1]?.text()).toBe(`[${queryTerm2.term_id}] ${queryTerm2.name}`)
    expect(wrapper.find(alertDetailSel).exists()).toBe(false)
    expect(wrapper.find(alertNoImportSel).exists()).toBe(false)
  })

  test('update term select with obsolete term in results', async () => {
    const qt2 = copy(queryTerm2) as OntologyTermResponseRef
    qt2.is_obsolete = true
    fetchRes = { terms: [queryTerm, qt2] }

    const wrapper = await showModal()
    await wrapper.find(searchInputSel).setValue('test')
    await waitMs(500)
    expect(fetch).toHaveBeenCalled()

    const terms = wrapper.findAll(searchOptSel)
    expect(terms.length).toBe(2)
    expect(terms[0]?.text()).toBe(`[${queryTerm.term_id}] ${queryTerm.name}`)
    expect(terms[1]?.text()).toBe(
      `[${queryTerm2.term_id}] ${queryTerm2.name} <OBSOLETE>`)
  })

  test('display response detail alert', async () => {
    fetchRes = { terms: [], detail: queryDetail, detail_type: queryDetailType }
    const wrapper = await showModal()
    expect(wrapper.find(alertDetailSel).exists()).toBe(false)

    await wrapper.find(searchInputSel).setValue('test')
    await waitMs(500)
    expect(fetch).toHaveBeenCalled()

    const detail = wrapper.find(alertDetailSel)
    expect(detail.text()).toBe(queryDetail)
    expect(detail.classes()).toContain('alert-info')
  })

  test('display response detail alert with default type', async () => {
    fetchRes = { terms: [], detail: queryDetail }
    const wrapper = await showModal()

    await wrapper.find(searchInputSel).setValue('test')
    await waitMs(500)
    expect(fetch).toHaveBeenCalled()

    const detail = wrapper.find(alertDetailSel)
    expect(detail.text()).toBe(queryDetail)
    expect(detail.classes()).toContain('alert-danger')
  })

  test('select term with default settings', async () => {
    fetchRes = { terms: [queryTerm, queryTerm2] }

    const wrapper = await showModal()
    let valTerms = wrapper.findAll(termRowSel)
    expect(valTerms.length).toBe(1)
    expect(valTerms[0]?.findAll('td')[0]?.text()).toBe(inputTerm.name)
    // Just to ensure the names differ
    expect(inputTerm.name).not.toBe(queryTerm2.name)

    await wrapper.find(searchInputSel).setValue('test')
    await waitMs(500)
    expect(fetch).toHaveBeenCalled()
    const searchTerms = wrapper.findAll(searchOptSel)
    expect(searchTerms.length).toBe(2)

    searchTerms[1]?.trigger('dblclick')
    await nextTick()
    // We should have one term with updated content
    valTerms = wrapper.findAll(termRowSel)
    expect(valTerms.length).toBe(1)
    expect(valTerms[0]?.findAll('td')[0]?.text()).toBe(queryTerm2.name)
    expect(valTerms[0]?.findAll('td')[1]?.text()).toBe(queryTerm2.ontology_name)
    expect(valTerms[0]?.findAll('td')[2]?.text()).toBe(queryTerm2.accession)
  })

  test('select term with allow_list=true', async () => {
    params.editConfigField.allow_list = true
    fetchRes = { terms: [queryTerm, queryTerm2] }

    const wrapper = await showModal()
    let valTerms = wrapper.findAll(termRowSel)
    expect(valTerms.length).toBe(1)
    expect(valTerms[0]?.findAll('td')[0]?.text()).toBe(inputTerm.name)

    await wrapper.find(searchInputSel).setValue('test')
    await waitMs(500)
    expect(fetch).toHaveBeenCalled()
    const searchTerms = wrapper.findAll(searchOptSel)
    expect(searchTerms.length).toBe(2)

    searchTerms[1]?.trigger('dblclick')
    await nextTick()
    // We should have one term with updated content
    valTerms = wrapper.findAll(termRowSel)
    expect(valTerms.length).toBe(2)
    expect(valTerms[0]?.findAll('td')[0]?.text()).toBe(inputTerm.name)
    expect(valTerms[1]?.findAll('td')[0]?.text()).toBe(queryTerm2.name)
  })

  test('select term with allow_list and term already in list', async () => {
    params.editConfigField.allow_list = true
    params.value.value.push(queryTerm2)
    fetchRes = { terms: [queryTerm, queryTerm2] }

    const wrapper = await showModal()
    let valTerms = wrapper.findAll(termRowSel)
    expect(valTerms.length).toBe(2)
    expect(valTerms[0]?.findAll('td')[0]?.text()).toBe(inputTerm.name)
    expect(valTerms[1]?.findAll('td')[0]?.text()).toBe(queryTerm2.name)

    await wrapper.find(searchInputSel).setValue('test')
    await waitMs(500)
    expect(fetch).toHaveBeenCalled()
    const searchTerms = wrapper.findAll(searchOptSel)
    expect(searchTerms.length).toBe(2)

    searchTerms[1]?.trigger('dblclick')
    await nextTick()
    // List should remain unchanged
    valTerms = wrapper.findAll(termRowSel)
    expect(valTerms.length).toBe(2)
    expect(valTerms[0]?.findAll('td')[0]?.text()).toBe(inputTerm.name)
    expect(valTerms[1]?.findAll('td')[0]?.text()).toBe(queryTerm2.name)
  })

  test('display inputs in term edit mode', async () => {
    const wrapper = await showModal()
    // NOTE: Limiting search to term row (insert row also exists)
    const term = wrapper.find(termRowSel)
    expect(term.findAll(displayCellSel).length).toBe(3)
    expect(term.findAll(editCellSel).length).toBe(0)
    expect(term.find(rowInputSel).exists()).toBe(false) // No inputs present

    const editBtn = term.find(editBtnSel)
    await editBtn.trigger('click')
    expect(term.findAll(displayCellSel).length).toBe(0) // Regualr rows hidden
    expect(term.findAll(editCellSel).length).toBe(3) // Edit rows visible
    const inputs = term.findAll(rowInputSel)
    expect(inputs.length).toBe(3) // Inputs visible
    expect(inputs[0]?.attributes().value).toBe(inputTerm.name)
    expect(inputs[1]?.attributes().value).toBe(inputTerm.ontology_name)
    expect(inputs[2]?.attributes().value).toBe(inputTerm.accession)
  })

  test('update buttons and search in term edit mode', async () => {
    // NOTE: Split from previous test to make unit tests more atomic
    const wrapper = await showModal()
    expect(wrapper.find(searchInputSel).attributes().disabled).not.toBeDefined()
    const term = wrapper.find(termRowSel)
    expect(term.find(editBtnSel).attributes().disabled).not.toBeDefined()
    expect(term.find(delBtnSel).attributes().disabled).not.toBeDefined()
    expect(term.find(stopBtnSel).exists()).toBe(false)

    const editBtn = term.find(editBtnSel)
    await editBtn.trigger('click')
    // Search should be disabled
    expect(wrapper.find(searchInputSel).attributes().disabled).toBeDefined()
    // Edit button should be replaced by stop button
    expect(term.find(editBtnSel).exists()).toBe(false)
    expect(term.find(stopBtnSel).exists()).toBe(true)
    expect(term.find(stopBtnSel).attributes().disabled).not.toBeDefined()
    expect(term.find(delBtnSel).attributes().disabled).not.toBeDefined()
  })

  test('display inputs in term edit mode with multiple terms', async () => {
    params.editConfigField.allow_list = true
    params.value.value.push(inputTerm2)
    const wrapper = await showModal()

    const terms = wrapper.findAll(termRowSel)
    expect(terms.length).toBe(2)
    expect(terms[0]?.findAll(displayCellSel).length).toBe(3)
    expect(terms[0]?.findAll(editCellSel).length).toBe(0)
    expect(terms[1]?.findAll(displayCellSel).length).toBe(3)
    expect(terms[1]?.findAll(editCellSel).length).toBe(0)

    const editBtn = terms[0]!.find(editBtnSel)
    await editBtn.trigger('click')
    expect(terms[0]?.findAll(displayCellSel).length).toBe(0)
    expect(terms[0]?.findAll(editCellSel).length).toBe(3) // Edit cells visible
    expect(terms[1]?.findAll(displayCellSel).length).toBe(3)
    expect(terms[1]?.findAll(editCellSel).length).toBe(0)
  })

  test('update buttons in term edit mode with multiple terms', async () => {
    params.editConfigField.allow_list = true
    params.value.value.push(inputTerm2)
    const wrapper = await showModal()

    const terms = wrapper.findAll(termRowSel)
    expect(terms[0]?.find(upBtnSel).attributes().disabled).toBeDefined()
    expect(terms[0]?.find(downBtnSel).attributes().disabled).not.toBeDefined()
    expect(terms[0]?.find(editBtnSel).attributes().disabled).not.toBeDefined()
    expect(terms[0]?.find(delBtnSel).attributes().disabled).not.toBeDefined()
    expect(terms[0]?.find(stopBtnSel).exists()).toBe(false)
    expect(terms[1]?.find(upBtnSel).attributes().disabled).not.toBeDefined()
    expect(terms[1]?.find(downBtnSel).attributes().disabled).toBeDefined()
    expect(terms[1]?.find(editBtnSel).attributes().disabled).not.toBeDefined()
    expect(terms[1]?.find(delBtnSel).attributes().disabled).not.toBeDefined()
    expect(terms[1]?.find(stopBtnSel).exists()).toBe(false)

    const editBtn = terms[0]!.find(editBtnSel)
    await editBtn.trigger('click')

    expect(terms[0]?.find(upBtnSel).attributes().disabled).toBeDefined()
    expect(terms[0]?.find(downBtnSel).attributes().disabled).toBeDefined()
    expect(terms[0]?.find(stopBtnSel).attributes().disabled).not.toBeDefined()
    expect(terms[0]?.find(delBtnSel).attributes().disabled).not.toBeDefined()
    expect(terms[0]?.find(editBtnSel).exists()).toBe(false)
    // All buttons for the second term should be disabled
    expect(terms[1]?.find(upBtnSel).attributes().disabled).toBeDefined()
    expect(terms[1]?.find(downBtnSel).attributes().disabled).toBeDefined()
    expect(terms[1]?.find(editBtnSel).attributes().disabled).toBeDefined()
    expect(terms[1]?.find(delBtnSel).attributes().disabled).toBeDefined()
    expect(terms[1]?.find(stopBtnSel).exists()).toBe(false)
  })

  test('edit row with unknown ontology without allow limit', async () => {
    const wrapper = await showModal()
    const term = wrapper.find(termRowSel)
    const editBtn = term.find(editBtnSel)

    await editBtn.trigger('click')
    const cell = term.findAll(editCellSel)[1]
    const input  = cell!.find(termInputSel)
    expect(input?.classes()).not.toContain('text-danger')

    await input.setValue(OBO_ID_UNKNOWN)
    // Since there is no limit, this should not be set
    expect(input?.classes()).not.toContain('text-danger')
  })

  test('edit row with unknown ontology with allow limit', async () => {
    params.editConfigField.ontologies = [OBO_ID_NCBITAXON]
    const wrapper = await showModal()
    const term = wrapper.find(termRowSel)
    const editBtn = term.find(editBtnSel)

    await editBtn.trigger('click')
    const cell = term.findAll(editCellSel)[1]
    const input  = cell!.find(termInputSel)
    expect(input?.classes()).not.toContain('text-danger')

    await input.setValue(OBO_ID_UNKNOWN)
    // With limit this should be set
    expect(input?.classes()).toContain('text-danger')
  })

  test('submit edit without changes', async () => {
    const wrapper = await showModal()
    const term = wrapper.find(termRowSel)
    const updateBtn = wrapper.find(updateBtnSel) // Modal update button
    expect(updateBtn.attributes().disabled).toBeDefined()
    const editBtn = term.find(editBtnSel)

    await editBtn.trigger('click')
    expect(updateBtn.attributes().disabled).toBeDefined()
    const stopBtn = term.find(stopBtnSel)

    await stopBtn.trigger('click')
    // No changes = button should still be disabled
    expect(updateBtn.attributes().disabled).toBeDefined()
  })

  test('submit edit with changes', async () => {
    const wrapper = await showModal()
    const term = wrapper.find(termRowSel)
    const updateBtn = wrapper.find(updateBtnSel)
    expect(updateBtn.attributes().disabled).toBeDefined()
    const editBtn = term.find(editBtnSel)

    await editBtn.trigger('click')
    const input = term.findAll(editCellSel)[0]!.find(termInputSel)
    await input.setValue('Updated term name')
    expect(updateBtn.attributes().disabled).toBeDefined()
    const stopBtn = term.find(stopBtnSel)

    await stopBtn.trigger('click')
    // Changes = button should be enabled
    expect(updateBtn.attributes().disabled).not.toBeDefined()
  })

  test('submit edit update with changes', async () => {
    const wrapper = await showModal()
    const term = wrapper.find(termRowSel)
    const updateBtn = wrapper.find(updateBtnSel)
    const editBtn = term.find(editBtnSel)

    await editBtn.trigger('click')
    const input = term.findAll(editCellSel)[0]!.find(termInputSel)
    await input.setValue('Updated term name')
    const stopBtn = term.find(stopBtnSel)
    expect(fetch).not.toHaveBeenCalled()

    await stopBtn.trigger('click')
    await updateBtn.trigger('click')
    const updatedTerm = copy(inputTerm) as EditOntologyRef
    updatedTerm.name = 'Updated term name'
    const reqBody = {
      updated_cells: [{
        header_name: 'organism',
        header_type: 'characteristics',
        obj_cls: 'GenericMaterial',
        uuid: TMP_UUID,
        value: [updatedTerm],
      }],
      verify: true
    }
    expect(fetch).toHaveBeenCalledWith(
      cellUpdateUrl,
      expect.objectContaining({ body: JSON.stringify(reqBody) }))
  })

  test('insert term with empty value and allow_list=false', async () => {
    params.value.value = []
    const wrapper = await showModal()
    const row = wrapper.find(insertRowSel)
    const inputs = row.findAll(termInputSel)
    const insertBtn = row.find(insertBtnSel)

    expect(wrapper.find(alertNoListSel).exists()).toBe(false)
    expect(wrapper.find(termRowSel).exists()).toBe(false)
    expect(insertBtn.attributes().disabled).toBeDefined()
    expect(wrapper.find(updateBtnSel).attributes().disabled).toBeDefined()

    await inputs[0]!.setValue(inputTerm.name)
    await inputs[1]!.setValue(inputTerm.ontology_name)
    await inputs[2]!.setValue(inputTerm.accession)
    // Insert button should now be enabled
    expect(insertBtn.attributes().disabled).not.toBeDefined()

    await insertBtn.trigger('click')
    // No list alert should be visible
    expect(wrapper.find(alertNoListSel).exists()).toBe(true)
    // Insert row should be replaced by regular term row
    expect(wrapper.find(termRowSel).exists()).toBe(true)
    expect(wrapper.find(insertRowSel).exists()).toBe(false)
    expect(wrapper.find(updateBtnSel).attributes().disabled).not.toBeDefined()
  })

  test('insert term with empty value and allow_list=true', async () => {
    params.editConfigField.allow_list = true
    params.value.value = []
    const wrapper = await showModal()
    const row = wrapper.find(insertRowSel)
    const inputs = row.findAll(termInputSel)
    const insertBtn = row.find(insertBtnSel)

    expect(wrapper.find(alertNoListSel).exists()).toBe(false)
    expect(wrapper.find(termRowSel).exists()).toBe(false)

    await inputs[0]!.setValue(inputTerm.name)
    await inputs[1]!.setValue(inputTerm.ontology_name)
    await inputs[2]!.setValue(inputTerm.accession)
    await insertBtn.trigger('click')

    expect(wrapper.find(alertNoListSel).exists()).toBe(false)
    // Insert row should still be visible
    expect(wrapper.find(termRowSel).exists()).toBe(true)
    expect(wrapper.find(insertRowSel).exists()).toBe(true)
  })

  test('insert term with existing value and allow_list=true', async () => {
    params.editConfigField.allow_list = true
    const wrapper = await showModal()
    const row = wrapper.find(insertRowSel)
    const inputs = row.findAll(termInputSel)
    const insertBtn = row.find(insertBtnSel)
    expect(insertBtn.attributes().disabled).toBeDefined()

    // Input identical
    await inputs[0]!.setValue(inputTerm.name)
    await inputs[1]!.setValue(inputTerm.ontology_name)
    await inputs[2]!.setValue(inputTerm.accession)
    // Insert button should remain disabled
    expect(insertBtn.attributes().disabled).toBeDefined()
  })

  test('try term insert with matching name and ontology', async () => {
    params.editConfigField.allow_list = true
    const wrapper = await showModal()
    const row = wrapper.find(insertRowSel)
    const inputs = row.findAll(termInputSel)
    const insertBtn = row.find(insertBtnSel)
    expect(wrapper.find(alertNoListSel).exists()).toBe(false)
    expect(wrapper.findAll(termRowSel).length).toBe(1)

    await inputs[0]!.setValue(inputTerm.name)
    await inputs[1]!.setValue(inputTerm.ontology_name)
    await inputs[2]!.setValue(inputTerm2.accession) // Different accession
    // Insert button should remain disabled
    expect(insertBtn.attributes().disabled).toBeDefined()
  })

  test('try term insert with matching accession', async () => {
    params.editConfigField.allow_list = true
    const wrapper = await showModal()
    const row = wrapper.find(insertRowSel)
    const inputs = row.findAll(termInputSel)
    const insertBtn = row.find(insertBtnSel)
    expect(wrapper.find(alertNoListSel).exists()).toBe(false)
    expect(wrapper.findAll(termRowSel).length).toBe(1)

    await inputs[0]!.setValue(inputTerm2.name)
    await inputs[1]!.setValue(inputTerm2.ontology_name)
    await inputs[2]!.setValue(inputTerm.accession) // Accession already in list
    // Insert button should remain disabled
    expect(insertBtn.attributes().disabled).toBeDefined()
  })

  test('try term insert with ontology limit and unknown ontology', async () => {
    params.editConfigField.allow_list = true
    params.editConfigField.ontologies = [OBO_ID_NCBITAXON]
    const wrapper = await showModal()
    const row = wrapper.find(insertRowSel)
    const inputs = row.findAll(termInputSel)
    const insertBtn = row.find(insertBtnSel)
    expect(wrapper.find(alertNoListSel).exists()).toBe(false)
    expect(wrapper.findAll(termRowSel).length).toBe(1)

    await inputs[0]!.setValue(inputTerm2.name)
    await inputs[1]!.setValue(OBO_ID_UBERON) // Known ontology but not allowed
    await inputs[2]!.setValue(inputTerm2.accession)
    // Insert button should remain disabled
    expect(insertBtn.attributes().disabled).toBeDefined()
  })

  test('render clipboard copy button with existing value', async () => {
    const wrapper = await showModal()
    const copyBtn = wrapper.find(clipCopySel)
    expect(copyBtn.exists()).toBe(true)
    expect(copyBtn.attributes().disabled).not.toBeDefined()
  })

  test('render clipboard copy button with empty value', async () => {
    params.value.value = []
    const wrapper = await showModal()
    const copyBtn = wrapper.find(clipCopySel)
    expect(copyBtn.attributes().disabled).toBeDefined() // Should be disabled
  })

  test('copy ontology terms into clipboard on button click', async () => {
    const wrapper = await showModal()
    const copyBtn = wrapper.find(clipCopySel)
    await copyBtn.trigger('click')
    expect(mockCopy).toHaveBeenCalledWith(JSON.stringify([inputTerm]))
  })

  test('paste term to replace existing', async () => {
    const wrapper = await showModal()
    expect(wrapper.findAll(termRowSel).length).toBe(1)
    let term = wrapper.find(termRowSel)
    expect(term?.find(termNameSel).text()).toBe(inputTerm.name)
    expect(term?.find(termOboSel).text()).toBe(inputTerm.ontology_name)
    expect(term?.find(termAccSel).text()).toBe(inputTerm.accession)

    const pasteInput = wrapper.find(clipPasteSel)
    await pasteInput.setValue(JSON.stringify([inputTerm2]))
    expect(wrapper.findAll(termRowSel).length).toBe(1)

    // Replaced term
    term = wrapper.find(termRowSel)
    expect(term?.find(termNameSel).text()).toBe(inputTerm2.name)
    expect(term?.find(termOboSel).text()).toBe(inputTerm2.ontology_name)
    expect(term?.find(termAccSel).text()).toBe(inputTerm2.accession)
  })

  test('paste term with no existing terms', async () => {
    params.value.value = []
    const wrapper = await showModal()
    expect(wrapper.findAll(termRowSel).length).toBe(0)

    const pasteInput = wrapper.find(clipPasteSel)
    await pasteInput.setValue(JSON.stringify([inputTerm2]))
    expect(wrapper.findAll(termRowSel).length).toBe(1)

    // Added term
    const term = wrapper.find(termRowSel)
    expect(term?.find(termNameSel).text()).toBe(inputTerm2.name)
    expect(term?.find(termOboSel).text()).toBe(inputTerm2.ontology_name)
    expect(term?.find(termAccSel).text()).toBe(inputTerm2.accession)
  })

  test('paste list of terms with allow_list=true', async () => {
    params.editConfigField.allow_list = true
    const wrapper = await showModal()
    expect(wrapper.findAll(termRowSel).length).toBe(1)

    const pasteInput = wrapper.find(clipPasteSel)
    await pasteInput.setValue(JSON.stringify([inputTerm2, inputTerm3]))
    expect(wrapper.findAll(termRowSel).length).toBe(2)

    // Original term should be updated with list
    const terms = wrapper.findAll(termRowSel)
    expect(terms[0]?.find(termNameSel).text()).toBe(inputTerm2.name)
    expect(terms[0]?.find(termOboSel).text()).toBe(inputTerm2.ontology_name)
    expect(terms[0]?.find(termAccSel).text()).toBe(inputTerm2.accession)
    expect(terms[1]?.find(termNameSel).text()).toBe(inputTerm3.name)
    expect(terms[1]?.find(termOboSel).text()).toBe(inputTerm3.ontology_name)
    expect(terms[1]?.find(termAccSel).text()).toBe(inputTerm3.accession)
  })

  test('paste list of terms with allow_list=false', async () => {
    expect(params.editConfigField.allow_list).toBe(false)
    const wrapper = await showModal()
    expect(wrapper.findAll(termRowSel).length).toBe(1)

    const pasteInput = wrapper.find(clipPasteSel)
    await pasteInput.setValue(JSON.stringify([inputTerm2, inputTerm3]))
    expect(wrapper.findAll(termRowSel).length).toBe(1)

    // This should fail, original term should be present
    const term = wrapper.find(termRowSel)
    expect(term?.find(termNameSel).text()).toBe(inputTerm.name)
    expect(term?.find(termOboSel).text()).toBe(inputTerm.ontology_name)
    expect(term?.find(termAccSel).text()).toBe(inputTerm.accession)
  })

  test('paste list of terms with unallowed ontology', async () => {
    params.editConfigField.allow_list = true
    params.editConfigField.ontologies = [OBO_ID_NCBITAXON]
    const updTerm2 = copy(inputTerm2) as EditOntologyRef
    updTerm2.ontology_name = OBO_ID_UBERON
    const wrapper = await showModal()
    expect(wrapper.findAll(termRowSel).length).toBe(1)

    const pasteInput = wrapper.find(clipPasteSel)
    await pasteInput.setValue(JSON.stringify([updTerm2, inputTerm3]))
    expect(wrapper.findAll(termRowSel).length).toBe(1)

    // This should fail, original term should be present
    const term = wrapper.find(termRowSel)
    expect(term?.find(termNameSel).text()).toBe(inputTerm.name)
    expect(term?.find(termOboSel).text()).toBe(inputTerm.ontology_name)
    expect(term?.find(termAccSel).text()).toBe(inputTerm.accession)
  })

  // TODO: Test state reset on modal reopen
  // TODO: Test title with node name (needs mocked api or real grid)
})
