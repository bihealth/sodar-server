import { nextTick } from 'vue'
import { beforeEach, describe, expect, test, vi } from 'vitest'
import {
  config,
  mount,
  type DOMWrapper,
  type VueWrapper
} from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { createBootstrap } from 'bootstrap-vue-next/plugins/createBootstrap'
import { type GridApi } from 'ag-grid-community'

import ColumnToggleModal from '@/components/modals/ColumnToggleModal.vue'
import { useAppStore } from '@/stores/appStore.ts'
import { useTableStore } from '@/stores/tableStore.ts'
import {
  type RenderTableData,
  type SheetTableCellData,
  type SheetTableFieldHeader,
  type SodarContext,
} from '@/types.ts'

import { copy, setUpTableStore } from '../testUtils.ts'
import { sodarContext } from '../data/sodarContext.ts'
import studyTables from '../data/studyTables.json'
import { ASSAY_UUID, STUDY_UUID } from '../testConstants.ts'

// Test Data -------------------------------------------------------------------

let fieldVisible: boolean
const mockNotifyCb = vi.fn()

// Global Setup ----------------------------------------------------------------

config.global.plugins = [createBootstrap()]

// Tests -----------------------------------------------------------------------

describe('ColumnToggleModal.vue', () => {
  async function showModal (
      studyUuid: string,
      assayMode: boolean
  ): Promise<VueWrapper> {
    const wrapper = mount(ColumnToggleModal)
    wrapper.vm.show(studyUuid, assayMode, mockNotifyCb)
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
    expect(wrapper.findAll(
      '.sodar-ss-col-toggle-top-header').length).toBe(nodeCount)
    expect(wrapper.findAll(
      '.sodar-ss-col-toggle-field').length).toBe(fieldCount)
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
    expect(wrapper.findAll(
      '.sodar-ss-col-toggle-top-header').length).toBe(nodeCount)
    expect(wrapper.findAll(
      '.sodar-ss-col-toggle-field').length).toBe(fieldCount)
  })

  test('render source header', async () => {
    const wrapper = await showModal(STUDY_UUID, false)
    const topHeader = wrapper.findAll('.sodar-ss-col-toggle-top-header')[0]
    expect(topHeader?.exists()).toBe(true)
    const thTitle = topHeader!.find('.sodar-ss-col-toggle-top-title')
    expect(thTitle.exists()).toBe(true)
    expect(thTitle.text()).toBe('Source')
    expect(thTitle.classes()).toContain('bg-info')
  })

  test('render process header', async () => {
    const wrapper = await showModal(STUDY_UUID, false)
    const topHeader = wrapper.findAll('.sodar-ss-col-toggle-top-header')[1]
    const thTitle = topHeader!.find('.sodar-ss-col-toggle-top-title')
    expect(thTitle.text()).toBe('Process')
    expect(thTitle.classes()).toContain('bg-danger')
  })

  test('render sample header', async () => {
    const wrapper = await showModal(STUDY_UUID, false)
    const topHeader = wrapper.findAll('.sodar-ss-col-toggle-top-header')[2]
    const thTitle = topHeader!.find('.sodar-ss-col-toggle-top-title')
    expect(thTitle.text()).toBe('Sample')
    expect(thTitle.classes()).toContain('bg-warning')
  })

  test('render source fields', async () => {
    const colSpan = studyTables.tables.study.top_header[0]!.colspan
    const inputFields = (
      copy(studyTables.tables.study.field_header) as
        Array<SheetTableFieldHeader>).slice(0, colSpan)

    const wrapper = await showModal(STUDY_UUID, false)
    const topHeader = wrapper.findAll('.sodar-ss-col-toggle-table')[0]
    const cmpFields = topHeader!.findAll('.sodar-ss-col-toggle-field')
    expect(cmpFields.length).toBe(colSpan - 1) // Name column is omitted here

    for (let i = 1; i < inputFields.length; i ++) {
      const field = cmpFields[i - 1] as DOMWrapper<Element>
      expect(field.text()).toBe(inputFields[i]?.value)
      // TODO: Assert "editable" label once editMode is supported
      expect(field.find('.sodar-ss-toggle-field-editable').exists()).toBe(false)
      expect(field.find('.sodar-ss-toggle-field-no-data').exists()).toBe(false)
      const checkbox = field.find('.sodar-ss-toggle-field-check input')
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
    const topHeader = wrapper.findAll('.sodar-ss-col-toggle-table')[0]
    const field = topHeader!.findAll('.sodar-ss-col-toggle-field')[1]
    expect(field?.find('.sodar-ss-toggle-field-no-data').exists()).toBe(true)
  })

  test('display hidden field checkbox unchecked', async () => {
    fieldVisible = false // GridApi returns false for isVisible()
    const wrapper = await showModal(STUDY_UUID, false)
    const topHeader = wrapper.findAll('.sodar-ss-col-toggle-table')[0]
    const field = topHeader!.findAll('.sodar-ss-col-toggle-field')[1]
    const checkbox = field?.find('.sodar-ss-toggle-field-check input')
    expect(checkbox?.attributes().checked).not.toBeDefined()
  })

  test('toggle node fields on button click', async () => {
    const wrapper = await showModal(STUDY_UUID, false)
    const topHeader = wrapper.findAll('.sodar-ss-col-toggle-table')[0]
    const fields = topHeader!.findAll('.sodar-ss-col-toggle-field')
    for (let i = 0; i < fields.length; i ++) {
      const field = fields[i] as DOMWrapper<Element>
      const checkbox = field.find('.sodar-ss-toggle-field-check input')
      expect(checkbox.attributes().checked, i.toString()).toBeDefined()
    }
    // Assert next node to make sure it is not affected
    const nextTopHeader = wrapper.findAll('.sodar-ss-col-toggle-table')[1]
    const nextFields = nextTopHeader!.findAll('.sodar-ss-col-toggle-field')
    for (let i = 0; i < nextFields.length; i ++) {
      const field = nextFields[i] as DOMWrapper<Element>
      const checkbox = field.find('.sodar-ss-toggle-field-check input')
      expect(checkbox.attributes().checked, i.toString()).toBeDefined()
    }
    expect(mockGridApi.setColumnsVisible).not.toHaveBeenCalled()

    const button = topHeader?.find('.sodar-ss-toggle-node-btn')
    await button?.trigger('click')

    for (let i = 0; i < fields.length; i ++) {
      const field = fields[i] as DOMWrapper<Element>
      const checkbox = field.find('.sodar-ss-toggle-field-check input')
      // All checkboxes should be unchecked now
      expect(checkbox.attributes().checked, i.toString()).not.toBeDefined()
    }
    // Assert next fields are still checked
    for (let i = 0; i < nextFields.length; i ++) {
      const field = nextFields[i] as DOMWrapper<Element>
      const checkbox = field.find('.sodar-ss-toggle-field-check input')
      expect(checkbox.attributes().checked, i.toString()).toBeDefined()
    }
    expect(mockGridApi.setColumnsVisible).toHaveBeenCalled()
  })

  // NOTE: The following left to be done later due to timeboxing
  // NOTE: Need to figure out a clean way to test modal hiding and
  //       bootstrap-vue-next input
  // TODO: Test closing modal with changes (save)
  // TODO: Test closing modal without changes
  // TODO: Test saving default
  // TODO: Test filtering
})
