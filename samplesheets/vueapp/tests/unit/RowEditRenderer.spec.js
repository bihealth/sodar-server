import { createLocalVue, mount } from '@vue/test-utils'
import {
  studyUuid,
  assayUuid,
  copy,
  getAppStub,
  getSheetTableComponents,
  getSheetTablePropsData,
  // waitNT,
  waitRAF,
  waitAG,
  waitSelector
} from '../testUtils.js'
import { initGridOptions } from '@/utils/gridUtils.js'
import BootstrapVue from 'bootstrap-vue'
import VueClipboard from 'vue-clipboard2'
import SheetTable from '@/components/SheetTable.vue'
import studyTablesEdit from './data/studyTablesEdit.json'
import sheetEditConfigModified from './data/sheetEditConfigModified.json'

// Set up extended Vue constructor
const localVue = createLocalVue()
localVue.use(BootstrapVue)
localVue.use(VueClipboard)

// Init data
// let propsData
let app
let gridOptions

describe('RowEditRenderer.vue', () => {
  function getApp () {
    const app = getAppStub({
      editMode: true,
      editContext: copy(studyTablesEdit.edit_context)
    })
    app.getGridOptionsByUuid = function () {
      return gridOptions
    }
    app.getStudyGridUuids = function (assayMode) {
      const ret = [assayUuid]
      if (!assayMode) ret.push(studyUuid)
      return ret
    }
    return app
  }

  function mountSheetTable (propsDataParams = {}, editStudyConfig = null) {
    const params = Object.assign({
      app: app,
      editMode: true,
      gridOptions: gridOptions,
      editStudyConfig: editStudyConfig ||
        copy(sheetEditConfigModified).studies[studyUuid]
    }, propsDataParams)
    return mount(SheetTable, {
      localVue,
      propsData: getSheetTablePropsData(params),
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
    app = getApp()
    gridOptions = initGridOptions(app, true) // editMode=true by default
  })

  it('renders study table row edit cells', async () => {
    const wrapper = mountSheetTable()
    await waitAG(wrapper)
    await waitRAF()
    await waitSelector(wrapper, '.sodar-ss-row-edit-buttons', 5)

    const buttonGroups = wrapper.findAll('.sodar-ss-row-edit-buttons')
    expect(buttonGroups.length).toBe(5)
    expect(wrapper.findAll('.sodar-ss-row-delete-btn').length).toBe(5)
    expect(wrapper.findAll('.sodar-ss-row-save-btn').length).toBe(0)
    for (let i = 0; i < buttonGroups.length; i++) {
      let disabled
      if (i === 1 || i === 2) disabled = 'true' // Samples 0815* used in assay
      expect(buttonGroups.at(i).find(
        '.sodar-ss-row-delete-btn').attributes().disabled).toBe(disabled)
    }
  })

  it('renders assay table row edit cells', async () => {
    const wrapper = mountSheetTable({ assayMode: true })
    await waitAG(wrapper)
    await waitRAF()
    await waitSelector(wrapper, '.sodar-ss-row-edit-buttons', 2)

    const buttonGroups = wrapper.findAll('.sodar-ss-row-edit-buttons')
    expect(buttonGroups.length).toBe(2)
    expect(wrapper.findAll('.sodar-ss-row-delete-btn').length).toBe(2)
    expect(wrapper.findAll('.sodar-ss-row-save-btn').length).toBe(0)
    for (let i = 0; i < buttonGroups.length; i++) {
      expect(buttonGroups.at(i).find(
        '.sodar-ss-row-delete-btn').attributes().disabled).toBe(undefined)
    }
  })

  // TODO: Test button status updating and event handling once edit helpers
  // TODO: have been refactored (see #747)
})
