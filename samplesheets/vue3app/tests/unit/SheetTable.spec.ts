import { type TemplateRef } from 'vue'
import { beforeEach, describe, expect, test, vi } from 'vitest'
import { mount, type VueWrapper } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { AllCommunityModule, ModuleRegistry } from 'ag-grid-community'

import SheetTable from '@/components/SheetTable.vue'
import DataCellRenderer from '@/components/renderers/DataCellRenderer.vue'
import { useAppStore } from '@/stores/appStore.ts'
import { useEditStore } from '@/stores/editStore.ts'
import { useTableStore } from '@/stores/tableStore.ts'
import {
  type RenderTableData,
  type SodarContext,
  type StudyShortcuts
} from '@/types.ts'
import { ROW_INS_MSG_DISABLED } from '@/constants.ts'

import { type SheetTableProps } from '../testTypes.ts'
import { copy, setUpTableStore } from '../testUtils.ts'
import { sodarContext } from '../data/sodarContext.ts'
import studyTables from '../data/studyTables.json'
import studyShortcutsGermline from '../data/studyShortcutsGermline.json'
import { ASSAY_UUID, STUDY_PLUGIN_NAME, STUDY_UUID } from '../testConstants.ts'

// Test Data -------------------------------------------------------------------

// Expected values for default table
const exTopHeaderStudy = [
  ['Row', 'secondary'],
  ['Source', 'info'],
  ['', 'info'],
  ['Process', 'danger'],
  ['Sample', 'warning'],
]
const exTopHeaderAssay = [
  ['Process', 'danger'],
  ['Library Name', 'success'],
  ['Process', 'danger'],
  ['Raw Data File', 'success'],
  ['Raw Data File', 'success'],
  ['Process', 'danger'],
  ['Derived Data File', 'success'],
]

const mockModal = { show: vi.fn() }
let props: SheetTableProps
let context: SodarContext
let tables: RenderTableData

// Selectors
const studyCardSel = '.sodar-ss-data-card-study'
const assayCardSel = '.sodar-ss-data-card-assay'
const studyGridSel = '#sodar-ss-table-grid-study'
const assayGridSel = '#sodar-ss-table-grid-assay-' + ASSAY_UUID
const rowBtnSel = '.sodar-ss-row-insert-btn'
const excelBtnSel = '.sodar-ss-excel-export-btn'

// Global Setup ----------------------------------------------------------------

ModuleRegistry.registerModules([AllCommunityModule])
// TODO: How to expose renderers globally for ag-grid? (see warnings)

const mockNotifyCb = vi.fn()

// Tests -----------------------------------------------------------------------

describe('SheetTable.vue', () => {
  function mountComponent (tableUuid: string, assayMode: boolean): VueWrapper {
    setUpTableStore(context, tables, STUDY_UUID, ASSAY_UUID)
    props = {
      assayMode: assayMode,
      colToggleModalRef: mockModal as unknown as TemplateRef,
      notifyCb: mockNotifyCb,
      tableUuid: tableUuid
    }
    // NOTE: Testing with shallowMount() as there are issues with exposing
    //       DataCellRender for ag-grid
    return mount(
      SheetTable, { props: props, expose: { DataCellRenderer } })
  }

  beforeEach(() => {
    setActivePinia(createPinia())
    const appStore = useAppStore()
    appStore.editMode = false

    context = copy(sodarContext) as SodarContext
    tables = copy(studyTables) as RenderTableData

    // Suppress ag-grid warnings
    vi.spyOn(console, 'warn').mockImplementation(() => undefined)
  })

  test('render study table', async () => {
    const wrapper = mountComponent(STUDY_UUID, false)
    expect(wrapper.find(studyCardSel).exists()).toBe(true)
    expect(wrapper.find(assayCardSel).exists()).toBe(false)
    expect(wrapper.find('h4').text()).toBe('Study Table')
    expect(wrapper.find(excelBtnSel).attributes().href).toBe(
      'export/excel/study/' + STUDY_UUID
    )
    expect(wrapper.find(rowBtnSel).exists()).toBe(false)
    const filterInput = wrapper.find('#sodar-ss-data-filter-study')
    expect(filterInput.exists()).toBe(true)
    expect(filterInput.attributes().value).toBe('')
    expect(wrapper.find(studyGridSel).exists()).toBe(true)
  })

  test('render assay table', async () => {
    const wrapper = mountComponent(ASSAY_UUID, true)
    expect(wrapper.find(studyCardSel).exists()).toBe(false)
    expect(wrapper.find(assayCardSel).exists()).toBe(true)
    expect(wrapper.find('h4').text()).toBe('Assay Table')
    expect(wrapper.find(rowBtnSel).exists()).toBe(false)
    expect(wrapper.find(excelBtnSel).attributes().href).toBe(
      'export/excel/assay/' + ASSAY_UUID
    )
    expect(wrapper.find(
      '#sodar-ss-data-filter-assay-' + ASSAY_UUID).exists()).toBe(true)
    expect(wrapper.find(assayGridSel).exists()).toBe(true)
  })

  test('open column toggle modal on button click', async () => {
    const wrapper = mountComponent(STUDY_UUID, false)
    expect(mockModal.show).not.toHaveBeenCalled()
    const btn = wrapper.find('.sodar-ss-column-toggle-btn')
    await btn.trigger('click')
    expect(mockModal.show).toHaveBeenCalled()
  })

  test('render study grid top header', async () => {
    const wrapper = mountComponent(STUDY_UUID, false)
    const grid = wrapper.find(studyGridSel)
    const topHeaders = grid.findAll('.ag-header-group-cell')
    expect(topHeaders.length).toBe(5)
    for (let i = 0; i < exTopHeaderStudy.length; i++) {
      const e = exTopHeaderStudy[i]
      expect(topHeaders[i]?.text()).toBe(e![0])
      expect(topHeaders[i]?.classes()).toContain('bg-' + e![1])
    }
  })

  test('render study grid field header', async () => {
    const wrapper = mountComponent(STUDY_UUID, false)
    const grid = wrapper.find(studyGridSel)
    const headers = grid.findAll('.ag-header-cell')
    const headerInput = ['#'].concat(
      studyTables.tables.study.field_header.map(x => x.value))
    for (let i = 0; i < headerInput.length; i++) {
      expect(headers[i]?.text()).toBe(headerInput[i])
    }
  })

  test('render study grid shortcut column', async () => {
    context.studies[STUDY_UUID]!.plugin_name = STUDY_PLUGIN_NAME
    tables.tables.study.shortcuts = studyShortcutsGermline as
      unknown as StudyShortcuts

    const wrapper = mountComponent(STUDY_UUID, false)
    const grid = wrapper.find(studyGridSel)
    const topHeaders = grid.findAll('.ag-header-group-cell')
    expect(topHeaders.length).toBe(6)
    expect(topHeaders[5]?.text()).toBe('Links')
    expect(topHeaders[5]?.classes()).toContain('bg-secondary')

    const headers = grid.findAll('.ag-header-cell')
    expect(headers.length).toBe(12)
    expect(headers[11]?.text()).toBe('Study')
  })

  // TODO: Test render study grid rows once expose issue is solved

  test('render assay grid top header', async () => {
    let exTopHeader = copy(exTopHeaderStudy) as Array<Array<string>>
    exTopHeader.splice(2, 1) // Second source group not there by default
    exTopHeader = exTopHeader.concat(exTopHeaderAssay)

    const wrapper = mountComponent(ASSAY_UUID, true)
    const grid = wrapper.find(assayGridSel)
    const topHeaders = grid.findAll('.ag-header-group-cell')
    expect(topHeaders.length).toBe(exTopHeader.length)
    for (let i = 0; i < exTopHeader.length; i++) {
      const e = exTopHeader[i]
      expect(topHeaders[i]?.text(), i.toString()).toBe(e![0])
      expect(topHeaders[i]?.classes()).toContain('bg-' + e![1])
    }
  })

  test('render assay grid top header with second source group', async () => {
    const exTopHeader = exTopHeaderStudy.concat(exTopHeaderAssay)
    // @ts-expect-error We know it's there
    tables.display_config.assays[ASSAY_UUID].nodes[0].fields[1].visible = true

    const wrapper = mountComponent(ASSAY_UUID, true)
    const grid = wrapper.find(assayGridSel)
    const topHeaders = grid.findAll('.ag-header-group-cell')
    expect(topHeaders.length).toBe(exTopHeader.length)
    for (let i = 0; i < exTopHeader.length; i++) {
      const e = exTopHeader[i]
      expect(topHeaders[i]?.text(), i.toString()).toBe(e![0])
      expect(topHeaders[i]?.classes()).toContain('bg-' + e![1])
    }
  })

  test('render assay grid field header', async () => {
    const wrapper = mountComponent(ASSAY_UUID, true)
    const grid = wrapper.find(assayGridSel)
    const headers = grid.findAll('.ag-header-cell')
    // Name fields are visible by default for study columns
    const exStudy = ['#', 'Name', 'Protocol', 'Name']
    for (let i = 0; i < exStudy.length; i++) {
      expect(headers[i]?.text()).toBe(exStudy[i])
    }
    // Assay fields
    const exAssay = [
      'Protocol',
      'Name',
      'Protocol',
      'Assay Name',
      'Name',
      'Name',
      'Data Transformation Name',
      'Name'
    ]
    for (let i = 4; i < exAssay.length + 4; i++) {
      expect(headers[i]?.text()).toBe(exAssay[i - 4])
    }
  })

  test('render assay grid row links column', async () => {
    expect(context.irods_status).toBe(true)
    context.studies[STUDY_UUID]!.assays[ASSAY_UUID]!.display_row_links = true

    const wrapper = mountComponent(ASSAY_UUID, true)
    const grid = wrapper.find(assayGridSel)
    const topHeaders = grid.findAll('.ag-header-group-cell')
    expect(topHeaders.length).toBe(12)
    expect(topHeaders[11]?.text()).toBe('iRODS')
    expect(topHeaders[11]?.classes()).toContain('bg-secondary')

    const headers = grid.findAll('.ag-header-cell')
    expect(headers.length).toBe(13)
    expect(headers[12]?.text()).toBe('Links')
  })

  test('render study table in edit mode', async () => {
    const appStore = useAppStore()
    appStore.editMode = true
    const wrapper = mountComponent(STUDY_UUID, false)
    // Row insert button should be visible and enabled
    const rowBtn = wrapper.find(rowBtnSel)
    expect(rowBtn.exists()).toBe(true)
    expect(rowBtn.attributes().disabled).not.toBeDefined()
    expect(rowBtn.attributes().title).toBe('')
  })

  test('render assay table in edit mode', async () => {
    const appStore = useAppStore()
    appStore.editMode = true
    const wrapper = mountComponent(ASSAY_UUID, true)
    const rowBtn = wrapper.find(rowBtnSel)
    expect(rowBtn.exists()).toBe(true)
    expect(rowBtn.attributes().disabled).not.toBeDefined()
    expect(rowBtn.attributes().title).toBe('')
  })

  test('render study table in edit mode with unsaved row', async () => {
    const appStore = useAppStore()
    const editStore = useEditStore()
    appStore.editMode = true
    editStore.unsavedRow = { id: '0', tableUuid: STUDY_UUID }
    const wrapper = mountComponent(STUDY_UUID, false)
    // Row insert button should be disabled with title message
    const rowBtn = wrapper.find(rowBtnSel)
    expect(rowBtn.attributes().disabled).toBeDefined()
    expect(rowBtn.attributes().title).toBe(ROW_INS_MSG_DISABLED)
  })

  test('display initial filter value', async () => {
    const tableStore = useTableStore()
    tableStore.initialFilter = '0814'
    const wrapper = mountComponent(STUDY_UUID, false)
    expect(wrapper.find(
      '#sodar-ss-data-filter-study').attributes().value).toBe('0814')
  })

  // TODO: Test insertRow() call
  // TODO: Test render assay grid rows once expose issue is solved
})
