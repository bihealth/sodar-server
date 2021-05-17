import { createLocalVue, mount } from '@vue/test-utils'
import {
  projectUuid,
  studyUuid,
  assayUuid,
  copy,
  getAppStub,
  getSheetTablePropsData,
  waitNT,
  waitRAF
} from '../testUtils.js'
import { initGridOptions } from '@/utils/gridUtils.js'
import BootstrapVue from 'bootstrap-vue'
import VueClipboard from 'vue-clipboard2'
import SheetTable from '@/components/SheetTable.vue'
import ColumnToggleModal from '@/components/modals/ColumnToggleModal.vue'
import sodarContext from './data/sodarContext.json'
import studyTables from './data/studyTables.json'
import sheetEditConfigModified from './data/sheetEditConfigModified.json'

// Set up extended Vue constructor
const localVue = createLocalVue()
localVue.use(BootstrapVue)
localVue.use(VueClipboard)

// Init data
let propsData
let app
let gridOptions

describe('ColumnToggleModal.vue', () => {
  function getApp (params = {}) {
    const app = getAppStub(params)
    app.getGridOptionsByUuid = function () {
      return gridOptions
    }
    app.getStudyGridUuids = function (assayMode) {
      const ret = [assayUuid]
      if (!assayMode) ret.push(studyUuid)
      return ret
    }
    app.studyDisplayConfig = copy(studyTables.display_config)
    return app
  }

  function getPropsData (params = {}) {
    if (!params.app) params.app = getAppStub(params)
    if (!params.projectUuid) params.projectUuid = projectUuid
    if (!params.studyUuid) params.studyUuid = studyUuid
    return params
  }

  function mountSheetTable (propsDataParams = {}) {
    const params = Object.assign({
      app: app,
      editMode: false,
      gridOptions: gridOptions,
      editStudyConfig: null
    }, propsDataParams)
    return mount(SheetTable, {
      localVue, propsData: getSheetTablePropsData(params)
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
    propsData = { app: getApp() }
    gridOptions = initGridOptions(app, false) // editMode=false by default
  })

  /* Config rendering ------------------------------------------------------- */

  it('renders modal for study table', async () => {
    mountSheetTable()
    const wrapper = mount(ColumnToggleModal, {
      localVue, propsData: getPropsData(propsData)
    })
    wrapper.vm.showModal(studyUuid, false)
    await waitNT(wrapper.vm)
    await waitRAF()

    expect(wrapper.find('#sodar-ss-toggle-modal-content').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-toggle-save').exists()).toBe(true)
    expect(wrapper.findAll('.sodar-ss-toggle-node').length).toBe(3)
    expect(wrapper.findAll('.sodar-ss-toggle-field-info').length).toBe(0)
    const fields = wrapper.findAll('.sodar-ss-toggle-field-check')
    expect(fields.length).toBe(7)
    for (let i = 0; i < fields.length; i++) {
      expect(fields.at(i).props().checked).toBe(true)
    }
  })

  it('renders modal for assay table', async () => {
    mountSheetTable({ assayMode: true })
    const wrapper = mount(ColumnToggleModal, {
      localVue, propsData: getPropsData(propsData)
    })
    wrapper.vm.showModal(assayUuid, true)
    await waitNT(wrapper.vm)
    await waitRAF()

    expect(wrapper.find('#sodar-ss-toggle-modal-content').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-toggle-save').exists()).toBe(true)
    expect(wrapper.findAll('.sodar-ss-toggle-node').length).toBe(10)
    expect(wrapper.findAll('.sodar-ss-toggle-field-info').length).toBe(0)
    const fields = wrapper.findAll('.sodar-ss-toggle-field-check')
    expect(fields.length).toBe(8)
    for (let i = 0; i < fields.length - 1; i++) {
      expect(fields.at(i).props().checked).toBe(false)
    }
    // Process name is visible by default
    expect(fields.at(7).props().checked).toBe(true)
  })

  it('renders modal for study table in edit mode', async () => {
    const app = getApp({ editMode: true })
    mountSheetTable({
      app: app,
      editMode: true,
      editStudyConfig: copy(sheetEditConfigModified).studies[studyUuid]
    })
    const wrapper = mount(ColumnToggleModal, {
      localVue, propsData: getPropsData({ app: app })
    })
    wrapper.vm.showModal(studyUuid, false)
    await waitNT(wrapper.vm)
    await waitRAF()

    const fieldInfos = wrapper.findAll('.sodar-ss-toggle-field-info')
    expect(fieldInfos.length).toBe(7)
    for (let i = 0; i < fieldInfos.length; i++) {
      expect(fieldInfos.at(i).text()).toBe('Editable')
    }
  })

  it('renders modal for assay table in edit mode', async () => {
    const app = getApp({ editMode: true })
    mountSheetTable({
      app: app,
      assayMode: true,
      editMode: true,
      editStudyConfig: copy(sheetEditConfigModified).studies[studyUuid]
    })
    const wrapper = mount(ColumnToggleModal, {
      localVue, propsData: getPropsData({ app: app })
    })
    wrapper.vm.showModal(assayUuid, true)
    await waitNT(wrapper.vm)
    await waitRAF()

    const fieldInfos = wrapper.findAll('.sodar-ss-toggle-field-info')
    expect(fieldInfos.length).toBe(8)
    for (let i = 0; i < fieldInfos.length; i++) {
      expect(fieldInfos.at(i).text()).toBe('Editable')
    }
  })

  it('renders modal without edit sheet permission', async () => {
    const sc = copy(sodarContext)
    sc.perms.edit_sheet = false
    const app = getApp({ sodarContext: sc })
    mountSheetTable({ app: app })
    const wrapper = mount(ColumnToggleModal, {
      localVue, propsData: getPropsData({ app: app })
    })
    wrapper.vm.showModal(studyUuid, false)
    await waitNT(wrapper.vm)
    await waitRAF()

    expect(wrapper.find('#sodar-ss-toggle-modal-content').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-toggle-save').exists()).toBe(false)
  })

  it('calls onFilterInput() on filter input', async () => {
    mountSheetTable()
    const wrapper = mount(ColumnToggleModal, {
      localVue, propsData: getPropsData(propsData)
    })
    const spyOnFilterInput = jest.spyOn(wrapper.vm, 'onFilterInput')
    wrapper.vm.showModal(studyUuid, false)
    await waitNT(wrapper.vm)
    await waitRAF()

    await wrapper.find('#sodar-ss-toggle-filter').vm.$emit('input')
    expect(spyOnFilterInput).toBeCalled()
  })

  it('filters fields on onFilterInput()', async () => {
    mountSheetTable()
    const wrapper = mount(ColumnToggleModal, {
      localVue, propsData: getPropsData(propsData)
    })
    wrapper.vm.showModal(studyUuid, false)
    await waitNT(wrapper.vm)
    await waitRAF()

    await wrapper.vm.onFilterInput('treatment')
    const fields = wrapper.findAll('.sodar-ss-toggle-field')
    for (let i = 0; i < fields.length - 1; i++) {
      expect(fields.at(i).isVisible()).toBe(false)
    }
    expect(fields.at(6).isVisible()).toBe(true) // Treatment is true
  })

  it('calls onColumnChange() on column hide/show click', async () => {
    mountSheetTable()
    const wrapper = mount(ColumnToggleModal, {
      localVue, propsData: getPropsData(propsData)
    })
    const spyOnColumnChange = jest.spyOn(wrapper.vm, 'onColumnChange')
    wrapper.vm.showModal(studyUuid, false)
    await waitNT(wrapper.vm)
    await waitRAF()

    await wrapper.findAll('.sodar-ss-toggle-field-check').at(0).vm.$emit('change')
    expect(spyOnColumnChange).toBeCalled()
  })

  it('calls onGroupChange() on column group hide/show click', async () => {
    mountSheetTable()
    const wrapper = mount(ColumnToggleModal, {
      localVue, propsData: getPropsData(propsData)
    })
    const spyOnGroupChange = jest.spyOn(wrapper.vm, 'onGroupChange')
    wrapper.vm.showModal(studyUuid, false)
    await waitNT(wrapper.vm)
    await waitRAF()

    await wrapper.findAll('.sodar-ss-toggle-node-check').at(0).vm.$emit('change')
    expect(spyOnGroupChange).toBeCalled()
  })

  // TODO: Test field hiding/showing in sheetTable
  // TODO: Test node hiding/showing in sheetTable

  it('calls postUpdate() on modal hide after changes', async () => {
    mountSheetTable()
    const wrapper = mount(ColumnToggleModal, {
      localVue, propsData: getPropsData(propsData)
    })
    const spyOnPostUpdate = jest.spyOn(
      wrapper.vm, 'postUpdate').mockImplementation(jest.fn())
    wrapper.vm.showModal(studyUuid, false)
    await waitNT(wrapper.vm)
    await waitRAF()

    await wrapper.findAll('.sodar-ss-toggle-field-check').at(0).vm.$emit('change')
    await wrapper.vm.onModalHide()
    expect(spyOnPostUpdate).toBeCalled()
  })

  it('does not call postUpdate() on modal hide with no changes', async () => {
    mountSheetTable()
    const wrapper = mount(ColumnToggleModal, {
      localVue, propsData: getPropsData(propsData)
    })
    const spyOnPostUpdate = jest.spyOn(
      wrapper.vm, 'postUpdate').mockImplementation(jest.fn())
    wrapper.vm.showModal(studyUuid, false)
    await waitNT(wrapper.vm)
    await waitRAF()

    await wrapper.vm.onModalHide()
    expect(spyOnPostUpdate).not.toBeCalled()
  })

  it('does not call postUpdate() on modal hide if anonymous user', async () => {
    propsData.app.sodarContext.user_uuid = null
    mountSheetTable()
    const wrapper = mount(ColumnToggleModal, {
      localVue, propsData: getPropsData(propsData)
    })
    const spyOnPostUpdate = jest.spyOn(
      wrapper.vm, 'postUpdate').mockImplementation(jest.fn())
    wrapper.vm.showModal(studyUuid, false)
    await waitNT(wrapper.vm)
    await waitRAF()

    await wrapper.findAll('.sodar-ss-toggle-field-check').at(0).vm.$emit('change')
    await wrapper.vm.onModalHide()
    expect(spyOnPostUpdate).not.toBeCalled()
  })
})
