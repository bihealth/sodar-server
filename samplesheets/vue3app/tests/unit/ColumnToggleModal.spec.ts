import { nextTick } from 'vue'
import { beforeEach, describe, expect, test, vi } from 'vitest'
import {
  config,
  flushPromises,
  mount,
  type DOMWrapper,
  type VueWrapper
} from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { createBootstrap } from 'bootstrap-vue-next/plugins/createBootstrap'
import { type ColDef, type GridApi } from 'ag-grid-community'

import ColumnToggleModal from '@/components/modals/ColumnToggleModal.vue'
import { useAppStore } from '@/stores/appStore.ts'
import { useTableStore } from '@/stores/tableStore.ts'
import {
  type RenderTableData,
  type SheetTableCellData,
  type SheetTableFieldHeader,
  type StudyDisplayConfig,
  type SodarContext,
} from '@/types.ts'
import {
  AJAX_RES_OK,
  DISPLAY_SAVE_MSG,
  DISPLAY_SAVE_DEFAULT_SUFFIX,
  URL_DISPLAY_CONFIG_PREFIX,
  VARIANT_SUCCESS,
} from '@/constants.ts'

import { copy, setUpTableStore } from '../testUtils.ts'
import { sodarContext } from '../data/sodarContext.ts'
import studyTables from '../data/studyTables.json'
import { ASSAY_UUID, STUDY_UUID } from '../testConstants.ts'

// Test Data -------------------------------------------------------------------

let fieldVisible: boolean
const url = URL_DISPLAY_CONFIG_PREFIX + STUDY_UUID

const fieldInputSel = '.sodar-ss-toggle-field-check input'
const fieldSel = '.sodar-ss-col-toggle-field'
const tableSel = '.sodar-ss-col-toggle-table'
const topHeaderSel = '.sodar-ss-col-toggle-top-header'
const topTitleSel = '.sodar-ss-col-toggle-top-title'

// Global Setup ----------------------------------------------------------------

config.global.plugins = [createBootstrap()]
const mockNotifyCb = vi.fn()
global.fetch = vi.fn(() => Promise.resolve({
  json: () => Promise.resolve({ detail: AJAX_RES_OK }),
  status: 200} as Response)
)

// Tests -----------------------------------------------------------------------

describe('ColumnToggleModal.vue', () => {
  function getVisibleFieldCount (wrapper: VueWrapper): number {
    // TODO: Probably could do a shorthand map() thing for this
    const fields = wrapper.findAll(fieldSel)
    let ret = 0
    for (let i = 0; i < fields.length; i++) {
      // TODO: Why doesn't isVisible() work here?
      if (fields[i]!.attributes().style !== 'display: none;') ret += 1
    }
    return ret
  }

  async function showModal (
      studyUuid: string,
      assayMode: boolean
  ): Promise<VueWrapper> {
    const wrapper = mount(ColumnToggleModal)
    wrapper.vm.show(studyUuid, assayMode)
    await nextTick() // Must wait for all reactive vals to update
    return wrapper
  }
  const mockGridApi = {
    getColumn: () => {
      return { isVisible: () => { return fieldVisible } }
    },
    setColumnsVisible: vi.fn()
  }

  beforeEach(() => {
    vi.clearAllMocks()

    // Set up stores
    setActivePinia(createPinia())
    const appStore = useAppStore()
    const tableStore = useTableStore()

    appStore.currentStudyUuid = STUDY_UUID
    appStore.editMode = false
    appStore.notifyCb = mockNotifyCb
    appStore.sodarContext = copy(sodarContext) as SodarContext
    setUpTableStore(
      appStore.sodarContext,
      studyTables as unknown as RenderTableData,
      STUDY_UUID,
      ASSAY_UUID)

    // Mock GridApi
    tableStore.gridApi.study = mockGridApi as unknown as GridApi
    tableStore.gridApi.assays[ASSAY_UUID] = mockGridApi as unknown as GridApi
    fieldVisible = true // Default return value for isVisible()
  })

  test('render component for study', async () => {
    const nodeCount = studyTables.tables.study.top_header.length
    // NOTE: Name fields are hidden so subtract node count
    const fieldCount = studyTables.tables.study.field_header.length - nodeCount

    const wrapper = await showModal(STUDY_UUID, false)
    expect(wrapper.find('#sodar-ss-col-toggle-modal').exists()).toBe(true)
    expect(wrapper.find('.modal-title').text()).toBe('Toggle Study Columns')
    expect(wrapper.find(
      '#sodar-ss-col-toggle-modal-content').exists()).toBe(true)
    expect(wrapper.findAll(topHeaderSel).length).toBe(nodeCount)
    expect(wrapper.findAll(fieldSel).length).toBe(fieldCount)
  })

  test('render component for assay', async () => {
    const nodeCount = (
      studyTables as unknown as RenderTableData).tables.assays[
        ASSAY_UUID]?.top_header.length as number
    // @ts-expect-error Reducing unnecessary ts overhead in a basic test
    const fieldCount = studyTables.tables.assays[
        ASSAY_UUID]?.field_header?.length - nodeCount
    const wrapper = await showModal(ASSAY_UUID, true)
    expect(wrapper.find('.modal-title').text()).toBe('Toggle Assay Columns')
    expect(wrapper.findAll(topHeaderSel).length).toBe(nodeCount)
    expect(wrapper.findAll(fieldSel).length).toBe(fieldCount)
  })

  test('render source header', async () => {
    const wrapper = await showModal(STUDY_UUID, false)
    const topHeader = wrapper.findAll(topHeaderSel)[0]
    expect(topHeader?.exists()).toBe(true)
    const thTitle = topHeader!.find(topTitleSel)
    expect(thTitle.exists()).toBe(true)
    expect(thTitle.text()).toBe('Source')
    expect(thTitle.classes()).toContain('bg-info')
  })

  test('render process header', async () => {
    const wrapper = await showModal(STUDY_UUID, false)
    const topHeader = wrapper.findAll(topHeaderSel)[1]
    const thTitle = topHeader!.find(topTitleSel)
    expect(thTitle.text()).toBe('Process')
    expect(thTitle.classes()).toContain('bg-danger')
  })

  test('render sample header', async () => {
    const wrapper = await showModal(STUDY_UUID, false)
    const topHeader = wrapper.findAll(topHeaderSel)[2]
    const thTitle = topHeader!.find(topTitleSel)
    expect(thTitle.text()).toBe('Sample')
    expect(thTitle.classes()).toContain('bg-warning')
  })

  test('render source fields', async () => {
    const colSpan = studyTables.tables.study.top_header[0]!.colspan
    const inputFields = (
      copy(studyTables.tables.study.field_header) as
        Array<SheetTableFieldHeader>).slice(0, colSpan)

    const wrapper = await showModal(STUDY_UUID, false)
    const table = wrapper.findAll(tableSel)[0]
    const cmpFields = table!.findAll(fieldSel)
    expect(cmpFields.length).toBe(colSpan - 1) // Name column is omitted here

    for (let i = 1; i < inputFields.length; i ++) {
      const field = cmpFields[i - 1] as DOMWrapper<Element>
      expect(field.text()).toBe(inputFields[i]?.value)
      expect(field.find('.sodar-ss-toggle-field-editable').exists()).toBe(false)
      expect(field.find('.sodar-ss-toggle-field-no-data').exists()).toBe(false)
      const checkbox = field.find(fieldInputSel)
      expect(checkbox.attributes().checked, i.toString()).toBeDefined()
    }
  })

  test('render field no data label', async () => {
    const tableStore = useTableStore()
    // Clear values from 3rd cell in source (2nd in modal)
    for (let i = 0; i < tableStore.rowData.study.length; i++) {
      const cell = tableStore.rowData.study[i]!['col2'] as SheetTableCellData
      cell.value = ''
    }
    const wrapper = await showModal(STUDY_UUID, false)
    const table = wrapper.findAll(tableSel)[0]
    const field = table!.findAll(fieldSel)[1]
    expect(field?.find('.sodar-ss-toggle-field-no-data').exists()).toBe(true)
  })

  test('display hidden field checkbox unchecked', async () => {
    fieldVisible = false // GridApi returns false for isVisible()
    const wrapper = await showModal(STUDY_UUID, false)
    const table = wrapper.findAll(tableSel)[0]
    const field = table!.findAll(fieldSel)[1]
    const checkbox = field?.find(fieldInputSel)
    expect(checkbox?.attributes().checked).not.toBeDefined()
  })

  test('render editable label in edit mode', async () => {
    const appStore = useAppStore()
    const tableStore = useTableStore()

    appStore.editMode = true
    const colDef = tableStore.columnDefs.study[2]!.children[0]! as ColDef
    colDef.cellRendererParams = { fieldEditable: true }

    const wrapper = await showModal(STUDY_UUID, false)
    expect(wrapper.findAll('.sodar-ss-toggle-field-editable').length).toBe(1)
  })

  test('toggle node fields on button click', async () => {
    const wrapper = await showModal(STUDY_UUID, false)
    const table = wrapper.findAll(tableSel)[0]
    const fields = table!.findAll(fieldSel)
    for (let i = 0; i < fields.length; i ++) {
      const field = fields[i] as DOMWrapper<Element>
      const checkbox = field.find(fieldInputSel)
      expect(checkbox.attributes().checked, i.toString()).toBeDefined()
    }
    // Assert next node to make sure it is not affected
    const nextTable = wrapper.findAll(tableSel)[1]
    const nextFields = nextTable!.findAll(fieldSel)
    for (let i = 0; i < nextFields.length; i ++) {
      const field = nextFields[i] as DOMWrapper<Element>
      const checkbox = field.find(fieldInputSel)
      expect(checkbox.attributes().checked, i.toString()).toBeDefined()
    }
    expect(mockGridApi.setColumnsVisible).not.toHaveBeenCalled()

    const button = table?.find('.sodar-ss-toggle-node-btn')
    await button?.trigger('click')

    for (let i = 0; i < fields.length; i ++) {
      const field = fields[i] as DOMWrapper<Element>
      const checkbox = field.find(fieldInputSel)
      // All checkboxes should be unchecked now
      expect(checkbox.attributes().checked, i.toString()).not.toBeDefined()
    }
    // Assert next fields are still checked
    for (let i = 0; i < nextFields.length; i ++) {
      const field = nextFields[i] as DOMWrapper<Element>
      const checkbox = field.find(fieldInputSel)
      expect(checkbox.attributes().checked, i.toString()).toBeDefined()
    }
    expect(mockGridApi.setColumnsVisible).toHaveBeenCalled()
  })

  test('save default configuration', async () => {
    expect(fetch).not.toHaveBeenCalled()

    const wrapper = await showModal(STUDY_UUID, false)
    // Update config by toggling node fields
    const table = wrapper.findAll(tableSel)[0]!
    const button = table.find('.sodar-ss-toggle-node-btn')!
    await button.trigger('click')
    await wrapper.find('#sodar-ss-col-toggle-save-btn').trigger('click')
    await flushPromises()

    const exp = copy(studyTables.display_config) as StudyDisplayConfig
    // @ts-expect-error Ignoring for brevity
    exp['nodes'][0]!['fields'][1]!.visible = false
    // @ts-expect-error Ignoring for brevity
    exp['nodes'][0]!['fields'][2]!.visible = false
    expect(fetch).toHaveBeenCalledWith(url, expect.objectContaining(
      { body: JSON.stringify({ study_config: exp, set_default: true }) }))
    expect(mockNotifyCb).toHaveBeenCalledWith(
      DISPLAY_SAVE_MSG + DISPLAY_SAVE_DEFAULT_SUFFIX, VARIANT_SUCCESS)
  })

  test('close modal without changes', async () => {
    expect(fetch).not.toHaveBeenCalled()
    const wrapper = await showModal(STUDY_UUID, false)
    // TODO: How to test modal closing via button click instead of vm func?
    // @ts-expect-error The function is exposed on the component
    wrapper.vm.hideModal()
    expect(fetch).not.toHaveBeenCalled()
  })

  test('close modal with changes', async () => {
    expect(fetch).not.toHaveBeenCalled()
    const wrapper = await showModal(STUDY_UUID, false)

    // Update config by toggling node fields
    const table = wrapper.findAll(tableSel)[0]!
    const button = table.find('.sodar-ss-toggle-node-btn')!
    await button.trigger('click')

    // @ts-expect-error The function is exposed on the component
    wrapper.vm.hideModal()
    const exp = copy(studyTables.display_config) as StudyDisplayConfig
    // @ts-expect-error Ignoring for brevity
    exp['nodes'][0]!['fields'][1]!.visible = false
    // @ts-expect-error Ignoring for brevity
    exp['nodes'][0]!['fields'][2]!.visible = false
    expect(fetch).toHaveBeenCalledWith(url, expect.objectContaining(
      { body: JSON.stringify({ study_config: exp, set_default: false }) }))
  })

  test('filter column visibility', async () => {
    const wrapper = await showModal(STUDY_UUID, false)
    await nextTick()
    expect(getVisibleFieldCount(wrapper)).toBe(7)

    const filter = wrapper.find('#sodar-ss-col-toggle-modal-filter')
    await filter.setValue('organism')
    await filter.trigger('keyup')
    expect(getVisibleFieldCount(wrapper)).toBe(1)
  })

  // TODO: Figure out how to test bootstrap-vue-next checkbox input
})
