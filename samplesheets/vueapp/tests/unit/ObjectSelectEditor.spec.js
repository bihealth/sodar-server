import { createLocalVue, mount } from '@vue/test-utils'
import {
  studyUuid,
  // assayUuid,
  copy,
  getAppStub,
  getSheetTablePropsData,
  // waitNT,
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

describe('ObjectSelectEditor.vue', () => {
  function mountSheetTable (params = {}) {
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
      localVue, propsData: getSheetTablePropsData(retParams)
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

  it('renders object select editor for protocol', async () => {
    const value = 'sample collection'
    const table = copy(studyTablesOneCol).tables.study
    table.field_header[0] = studyTablesEdit.tables.study.field_header[3]
    table.table_data[0][0] = studyTablesEdit.tables.study.table_data[0][3]
    const wrapper = mountSheetTable({
      table: table,
      editStudyConfig: {
        nodes: [{ fields: [studyEditConfig.nodes[1].fields[0]] }]
      }
    })
    await waitAG(wrapper)
    await waitRAF()

    expect(wrapper.find('.sodar-ss-data').text()).toBe(value)
    await wrapper.find('.sodar-ss-data-cell').trigger('dblclick')
    expect(wrapper.find('.sodar-ss-data-object-select').exists()).toBe(true)
    const options = wrapper.find('.sodar-ss-data-object-select').findAll('option')
    expect(options.length).toBe(3)
  })

  it('updates object select editor value for protocol', async () => {
    const table = copy(studyTablesOneCol).tables.study
    table.field_header[0] = studyTablesEdit.tables.study.field_header[3]
    table.table_data[0][0] = copy(studyTablesEdit).tables.study.table_data[0][3]
    const wrapper = mountSheetTable({
      table: table,
      editStudyConfig: {
        nodes: [{ fields: [studyEditConfig.nodes[1].fields[0]] }]
      }
    })
    await waitAG(wrapper)
    await waitRAF()

    expect(wrapper.find('.sodar-ss-data').text()).toBe('sample collection')
    await wrapper.find('.sodar-ss-data-cell').trigger('dblclick')
    await wrapper.find('.sodar-ss-data-object-select')
      .findAll('option').at(0).setSelected()
    await gridOptions.api.stopEditing()
    expect(wrapper.find('.ag-cell-edit-input').exists()).toBe(false)
    expect(wrapper.find('.sodar-ss-data').text()).toBe('library preparation')
  })

  // TODO: Test editor with sample in assay table (first refactor edit helpers)

  /*
  it('renders object select editor for new sample in assay table', async () => {
    const value = '0815-N1'
    const table = copy(studyTablesOneCol).tables.assays[assayUuid]
    table.field_header[0] = studyTablesEdit.tables.assays[assayUuid].field_header[7]
    table.table_data[0][0] = studyTablesEdit.tables.assays[assayUuid].table_data[0][7]
    const wrapper = mountSheetTable({
      assayMode: true,
      table: table,
      editStudyConfig: {
        nodes: [{ fields: [studyEditConfig.nodes[2].fields[0]] }]
      }
    })
    await waitAG(wrapper)
    await waitRAF()
    await wrapper.find('.sodar-ss-row-insert-btn').trigger('click')

    const cell = wrapper.findAll('.sodar-ss-data-cell').at(1)
    expect(cell.find('.sodar-ss-data').text()).toBe('')
    await cell.trigger('dblclick')
    expect(wrapper.find('.sodar-ss-data-object-select').exists()).toBe(true)
    const options = wrapper.find('.sodar-ss-data-object-select').findAll('option')
    expect(options.length).toBe(3)
  })
  */
})
