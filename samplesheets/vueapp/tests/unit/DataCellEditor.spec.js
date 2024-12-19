import { createLocalVue, mount } from '@vue/test-utils'
import {
  studyUuid,
  assayUuid,
  copy,
  getAppStub,
  getSheetTableComponents,
  getSheetTablePropsData,
  waitNT,
  waitRAF,
  waitAG
} from '../testUtils.js'
import { initGridOptions } from '@/utils/gridUtils.js'
import BootstrapVue from 'bootstrap-vue'
import VueClipboard from 'vue-clipboard2'
import SheetTable from '@/components/SheetTable.vue'
import studyTablesEdit from './data/studyTablesEdit.json'
import studyTablesOneCol from './data/studyTablesOneCol.json'
import sheetEditConfigModified from './data/sheetEditConfigModified.json'

// Set up extended Vue constructor
const localVue = createLocalVue()
localVue.use(BootstrapVue)
localVue.use(VueClipboard)

// Init data
const studyEditConfig = sheetEditConfigModified.studies[studyUuid]
let gridOptions

describe('DataCellEditor.vue', () => {
  function mountSheetTable (params = {}, editStudyConfig = null) {
    const retParams = Object.assign({
      app: getAppStub(params),
      editMode: true,
      editContext: copy(studyTablesEdit).edit_context,
      gridOptions: null,
      editStudyConfig: null
    }, params)
    gridOptions = initGridOptions(retParams.app, retParams.editMode)
    retParams.gridOptions = gridOptions
    return mount(SheetTable, {
      localVue,
      propsData: getSheetTablePropsData(retParams),
      components: getSheetTableComponents()
    })
  }

  beforeAll(() => {
    // NOTE: Workaround for bootstrap-vue "Vue warn" errors, see issue #1034
    jest.spyOn(console, 'error').mockImplementation(jest.fn())
    // Disable warnings
    jest.spyOn(console, 'warn').mockImplementation(jest.fn())
  })

  beforeEach(() => {
    jest.resetModules()
    jest.clearAllMocks()
  })

  it('renders editor for name column', async () => {
    const table = copy(studyTablesOneCol).tables.study
    table.field_header[0] = studyTablesEdit.tables.study.field_header[0]
    table.table_data[0][0] = studyTablesEdit.tables.study.table_data[0][0]
    const wrapper = mountSheetTable({
      table: table,
      editStudyConfig: {
        nodes: [{ fields: [studyEditConfig.nodes[0].fields[0]] }]
      }
    })
    await waitAG(wrapper)
    await waitRAF()

    await wrapper.find('.sodar-ss-data-cell').trigger('dblclick')
    expect(wrapper.find('.sodar-ss-data-cell-editor').exists()).toBe(true)
    expect(wrapper.find('input.ag-cell-edit-input').exists()).toBe(true)
    expect(wrapper.find('.ag-cell-edit-input').classes()).toContain('text-left')
    expect(wrapper.find('.ag-cell-edit-input').element.value).toBe('0814')
  })

  // NOTE: Skip ontology column (different editor)

  it('renders editor for unit column', async () => {
    const table = copy(studyTablesOneCol).tables.study
    table.field_header[0] = studyTablesEdit.tables.study.field_header[2]
    table.table_data[0][0] = studyTablesEdit.tables.study.table_data[0][2]
    const wrapper = mountSheetTable({
      table: table,
      editStudyConfig: {
        nodes: [{ fields: [studyEditConfig.nodes[0].fields[2]] }]
      }
    })
    await waitAG(wrapper)
    await waitRAF()

    await wrapper.find('.sodar-ss-data-cell').trigger('dblclick')
    expect(wrapper.find('.sodar-ss-data-cell-popup').exists()).toBe(true)
    expect(wrapper.find('input.ag-cell-edit-input').exists()).toBe(true)
    expect(wrapper.find('.ag-cell-edit-input').classes()).toContain('text-right')
    expect(wrapper.find('.ag-cell-edit-input').element.value).toBe('90')
    const unitSelect = wrapper.find('#sodar-ss-data-cell-unit')
    expect(unitSelect.exists()).toBe(true)
    const unitOptions = unitSelect.findAll('option')
    expect(unitOptions.length).toBe(3)
    for (let i = 0; i < unitOptions.length; i++) {
      expect(['-', 'day', 'year']).toContain(unitOptions.at(i).text())
    }
  })

  // NOTE: Skip protocol column (different editor)

  it('renders editor for text column', async () => {
    const table = copy(studyTablesOneCol).tables.study
    table.field_header[0] = studyTablesEdit.tables.study.field_header[4]
    table.table_data[0][0] = studyTablesEdit.tables.study.table_data[0][4]
    const wrapper = mountSheetTable({
      table: table,
      editStudyConfig: {
        nodes: [{ fields: [studyEditConfig.nodes[1].fields[1]] }]
      }
    })
    await waitAG(wrapper)
    await waitRAF()

    await wrapper.find('.sodar-ss-data-cell').trigger('dblclick')
    expect(wrapper.find('.sodar-ss-data-cell-editor').exists()).toBe(true)
    expect(wrapper.find('input.ag-cell-edit-input').exists()).toBe(true)
    expect(wrapper.find('.ag-cell-edit-input').classes()).toContain('text-left')
    expect(wrapper.find('.ag-cell-edit-input').element.value).toBe('scalpel')
  })

  it('renders editor for contact column', async () => {
    const table = copy(studyTablesOneCol).tables.study
    table.field_header[0] = studyTablesEdit.tables.study.field_header[5]
    table.table_data[0][0] = studyTablesEdit.tables.study.table_data[0][5]
    const wrapper = mountSheetTable({
      table: table,
      editStudyConfig: {
        nodes: [{ fields: [studyEditConfig.nodes[1].fields[2]] }]
      }
    })
    await waitAG(wrapper)
    await waitRAF()

    await wrapper.find('.sodar-ss-data-cell').trigger('dblclick')
    expect(wrapper.find('.sodar-ss-data-cell-editor').exists()).toBe(true)
    expect(wrapper.find('input.ag-cell-edit-input').exists()).toBe(true)
    expect(wrapper.find('.ag-cell-edit-input').classes()).toContain('text-left')
    expect(wrapper.find('.ag-cell-edit-input').element.value).toBe('John Doe')
  })

  it('renders editor for contact column with full syntax', async () => {
    const value = 'John Doe <john@example.com>'
    const table = copy(studyTablesOneCol).tables.study
    table.field_header[0] = studyTablesEdit.tables.study.field_header[5]
    table.table_data[0][0] = studyTablesEdit.tables.study.table_data[0][5]
    table.table_data[0][0].value = value
    const wrapper = mountSheetTable({
      table: table,
      editStudyConfig: {
        nodes: [{ fields: [studyEditConfig.nodes[1].fields[2]] }]
      }
    })
    await waitAG(wrapper)
    await waitRAF()

    await wrapper.find('.sodar-ss-data-cell').trigger('dblclick')
    expect(wrapper.find('.sodar-ss-data-cell-editor').exists()).toBe(true)
    expect(wrapper.find('input.ag-cell-edit-input').exists()).toBe(true)
    expect(wrapper.find('.ag-cell-edit-input').classes()).toContain('text-left')
    expect(wrapper.find('.ag-cell-edit-input').element.value).toBe(value)
  })

  it('renders editor for date column', async () => {
    const table = copy(studyTablesOneCol).tables.study
    table.field_header[0] = studyTablesEdit.tables.study.field_header[6]
    table.table_data[0][0] = studyTablesEdit.tables.study.table_data[0][6]
    const wrapper = mountSheetTable({
      table: table,
      editStudyConfig: {
        nodes: [{ fields: [studyEditConfig.nodes[1].fields[3]] }]
      }
    })
    await waitAG(wrapper)
    await waitRAF()

    await wrapper.find('.sodar-ss-data-cell').trigger('dblclick')
    expect(wrapper.find('.sodar-ss-data-cell-editor').exists()).toBe(true)
    expect(wrapper.find('input.ag-cell-edit-input').exists()).toBe(true)
    expect(wrapper.find('.ag-cell-edit-input').classes()).toContain('text-left')
    expect(wrapper.find('.ag-cell-edit-input').element.value).toBe('2018-02-02')
  })

  it('renders editor for integer column', async () => {
    const table = copy(studyTablesOneCol).tables.study
    table.field_header[0] = studyTablesEdit.tables.study.field_header[8]
    table.table_data[0][0] = studyTablesEdit.tables.study.table_data[0][8]
    const wrapper = mountSheetTable({
      table: table,
      editStudyConfig: {
        nodes: [{ fields: [studyEditConfig.nodes[2].fields[1]] }]
      }
    })
    await waitAG(wrapper)
    await waitRAF()

    await wrapper.find('.sodar-ss-data-cell').trigger('dblclick')
    expect(wrapper.find('.sodar-ss-data-cell-popup').exists()).toBe(false)
    expect(wrapper.find('input.ag-cell-edit-input').exists()).toBe(true)
    expect(wrapper.find('.ag-cell-edit-input').classes()).toContain('text-right')
    expect(wrapper.find('.ag-cell-edit-input').element.value).toBe('0')
    expect(wrapper.find('#sodar-ss-data-cell-unit').exists()).toBe(false)
  })

  it('renders editor for select column', async () => {
    const table = copy(studyTablesOneCol).tables.study
    table.field_header[0] = studyTablesEdit.tables.study.field_header[9]
    table.table_data[0][0] = studyTablesEdit.tables.study.table_data[0][9]
    const wrapper = mountSheetTable({
      table: table,
      editStudyConfig: {
        nodes: [{ fields: [studyEditConfig.nodes[2].fields[2]] }]
      }
    })
    await waitAG(wrapper)
    await waitRAF()

    await wrapper.find('.sodar-ss-data-cell').trigger('dblclick')
    expect(wrapper.find('select.ag-cell-edit-input').exists()).toBe(true)
    expect(wrapper.find('.ag-cell-edit-input').element.value).toBe('yes')
    const unitOptions = wrapper.find('.ag-cell-edit-input').findAll('option')
    expect(unitOptions.length).toBe(3)
    for (let i = 0; i < unitOptions.length; i++) {
      expect(['-', 'yes', 'no']).toContain(unitOptions.at(i).text())
    }
  })

  it('updates value in name column', async () => {
    const value = '0814-UPDATED'
    const table = copy(studyTablesOneCol).tables.study
    table.field_header[0] = studyTablesEdit.tables.study.field_header[0]
    table.table_data[0][0] = copy(studyTablesEdit).tables.study.table_data[0][0]
    const wrapper = mountSheetTable({
      table: table,
      editStudyConfig: {
        nodes: [{ fields: [studyEditConfig.nodes[0].fields[0]] }]
      }
    })
    await waitAG(wrapper)
    await waitRAF()

    await wrapper.find('.sodar-ss-data-cell').trigger('dblclick')
    const input = wrapper.find('.ag-cell-edit-input')
    input.element.value = value
    await input.trigger('input')
    await gridOptions.api.stopEditing()
    expect(wrapper.find('.ag-cell-edit-input').exists()).toBe(false)
    expect(wrapper.find('.sodar-ss-data').text()).toBe(value)
  })

  it('updates value in name column to empty string (should fail)', async () => {
    const value = '0814'
    const table = copy(studyTablesOneCol).tables.study
    table.field_header[0] = studyTablesEdit.tables.study.field_header[0]
    table.table_data[0][0] = copy(studyTablesEdit).tables.study.table_data[0][0]
    const wrapper = mountSheetTable({
      table: table,
      editStudyConfig: {
        nodes: [{ fields: [studyEditConfig.nodes[0].fields[0]] }]
      }
    })
    await waitAG(wrapper)
    await waitRAF()

    await wrapper.find('.sodar-ss-data-cell').trigger('dblclick')
    const input = wrapper.find('.ag-cell-edit-input')
    expect(input.element.value).toBe(value)
    input.element.value = ''
    await input.trigger('input')
    await gridOptions.api.stopEditing()
    expect(wrapper.find('.ag-cell-edit-input').exists()).toBe(false)
    expect(wrapper.find('.sodar-ss-data').text()).toBe(value)
  })

  it('updates value in name column with invalid regex (should fail)', async () => {
    const value = '0814' // Special characters not allowed
    const table = copy(studyTablesOneCol).tables.study
    table.field_header[0] = studyTablesEdit.tables.study.field_header[0]
    table.table_data[0][0] = copy(studyTablesEdit).tables.study.table_data[0][0]
    const wrapper = mountSheetTable({
      table: table,
      editStudyConfig: {
        nodes: [{ fields: [studyEditConfig.nodes[0].fields[0]] }]
      }
    })
    await waitAG(wrapper)
    await waitRAF()

    await wrapper.find('.sodar-ss-data-cell').trigger('dblclick')
    const input = wrapper.find('.ag-cell-edit-input')
    expect(input.element.value).toBe(value)
    input.element.value = '0814 #%&:' // Special characters not allowed
    await input.trigger('input')
    await gridOptions.api.stopEditing()
    expect(wrapper.find('.ag-cell-edit-input').exists()).toBe(false)
    expect(wrapper.find('.sodar-ss-data').text()).toBe(value)
  })

  it('updates value in unit column', async () => {
    const oldValue = '90'
    const newValue = '100'
    const table = copy(studyTablesOneCol).tables.study
    table.field_header[0] = studyTablesEdit.tables.study.field_header[2]
    table.table_data[0][0] = copy(studyTablesEdit).tables.study.table_data[0][2]
    const wrapper = mountSheetTable({
      table: table,
      editStudyConfig: {
        nodes: [{ fields: [studyEditConfig.nodes[0].fields[2]] }]
      }
    })
    await waitAG(wrapper)
    await waitRAF()

    // NOTE: Vue inserts line breaks and spaces between words in spans, so we
    //       have to test these with toContain() (or modify the text)
    expect(wrapper.find('.sodar-ss-data').text()).toContain(oldValue)
    expect(wrapper.find('.sodar-ss-data').text()).toContain('day')
    await wrapper.find('.sodar-ss-data-cell').trigger('dblclick')
    const input = wrapper.find('.ag-cell-edit-input')
    input.element.value = newValue
    await input.trigger('input')
    await gridOptions.api.stopEditing()
    expect(wrapper.find('.ag-cell-edit-input').exists()).toBe(false)
    expect(wrapper.find('.sodar-ss-data').text()).toContain(newValue)
    expect(wrapper.find('.sodar-ss-data').text()).toContain('day')
  })

  it('updates value in unit column to a list', async () => {
    const oldValue = '90'
    const newValue = '100;101'
    const table = copy(studyTablesOneCol).tables.study
    table.field_header[0] = studyTablesEdit.tables.study.field_header[2]
    table.table_data[0][0] = copy(studyTablesEdit).tables.study.table_data[0][2]
    const wrapper = mountSheetTable({
      table: table,
      editStudyConfig: {
        nodes: [{ fields: [studyEditConfig.nodes[0].fields[2]] }]
      }
    })
    await waitAG(wrapper)
    await waitRAF()

    expect(wrapper.find('.sodar-ss-data').text()).toContain(oldValue)
    expect(wrapper.find('.sodar-ss-data').text()).not.toContain('100; 101')
    expect(wrapper.find('.sodar-ss-data').text()).toContain('day')
    await wrapper.find('.sodar-ss-data-cell').trigger('dblclick')
    const input = wrapper.find('.ag-cell-edit-input')
    input.element.value = newValue
    await input.trigger('input')
    await gridOptions.api.stopEditing()
    expect(wrapper.find('.ag-cell-edit-input').exists()).toBe(false)
    expect(wrapper.find('.sodar-ss-data').text()).toContain('100; 101')
    expect(wrapper.find('.sodar-ss-data').text()).toContain('day')
  })

  it('updates value in unit column outside range (should fail)', async () => {
    const oldValue = '90'
    const newValue = '170' // max = 150
    const table = copy(studyTablesOneCol).tables.study
    table.field_header[0] = studyTablesEdit.tables.study.field_header[2]
    table.table_data[0][0] = copy(studyTablesEdit).tables.study.table_data[0][2]
    const wrapper = mountSheetTable({
      table: table,
      editStudyConfig: {
        nodes: [{ fields: [studyEditConfig.nodes[0].fields[2]] }]
      }
    })
    await waitAG(wrapper)
    await waitRAF()

    expect(wrapper.find('.sodar-ss-data').text()).toContain(oldValue)
    await wrapper.find('.sodar-ss-data-cell').trigger('dblclick')
    const input = wrapper.find('.ag-cell-edit-input')
    input.element.value = newValue
    await input.trigger('input')
    await waitNT(wrapper.vm)
    expect(wrapper.find('.ag-cell-edit-input').classes()).toContain('text-danger')
    await gridOptions.api.stopEditing()
    expect(wrapper.find('.ag-cell-edit-input').exists()).toBe(false)
    expect(wrapper.find('.sodar-ss-data').text()).toContain(oldValue)
  })

  it('updates list value in unit column outside range (should fail)', async () => {
    const oldValue = '90'
    const newValue = '100;170'
    const table = copy(studyTablesOneCol).tables.study
    table.field_header[0] = studyTablesEdit.tables.study.field_header[2]
    table.table_data[0][0] = copy(studyTablesEdit).tables.study.table_data[0][2]
    const wrapper = mountSheetTable({
      table: table,
      editStudyConfig: {
        nodes: [{ fields: [studyEditConfig.nodes[0].fields[2]] }]
      }
    })
    await waitAG(wrapper)
    await waitRAF()

    expect(wrapper.find('.sodar-ss-data').text()).toContain(oldValue)
    await wrapper.find('.sodar-ss-data-cell').trigger('dblclick')
    const input = wrapper.find('.ag-cell-edit-input')
    input.element.value = newValue
    await input.trigger('input')
    await gridOptions.api.stopEditing()
    expect(wrapper.find('.ag-cell-edit-input').exists()).toBe(false)
    expect(wrapper.find('.sodar-ss-data').text()).toContain(oldValue)
  })

  it('updates unit in unit column', async () => {
    const oldValue = '90'
    const table = copy(studyTablesOneCol).tables.study
    table.field_header[0] = studyTablesEdit.tables.study.field_header[2]
    table.table_data[0][0] = copy(studyTablesEdit).tables.study.table_data[0][2]
    const wrapper = mountSheetTable({
      table: table,
      editStudyConfig: {
        nodes: [{ fields: [studyEditConfig.nodes[0].fields[2]] }]
      }
    })
    await waitAG(wrapper)
    await waitRAF()

    expect(wrapper.find('.sodar-ss-data').text()).toContain(oldValue)
    expect(wrapper.find('.sodar-ss-data').text()).toContain('day')
    expect(wrapper.find('.sodar-ss-data').text()).not.toContain('year')
    await wrapper.find('.sodar-ss-data-cell').trigger('dblclick')
    const unitInput = wrapper.find('#sodar-ss-data-cell-unit')
    await unitInput.findAll('option').at(2).setSelected()
    await gridOptions.api.stopEditing()
    expect(wrapper.find('.ag-cell-edit-input').exists()).toBe(false)
    expect(wrapper.find('.sodar-ss-data').text()).toContain('90')
    expect(wrapper.find('.sodar-ss-data').text()).toContain('year')
    expect(wrapper.find('.sodar-ss-data').text()).not.toContain('day')
  })

  it('updates value in unit column with empty value', async () => {
    const table = copy(studyTablesOneCol).tables.study
    table.field_header[0] = studyTablesEdit.tables.study.field_header[2]
    table.table_data[0][0] = copy(studyTablesEdit).tables.study.table_data[0][2]
    const wrapper = mountSheetTable({
      table: table,
      editStudyConfig: {
        nodes: [{ fields: [studyEditConfig.nodes[0].fields[2]] }]
      }
    })
    await waitAG(wrapper)
    await waitRAF()

    await wrapper.find('.sodar-ss-data-cell').trigger('dblclick')
    const input = wrapper.find('.ag-cell-edit-input')
    input.element.value = ''
    await input.trigger('input')
    await gridOptions.api.stopEditing()
    expect(wrapper.find('.ag-cell-edit-input').exists()).toBe(false)
    expect(wrapper.find('.sodar-ss-data').text()).toBe('-')
  })

  it('updates unit in unit column to empty unit', async () => {
    const oldValue = '90'
    const table = copy(studyTablesOneCol).tables.study
    table.field_header[0] = studyTablesEdit.tables.study.field_header[2]
    table.table_data[0][0] = copy(studyTablesEdit).tables.study.table_data[0][2]
    const wrapper = mountSheetTable({
      table: table,
      editStudyConfig: {
        nodes: [{ fields: [studyEditConfig.nodes[0].fields[2]] }]
      }
    })
    await waitAG(wrapper)
    await waitRAF()

    expect(wrapper.find('.sodar-ss-data').text()).toContain(oldValue)
    expect(wrapper.find('.sodar-ss-data').text()).toContain('day')
    await wrapper.find('.sodar-ss-data-cell').trigger('dblclick')
    const unitInput = wrapper.find('#sodar-ss-data-cell-unit')
    await unitInput.findAll('option').at(0).setSelected()
    await gridOptions.api.stopEditing()
    expect(wrapper.find('.ag-cell-edit-input').exists()).toBe(false)
    expect(wrapper.find('.sodar-ss-data').text()).toBe('90')
  })

  it('updates value in text column', async () => {
    const oldValue = 'scalpel'
    const newValue = 'scalpel type B'
    const table = copy(studyTablesOneCol).tables.study
    table.field_header[0] = studyTablesEdit.tables.study.field_header[4]
    table.table_data[0][0] = copy(studyTablesEdit).tables.study.table_data[0][4]
    const wrapper = mountSheetTable({
      table: table,
      editStudyConfig: {
        nodes: [{ fields: [studyEditConfig.nodes[1].fields[1]] }]
      }
    })
    await waitAG(wrapper)
    await waitRAF()

    expect(wrapper.find('.sodar-ss-data').text()).toBe(oldValue)
    await wrapper.find('.sodar-ss-data-cell').trigger('dblclick')
    const input = wrapper.find('.ag-cell-edit-input')
    input.element.value = newValue
    await input.trigger('input')
    await gridOptions.api.stopEditing()
    expect(wrapper.find('.ag-cell-edit-input').exists()).toBe(false)
    expect(wrapper.find('.sodar-ss-data').text()).toBe(newValue)
  })

  it('updates value in text column to a list', async () => {
    const table = copy(studyTablesOneCol).tables.study
    table.field_header[0] = studyTablesEdit.tables.study.field_header[4]
    table.table_data[0][0] = copy(studyTablesEdit).tables.study.table_data[0][4]
    const wrapper = mountSheetTable({
      table: table,
      editStudyConfig: {
        nodes: [{ fields: [studyEditConfig.nodes[1].fields[1]] }]
      }
    })
    await waitAG(wrapper)
    await waitRAF()

    expect(table.table_data[0][0].value.length).toBe(7) // String
    expect(wrapper.find('.sodar-ss-data').text()).toBe('scalpel')
    await wrapper.find('.sodar-ss-data-cell').trigger('dblclick')
    const input = wrapper.find('.ag-cell-edit-input')
    input.element.value = 'scalpel type A;scalpel type B'
    await input.trigger('input')
    await gridOptions.api.stopEditing()
    expect(wrapper.find('.ag-cell-edit-input').exists()).toBe(false)
    expect(wrapper.find('.sodar-ss-data').text()).toBe(
      'scalpel type A; scalpel type B') // Note the extra space
    expect(table.table_data[0][0].value.length).toBe(2) // List
  })

  it('updates value in text column with empty value', async () => {
    const table = copy(studyTablesOneCol).tables.study
    table.field_header[0] = studyTablesEdit.tables.study.field_header[4]
    table.table_data[0][0] = copy(studyTablesEdit).tables.study.table_data[0][4]
    const wrapper = mountSheetTable({
      table: table,
      editStudyConfig: {
        nodes: [{ fields: [studyEditConfig.nodes[1].fields[1]] }]
      }
    })
    await waitAG(wrapper)
    await waitRAF()

    await wrapper.find('.sodar-ss-data-cell').trigger('dblclick')
    const input = wrapper.find('.ag-cell-edit-input')
    input.element.value = ''
    await input.trigger('input')
    await gridOptions.api.stopEditing()
    expect(wrapper.find('.ag-cell-edit-input').exists()).toBe(false)
    expect(wrapper.find('.sodar-ss-data').text()).toBe('-')
  })

  it('updates value in contact column', async () => {
    const oldValue = 'John Doe'
    const newValue = 'Jane Doe'
    const table = copy(studyTablesOneCol).tables.study
    table.field_header[0] = studyTablesEdit.tables.study.field_header[5]
    table.table_data[0][0] = copy(studyTablesEdit).tables.study.table_data[0][5]
    const wrapper = mountSheetTable({
      table: table,
      editStudyConfig: {
        nodes: [{ fields: [studyEditConfig.nodes[1].fields[2]] }]
      }
    })
    await waitAG(wrapper)
    await waitRAF()

    expect(wrapper.find('.sodar-ss-data').text()).toBe(oldValue)
    await wrapper.find('.sodar-ss-data-cell').trigger('dblclick')
    const input = wrapper.find('.ag-cell-edit-input')
    input.element.value = newValue
    await input.trigger('input')
    await gridOptions.api.stopEditing()
    expect(wrapper.find('.ag-cell-edit-input').exists()).toBe(false)
    expect(wrapper.find('.sodar-ss-data').text()).toBe(newValue)
    expect(wrapper.find('.sodar-ss-data').find('a').exists()).toBe(false)
  })

  it('updates value in contact column with full syntax', async () => {
    const oldValue = 'John Doe'
    const table = copy(studyTablesOneCol).tables.study
    table.field_header[0] = studyTablesEdit.tables.study.field_header[5]
    table.table_data[0][0] = copy(studyTablesEdit).tables.study.table_data[0][5]
    const wrapper = mountSheetTable({
      table: table,
      editStudyConfig: {
        nodes: [{ fields: [studyEditConfig.nodes[1].fields[2]] }]
      }
    })
    await waitAG(wrapper)
    await waitRAF()

    expect(wrapper.find('.sodar-ss-data').text()).toBe(oldValue)
    await wrapper.find('.sodar-ss-data-cell').trigger('dblclick')
    const input = wrapper.find('.ag-cell-edit-input')
    input.element.value = 'Jane Doe <jane@example.com>'
    await input.trigger('input')
    await gridOptions.api.stopEditing()
    expect(wrapper.find('.ag-cell-edit-input').exists()).toBe(false)
    expect(wrapper.find('.sodar-ss-data').text()).toBe('Jane Doe')
    expect(wrapper.find('.sodar-ss-data').find('a').exists()).toBe(true)
    expect(wrapper.find('.sodar-ss-data').find('a')
      .attributes().href).toBe('mailto:jane@example.com')
  })

  it('updates value in contact column with empty value', async () => {
    const table = copy(studyTablesOneCol).tables.study
    table.field_header[0] = studyTablesEdit.tables.study.field_header[5]
    table.table_data[0][0] = copy(studyTablesEdit).tables.study.table_data[0][5]
    const wrapper = mountSheetTable({
      table: table,
      editStudyConfig: {
        nodes: [{ fields: [studyEditConfig.nodes[1].fields[2]] }]
      }
    })
    await waitAG(wrapper)
    await waitRAF()

    await wrapper.find('.sodar-ss-data-cell').trigger('dblclick')
    const input = wrapper.find('.ag-cell-edit-input')
    input.element.value = ''
    await input.trigger('input')
    await gridOptions.api.stopEditing()
    expect(wrapper.find('.ag-cell-edit-input').exists()).toBe(false)
    expect(wrapper.find('.sodar-ss-data').text()).toBe('-')
    expect(wrapper.find('.sodar-ss-data').find('a').exists()).toBe(false)
  })

  it('updates value in date column', async () => {
    const oldValue = '2018-02-02'
    const newValue = '2018-05-25'
    const table = copy(studyTablesOneCol).tables.study
    table.field_header[0] = studyTablesEdit.tables.study.field_header[6]
    table.table_data[0][0] = copy(studyTablesEdit).tables.study.table_data[0][6]
    const wrapper = mountSheetTable({
      table: table,
      editStudyConfig: {
        nodes: [{ fields: [studyEditConfig.nodes[1].fields[3]] }]
      }
    })
    await waitAG(wrapper)
    await waitRAF()

    expect(wrapper.find('.sodar-ss-data').text()).toBe(oldValue)
    await wrapper.find('.sodar-ss-data-cell').trigger('dblclick')
    const input = wrapper.find('.ag-cell-edit-input')
    input.element.value = newValue
    await input.trigger('input')
    await gridOptions.api.stopEditing()
    expect(wrapper.find('.ag-cell-edit-input').exists()).toBe(false)
    expect(wrapper.find('.sodar-ss-data').text()).toBe(newValue)
  })

  it('updates value in date column to invalid month (should fail)', async () => {
    const oldValue = '2018-02-02'
    const newValue = '2018-13-02'
    const table = copy(studyTablesOneCol).tables.study
    table.field_header[0] = studyTablesEdit.tables.study.field_header[6]
    table.table_data[0][0] = copy(studyTablesEdit).tables.study.table_data[0][6]
    const wrapper = mountSheetTable({
      table: table,
      editStudyConfig: {
        nodes: [{ fields: [studyEditConfig.nodes[1].fields[3]] }]
      }
    })
    await waitAG(wrapper)
    await waitRAF()

    expect(wrapper.find('.sodar-ss-data').text()).toBe(oldValue)
    await wrapper.find('.sodar-ss-data-cell').trigger('dblclick')
    const input = wrapper.find('.ag-cell-edit-input')
    input.element.value = newValue
    await input.trigger('input')
    await waitNT(wrapper.vm)
    expect(wrapper.find('.ag-cell-edit-input').classes()).toContain('text-danger')
    await gridOptions.api.stopEditing()
    expect(wrapper.find('.ag-cell-edit-input').exists()).toBe(false)
    expect(wrapper.find('.sodar-ss-data').text()).toBe(oldValue)
  })

  it('updates value in date column to invalid day (should fail)', async () => {
    const oldValue = '2018-02-02'
    const newValue = '2018-02-32'
    const table = copy(studyTablesOneCol).tables.study
    table.field_header[0] = studyTablesEdit.tables.study.field_header[6]
    table.table_data[0][0] = copy(studyTablesEdit).tables.study.table_data[0][6]
    const wrapper = mountSheetTable({
      table: table,
      editStudyConfig: {
        nodes: [{ fields: [studyEditConfig.nodes[1].fields[3]] }]
      }
    })
    await waitAG(wrapper)
    await waitRAF()

    expect(wrapper.find('.sodar-ss-data').text()).toBe(oldValue)
    await wrapper.find('.sodar-ss-data-cell').trigger('dblclick')
    const input = wrapper.find('.ag-cell-edit-input')
    input.element.value = newValue
    await input.trigger('input')
    await waitNT(wrapper.vm)
    expect(wrapper.find('.ag-cell-edit-input').classes()).toContain('text-danger')
    await gridOptions.api.stopEditing()
    expect(wrapper.find('.ag-cell-edit-input').exists()).toBe(false)
    expect(wrapper.find('.sodar-ss-data').text()).toBe(oldValue)
  })

  it('updates value in date column with empty value', async () => {
    const table = copy(studyTablesOneCol).tables.study
    table.field_header[0] = studyTablesEdit.tables.study.field_header[6]
    table.table_data[0][0] = copy(studyTablesEdit).tables.study.table_data[0][6]
    const wrapper = mountSheetTable({
      table: table,
      editStudyConfig: {
        nodes: [{ fields: [studyEditConfig.nodes[1].fields[3]] }]
      }
    })
    await waitAG(wrapper)
    await waitRAF()

    await wrapper.find('.sodar-ss-data-cell').trigger('dblclick')
    const input = wrapper.find('.ag-cell-edit-input')
    input.element.value = ''
    await input.trigger('input')
    await gridOptions.api.stopEditing()
    expect(wrapper.find('.ag-cell-edit-input').exists()).toBe(false)
    expect(wrapper.find('.sodar-ss-data').text()).toBe('-')
  })

  it('updates value in integer column', async () => {
    const oldValue = '0'
    const newValue = '2'
    const table = copy(studyTablesOneCol).tables.study
    table.field_header[0] = studyTablesEdit.tables.study.field_header[8]
    table.table_data[0][0] = copy(studyTablesEdit).tables.study.table_data[0][8]
    const wrapper = mountSheetTable({
      table: table,
      editStudyConfig: {
        nodes: [{ fields: [studyEditConfig.nodes[2].fields[1]] }]
      }
    })
    await waitAG(wrapper)
    await waitRAF()

    expect(wrapper.find('.sodar-ss-data').text()).toBe(oldValue)
    await wrapper.find('.sodar-ss-data-cell').trigger('dblclick')
    const input = wrapper.find('.ag-cell-edit-input')
    input.element.value = newValue
    await input.trigger('input')
    await gridOptions.api.stopEditing()
    expect(wrapper.find('.ag-cell-edit-input').exists()).toBe(false)
    expect(wrapper.find('.sodar-ss-data').text()).toBe(newValue)
  })

  it('updates value in integer column outside range (should fail)', async () => {
    const oldValue = '0'
    const newValue = '3' // Max range is 2
    const table = copy(studyTablesOneCol).tables.study
    table.field_header[0] = studyTablesEdit.tables.study.field_header[8]
    table.table_data[0][0] = copy(studyTablesEdit).tables.study.table_data[0][8]
    const wrapper = mountSheetTable({
      table: table,
      editStudyConfig: {
        nodes: [{ fields: [studyEditConfig.nodes[2].fields[1]] }]
      }
    })
    await waitAG(wrapper)
    await waitRAF()

    expect(wrapper.find('.sodar-ss-data').text()).toBe(oldValue)
    await wrapper.find('.sodar-ss-data-cell').trigger('dblclick')
    const input = wrapper.find('.ag-cell-edit-input')
    input.element.value = newValue
    await input.trigger('input')
    await waitNT(wrapper.vm)
    expect(wrapper.find('.ag-cell-edit-input').classes()).toContain('text-danger')
    await gridOptions.api.stopEditing()
    expect(wrapper.find('.ag-cell-edit-input').exists()).toBe(false)
    expect(wrapper.find('.sodar-ss-data').text()).toBe(oldValue)
  })

  it('updates value in integer column with text (should fail)', async () => {
    const oldValue = '0'
    const newValue = 'abcxyz' // Max range is 2
    const table = copy(studyTablesOneCol).tables.study
    table.field_header[0] = studyTablesEdit.tables.study.field_header[8]
    table.table_data[0][0] = copy(studyTablesEdit).tables.study.table_data[0][8]
    const wrapper = mountSheetTable({
      table: table,
      editStudyConfig: {
        nodes: [{ fields: [studyEditConfig.nodes[2].fields[1]] }]
      }
    })
    await waitAG(wrapper)
    await waitRAF()

    expect(wrapper.find('.sodar-ss-data').text()).toBe(oldValue)
    await wrapper.find('.sodar-ss-data-cell').trigger('dblclick')
    const input = wrapper.find('.ag-cell-edit-input')
    input.element.value = newValue
    await input.trigger('input')
    await waitNT(wrapper.vm)
    expect(wrapper.find('.ag-cell-edit-input').classes()).toContain('text-danger')
    await gridOptions.api.stopEditing()
    expect(wrapper.find('.ag-cell-edit-input').exists()).toBe(false)
    expect(wrapper.find('.sodar-ss-data').text()).toBe(oldValue)
  })

  it('updates value in integer column with empty value', async () => {
    const oldValue = '0'
    const table = copy(studyTablesOneCol).tables.study
    table.field_header[0] = studyTablesEdit.tables.study.field_header[8]
    table.table_data[0][0] = copy(studyTablesEdit).tables.study.table_data[0][8]
    const wrapper = mountSheetTable({
      table: table,
      editStudyConfig: {
        nodes: [{ fields: [studyEditConfig.nodes[2].fields[1]] }]
      }
    })
    await waitAG(wrapper)
    await waitRAF()

    expect(wrapper.find('.sodar-ss-data').text()).toBe(oldValue)
    await wrapper.find('.sodar-ss-data-cell').trigger('dblclick')
    const input = wrapper.find('.ag-cell-edit-input')
    input.element.value = ''
    await input.trigger('input')
    await gridOptions.api.stopEditing()
    expect(wrapper.find('.ag-cell-edit-input').exists()).toBe(false)
    expect(wrapper.find('.sodar-ss-data').text()).toBe('-')
  })

  it('updates value in select column', async () => {
    const table = copy(studyTablesOneCol).tables.study
    table.field_header[0] = studyTablesEdit.tables.study.field_header[9]
    table.table_data[0][0] = copy(studyTablesEdit).tables.study.table_data[0][9]
    const wrapper = mountSheetTable({
      table: table,
      editStudyConfig: {
        nodes: [{ fields: [studyEditConfig.nodes[2].fields[2]] }]
      }
    })
    await waitAG(wrapper)
    await waitRAF()

    expect(wrapper.find('.sodar-ss-data').text()).toBe('yes')
    await wrapper.find('.sodar-ss-data-cell').trigger('dblclick')
    await wrapper.find('.ag-cell-edit-input').findAll('option').at(2).setSelected()
    await gridOptions.api.stopEditing()
    expect(wrapper.find('.ag-cell-edit-input').exists()).toBe(false)
    expect(wrapper.find('.sodar-ss-data').text()).toBe('no')
  })

  it('updates value in select column with empty value', async () => {
    const table = copy(studyTablesOneCol).tables.study
    table.field_header[0] = studyTablesEdit.tables.study.field_header[9]
    table.table_data[0][0] = copy(studyTablesEdit).tables.study.table_data[0][9]
    const wrapper = mountSheetTable({
      table: table,
      editStudyConfig: {
        nodes: [{ fields: [studyEditConfig.nodes[2].fields[2]] }]
      }
    })
    await waitAG(wrapper)
    await waitRAF()

    expect(wrapper.find('.sodar-ss-data').text()).toBe('yes')
    await wrapper.find('.sodar-ss-data-cell').trigger('dblclick')
    await wrapper.find('.ag-cell-edit-input').findAll('option').at(0).setSelected()
    await gridOptions.api.stopEditing()
    expect(wrapper.find('.ag-cell-edit-input').exists()).toBe(false)
    expect(wrapper.find('.sodar-ss-data').text()).toBe('-')
  })

  it('updates value in process assay name column', async () => {
    const value = '0815-N1-DNA1-WES1-UPDATED'
    const table = copy(studyTablesOneCol).tables.assays[assayUuid]
    table.field_header[0] = studyTablesEdit.tables.assays[assayUuid].field_header[13]
    table.table_data[0][0] = copy(studyTablesEdit).tables.assays[assayUuid].table_data[0][13]
    const wrapper = mountSheetTable({
      table: table,
      editStudyConfig: {
        nodes: [{ fields: [studyEditConfig.assays[assayUuid].nodes[2].fields[1]] }]
      }
    })
    await waitAG(wrapper)
    await waitRAF()

    await wrapper.find('.sodar-ss-data-cell').trigger('dblclick')
    const input = wrapper.find('.ag-cell-edit-input')
    input.element.value = value
    await input.trigger('input')
    await gridOptions.api.stopEditing()
    expect(wrapper.find('.ag-cell-edit-input').exists()).toBe(false)
    expect(wrapper.find('.sodar-ss-data').text()).toBe(value)
  })

  it('updates process assay name column with empty value', async () => {
    const value = '' // NOTE: For named processes this IS allowed
    const table = copy(studyTablesOneCol).tables.assays[assayUuid]
    table.field_header[0] = studyTablesEdit.tables.assays[assayUuid].field_header[13]
    table.table_data[0][0] = copy(studyTablesEdit).tables.assays[assayUuid].table_data[0][13]
    const wrapper = mountSheetTable({
      table: table,
      editStudyConfig: {
        nodes: [{ fields: [studyEditConfig.assays[assayUuid].nodes[2].fields[1]] }]
      }
    })
    await waitAG(wrapper)
    await waitRAF()

    await wrapper.find('.sodar-ss-data-cell').trigger('dblclick')
    const input = wrapper.find('.ag-cell-edit-input')
    input.element.value = value
    await input.trigger('input')
    await gridOptions.api.stopEditing()
    expect(wrapper.find('.ag-cell-edit-input').exists()).toBe(false)
    expect(wrapper.find('.sodar-ss-data').text()).toBe('-') // Empty value
  })

  // TODO: Test renaming to assay name already existing in table for new/old row
  // TODO: Test update propagation for multiple rows
  // TODO: Test value updating for new rows
})
