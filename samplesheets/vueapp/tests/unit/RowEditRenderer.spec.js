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
import {
  rowDeleteMsgAll,
  rowDeleteMsgAssay,
  rowDeleteMsgCancel,
  rowDeleteMsgOk,
  rowDeleteMsgUnsaved
} from '@/components/renderers/RowEditRenderer.vue'
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
      let title = rowDeleteMsgOk
      if (i === 1 || i === 2) { // Samples 0815* used in assay
        disabled = 'true'
        title = rowDeleteMsgAssay
      }
      expect(buttonGroups.at(i).find(
        '.sodar-ss-row-delete-btn').attributes().disabled).toBe(disabled)
      expect(buttonGroups.at(i).find(
        '.sodar-ss-row-delete-btn').attributes().title).toBe(title)
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
      expect(buttonGroups.at(i).find(
        '.sodar-ss-row-delete-btn').attributes().title).toBe(rowDeleteMsgOk)
    }
  })

  it('renders row edit cells with unsaved row', async () => {
    app.unsavedRow = {
      gridUuid: '33333333-3333-3333-3333-333333333333',
      rowId: 'row170'
    }
    const wrapper = mountSheetTable()
    await waitAG(wrapper)
    await waitRAF()
    await waitSelector(wrapper, '.sodar-ss-row-edit-buttons', 5)

    const buttonGroups = wrapper.findAll('.sodar-ss-row-edit-buttons')
    for (let i = 0; i < buttonGroups.length; i++) {
      expect(buttonGroups.at(i).find(
        '.sodar-ss-row-delete-btn').attributes().disabled).toBe('true')
      expect(buttonGroups.at(i).find(
        '.sodar-ss-row-delete-btn').attributes().title).toBe(rowDeleteMsgUnsaved)
    }
  })

  it('renders row edit cells with single row in table', async () => {
    // Update assay table data to only contain the first row
    const singleRowTable = copy(studyTablesEdit).tables.assays[assayUuid]
    singleRowTable.table_data = [singleRowTable.table_data[0]]
    const wrapper = mountSheetTable({ assayMode: true, table: singleRowTable })
    await waitAG(wrapper)
    await waitRAF()
    await waitSelector(wrapper, '.sodar-ss-row-edit-buttons', 1)

    const buttonGroup = wrapper.find('.sodar-ss-row-edit-buttons')
    expect(buttonGroup.find(
      '.sodar-ss-row-delete-btn').attributes().disabled).toBe('true')
    expect(buttonGroup.find(
      '.sodar-ss-row-delete-btn').attributes().title).toBe(rowDeleteMsgAll)
  })

  it('renders row edit cells with new row', async () => {
    app.unsavedRow = { gridUuid: studyUuid, id: '4' }
    const wrapper = mountSheetTable()
    await waitAG(wrapper)
    await waitRAF()
    await waitSelector(wrapper, '.sodar-ss-row-edit-buttons', 5)

    const buttonGroups = wrapper.findAll('.sodar-ss-row-edit-buttons')
    expect(buttonGroups.at(4).find(
      '.sodar-ss-row-delete-btn').attributes().disabled).toBe(undefined)
    expect(buttonGroups.at(4).find(
      '.sodar-ss-row-delete-btn').attributes().title).toBe(rowDeleteMsgCancel)
  })

  // TODO: Test button status updating and event handling once edit helpers
  //       have been refactored (see #747)
})
