import { createLocalVue, mount } from '@vue/test-utils'
import {
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

// Set up extended Vue constructor
const localVue = createLocalVue()
localVue.use(BootstrapVue)
localVue.use(VueClipboard)

// Init data
// let propsData

describe('IrodsButtonsRenderer.vue', () => {
  function mountSheetTable (params = {}) {
    const retParams = Object.assign({
      app: getAppStub(params),
      assayMode: true, // This renderer is only used in assay tables
      editMode: false,
      gridOptions: null,
      editStudyConfig: null
    }, params)
    retParams.gridOptions = initGridOptions(retParams.app, retParams.editMode)
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

  it('renders irods buttons for an assay table', async () => {
    const wrapper = mountSheetTable()
    await waitAG(wrapper)
    await waitRAF()
    await waitSelector(wrapper, '.sodar-ss-data-links-cell', 2)

    expect(wrapper.findAll('.sodar-ss-data-links-cell').length).toBe(2)
    expect(wrapper.findAll('.sodar-ss-irods-links').length).toBe(2)
  })

  // TODO: Fix nested components in tests (see issue #1034)
  // TODO: More tests once aforementioned issue has been fixed
})
