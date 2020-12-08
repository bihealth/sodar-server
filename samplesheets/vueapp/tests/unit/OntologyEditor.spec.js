import { createLocalVue, mount } from '@vue/test-utils'
import {
  studyUuid,
  copy,
  getAppStub,
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

// Set up extended Vue constructor
const localVue = createLocalVue()
localVue.use(BootstrapVue)
localVue.use(VueClipboard)

// Init data
const studyEditConfig = sheetEditConfigModified.studies[studyUuid]
let app
let gridOptions

describe('OntologyEditor.vue', () => {
  function mountSheetTable (params = {}) {
    const retParams = Object.assign({
      app: app,
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
    app = getAppStub()
    app.$refs.ontologyEditModal = { showModal: jest.fn() }
  })

  it('renders and hides ontology editor', async () => {
    const value = 'Mus musculus; Homo sapiens'
    const table = copy(studyTablesOneCol).tables.study
    table.field_header[0] = studyTablesEdit.tables.study.field_header[1]
    table.table_data[0][0] = studyTablesEdit.tables.study.table_data[0][1]
    const spyShowModal = jest.spyOn(app.$refs.ontologyEditModal, 'showModal')
    const wrapper = mountSheetTable({
      table: table,
      editStudyConfig: {
        nodes: [{ fields: [studyEditConfig.nodes[0].fields[1]] }]
      }
    })
    await waitAG(wrapper)
    await waitRAF()

    expect(wrapper.find('.sodar-ss-data').text()).toBe(value)
    await wrapper.find('.sodar-ss-data-cell').trigger('dblclick')
    expect(wrapper.find('.sodar-ss-data-cell-busy').exists()).toBe(true)
    expect(spyShowModal).toBeCalled()
    await gridOptions.api.stopEditing()
    expect(wrapper.find('.sodar-ss-data-cell-busy').exists()).toBe(false)
    expect(wrapper.find('.sodar-ss-data').text()).toBe(value)
  })
})
