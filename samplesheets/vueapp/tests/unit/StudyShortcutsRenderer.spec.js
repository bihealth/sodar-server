import { createLocalVue, mount } from '@vue/test-utils'
import {
  copy,
  getAppStub,
  getSheetTablePropsData,
  waitRAF,
  waitAG,
  waitSelector
} from '../testUtils.js'
import { initGridOptions } from '@/utils/gridUtils.js'
import BootstrapVue from 'bootstrap-vue'
import VueClipboard from 'vue-clipboard2'
import SheetTable from '@/components/SheetTable.vue'
import studyTables from './data/studyTables.json'
import studyShortcutsGermline from './data/studyShortcutsGermline.json'

// Set up extended Vue constructor
const localVue = createLocalVue()
localVue.use(BootstrapVue)
localVue.use(VueClipboard)

// Init data
// let propsData

describe('StudyShortcutsRenderer.vue', () => {
  function mountSheetTable (params = {}) {
    const app = getAppStub(params)
    app.sodarContext.configuration = 'bih_germline'
    const table = copy(studyTables).tables.study
    table.shortcuts = copy(studyShortcutsGermline)
    const retParams = Object.assign({
      app: app,
      assayMode: false, // This renderer is only used in study tables
      editMode: false,
      gridOptions: initGridOptions(app, false),
      editStudyConfig: null,
      table: table
    }, params)
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

  it('renders study shortucts for a study table', async () => {
    const wrapper = mountSheetTable()
    await waitAG(wrapper)
    await waitRAF()
    await waitSelector(wrapper, '.sodar-ss-data-links-cell', 5)

    expect(wrapper.findAll('.sodar-ss-data-links-cell').length).toBe(5)
    expect(wrapper.findAll('.sodar-ss-study-shortcuts').length).toBe(5)
  })

  // TODO: Fix nested components in tests (see issue #1034)
  // TODO: More tests once aforementioned issue has been fixed
})
