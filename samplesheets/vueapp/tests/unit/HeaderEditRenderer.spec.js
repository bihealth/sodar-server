import { createLocalVue, mount } from '@vue/test-utils'
import {
  studyUuid,
  copy,
  getAppStub,
  getSheetTableComponents,
  getSheetTablePropsData,
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
import sodarContext from './data/sodarContext.json'

// Set up extended Vue constructor
const localVue = createLocalVue()
localVue.use(BootstrapVue)
localVue.use(VueClipboard)

// Init data
const studyEditConfig = sheetEditConfigModified.studies[studyUuid]

describe('HeaderEditRenderer.vue', () => {
  function mountSheetTable (params = {}, editStudyConfig = null) {
    const retParams = Object.assign({
      app: getAppStub(params),
      editMode: true,
      editContext: copy(studyTablesEdit).edit_context,
      gridOptions: null,
      editStudyConfig: null
    }, params)
    retParams.gridOptions = initGridOptions(retParams.app, retParams.editMode)
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

  it('renders name edit header', async () => {
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

    const header = wrapper.find('.sodar-ss-header-edit')
    expect(header.exists()).toBe(true)
    expect(header.find('.sodar-ss-col-config-btn').exists()).toBe(true)
    expect(header.find('.sodar-ss-col-config-btn')
      .attributes().disabled).toBe(undefined)
  })

  it('renders name edit header with unsaved row', async () => {
    const table = copy(studyTablesOneCol).tables.study
    table.field_header[0] = studyTablesEdit.tables.study.field_header[0]
    table.table_data[0][0] = studyTablesEdit.tables.study.table_data[0][0]
    const app = getAppStub({ unsavedRow: { gridUuid: studyUuid, id: '5' } })
    const wrapper = mountSheetTable({
      app: app,
      table: table,
      editStudyConfig: {
        nodes: [{ fields: [studyEditConfig.nodes[0].fields[0]] }]
      }
    })
    await waitAG(wrapper)
    await waitRAF()

    const header = wrapper.find('.sodar-ss-header-edit')
    // NOTE: Should be disabled only until issue #897 is fixed
    expect(header.find('.sodar-ss-col-config-btn')
      .attributes().disabled).toBe('true')
  })

  it('renders characteristics edit header', async () => {
    const table = copy(studyTablesOneCol).tables.study
    table.field_header[0] = studyTablesEdit.tables.study.field_header[1]
    table.table_data[0][0] = studyTablesEdit.tables.study.table_data[0][1]
    const wrapper = mountSheetTable({
      table: table,
      editStudyConfig: {
        nodes: [{ fields: [studyEditConfig.nodes[0].fields[1]] }]
      }
    })
    await waitAG(wrapper)
    await waitRAF()

    const header = wrapper.find('.sodar-ss-header-edit')
    expect(header.find('.sodar-ss-col-config-btn')
      .attributes().disabled).toBe(undefined)
  })

  it('renders characteristics edit header with unsaved row', async () => {
    const table = copy(studyTablesOneCol).tables.study
    table.field_header[0] = studyTablesEdit.tables.study.field_header[1]
    table.table_data[0][0] = studyTablesEdit.tables.study.table_data[0][1]
    const app = getAppStub({ unsavedRow: { gridUuid: studyUuid, id: '5' } })
    const wrapper = mountSheetTable({
      app: app,
      table: table,
      editStudyConfig: {
        nodes: [{ fields: [studyEditConfig.nodes[0].fields[1]] }]
      }
    })
    await waitAG(wrapper)
    await waitRAF()

    const header = wrapper.find('.sodar-ss-header-edit')
    expect(header.find('.sodar-ss-col-config-btn')
      .attributes().disabled).toBe(undefined)
  })

  it('renders protocol edit header', async () => {
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

    const header = wrapper.find('.sodar-ss-header-edit')
    expect(header.find('.sodar-ss-col-config-btn')
      .attributes().disabled).toBe(undefined)
  })

  it('renders name edit header with unsaved row', async () => {
    const table = copy(studyTablesOneCol).tables.study
    table.field_header[0] = studyTablesEdit.tables.study.field_header[3]
    table.table_data[0][0] = studyTablesEdit.tables.study.table_data[0][3]
    const app = getAppStub({ unsavedRow: { gridUuid: studyUuid, id: '5' } })
    const wrapper = mountSheetTable({
      app: app,
      table: table,
      editStudyConfig: {
        nodes: [{ fields: [studyEditConfig.nodes[1].fields[0]] }]
      }
    })
    await waitAG(wrapper)
    await waitRAF()

    const header = wrapper.find('.sodar-ss-header-edit')
    // NOTE: Should be disabled only until issue #897 is fixed
    expect(header.find('.sodar-ss-col-config-btn')
      .attributes().disabled).toBe('true')
  })

  it('renders header when user is allowed to edit column', async () => {
    const sc = copy(sodarContext)
    sc.perms.edit_column = true
    const wrapper = mountSheetTable({ sodarContext: sc })
    await waitAG(wrapper)
    await waitRAF()

    const header = wrapper.find('.sodar-ss-header-edit')
    expect(header.find('.sodar-ss-col-config-btn').exists()).toBe(true)
  })

  // TODO: Test data provided to modalComponent per column type
  // TODO: How to access/modify renderer data?
})
