import { createLocalVue, mount } from '@vue/test-utils'
import {
  projectUuid,
  studyUuid,
  assayUuid,
  copy,
  getAppStub,
  // getColDefParams,
  // getRowDataParams,
  getSheetTablePropsData,
  waitNT,
  waitRAF
} from '../testUtils.js'
import { initGridOptions } from '@/utils/gridUtils.js'
import BootstrapVue from 'bootstrap-vue'
import VueClipboard from 'vue-clipboard2'
import SheetTable from '@/components/SheetTable.vue'
import ColumnConfigModal from '@/components/modals/ColumnConfigModal.vue'
import studyTablesEdit from './data/studyTablesEdit.json'
import sheetEditConfigModified from './data/sheetEditConfigModified.json'
import sheetEditConfigNew from './data/sheetEditConfigNew.json'

// Set up extended Vue constructor
const localVue = createLocalVue()
localVue.use(BootstrapVue)
localVue.use(VueClipboard)

// Init data
// let propsData
let app
let gridOptions
const studyNodeLen = 3

// TODO: Better way to set up grid than mounting an entire SheetTable comp?

describe('ColumnConfigModal.vue', () => {
  function getApp () {
    const app = getAppStub({ editContext: copy(studyTablesEdit.edit_context) })
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

  function getPropsData (params = {}) {
    if (!params.app) params.app = getAppStub(params)
    if (!params.projectUuid) params.projectUuid = projectUuid
    if (!params.studyUuid) params.studyUuid = studyUuid
    return params
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
      localVue, propsData: getSheetTablePropsData(params)
    })
  }

  function getShowModalParams (
    colId, params = {}, assayMode = false, sheetEditConfig = null
  ) {
    if (!sheetEditConfig) sheetEditConfig = copy(sheetEditConfigModified)
    let aUuid = null
    let config
    let configNodeIdx = params.configNodeIdx
    if (!assayMode || configNodeIdx < studyNodeLen) {
      config = sheetEditConfig.studies[studyUuid]
    } else {
      aUuid = assayUuid
      config = sheetEditConfig.studies[studyUuid].assays[aUuid]
      configNodeIdx -= studyNodeLen
    }
    const ret = Object.assign({
      col: gridOptions.columnApi.getColumn(colId),
      fieldConfig: config.nodes[configNodeIdx].fields[params.configFieldIdx],
      newConfig: params.newConfig || false,
      colType: null,
      fieldDisplayName: null,
      assayUuid: aUuid,
      configNodeIdx: configNodeIdx,
      configFieldIdx: params.configFieldIdx
    }, params)
    if (!('editable' in ret.fieldConfig)) ret.fieldConfig.editable = false
    if (!('range' in ret.fieldConfig)) ret.fieldConfig.range = [null, null]
    if (!('regex' in ret.fieldConfig)) ret.fieldConfig.regex = ''
    ret.fieldDisplayName = ret.fieldConfig.name
    return ret
  }

  function mockPostUpdate () {
    return { json: function () { return { message: 'ok' } } }
  }

  beforeAll(() => {
    // TODO: Why do we get bootstrap-vue errors?
    // TODO: See https://stackoverflow.com/questions/51536537/running-jest-with-bootstrap-vue
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

  /* Config rendering ------------------------------------------------------- */

  it('renders modal with source name config', async () => {
    mountSheetTable()
    const wrapper = mount(ColumnConfigModal, {
      localVue, propsData: getPropsData({ app: app })
    })
    wrapper.vm.showModal(getShowModalParams('col0', {
      colType: 'NAME',
      configNodeIdx: 0,
      configFieldIdx: 0
    }))
    await waitNT(wrapper.vm)
    await waitRAF()

    expect(wrapper.find('#sodar-ss-col-btn-copy').attributes().disabled).toBe('disabled')
    expect(wrapper.find('#sodar-ss-col-input-paste').attributes().disabled).toBe('disabled')
    expect(wrapper.vm.fieldConfig.editable).toBe(true)
    expect(wrapper.find('#sodar-ss-col-content').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-col-table-name').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-col-tr-name-suffix').exists()).toBe(false) // No name suffix for source
  })

  it('renders modal with ontology config', async () => {
    mountSheetTable()
    const wrapper = mount(ColumnConfigModal, {
      localVue, propsData: getPropsData({ app: app })
    })
    wrapper.vm.showModal(getShowModalParams('col1', {
      colType: 'ONTOLOGY',
      configNodeIdx: 0,
      configFieldIdx: 1
    }))
    await waitNT(wrapper.vm)
    await waitRAF()

    expect(wrapper.find('#sodar-ss-col-btn-copy').attributes().disabled).toBe(undefined)
    expect(wrapper.find('#sodar-ss-col-input-paste').attributes().disabled).toBe(undefined)
    expect(wrapper.vm.fieldConfig.editable).toBe(true)
    expect(wrapper.find('#sodar-ss-col-table-ontology').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-col-td-allow-list').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-col-post-ontology').exists()).toBe(true)
  })

  it('renders modal with integer and unit config', async () => {
    mountSheetTable()
    const wrapper = mount(ColumnConfigModal, {
      localVue, propsData: getPropsData({ app: app })
    })
    wrapper.vm.showModal(getShowModalParams('col2', {
      colType: 'UNIT',
      configNodeIdx: 0,
      configFieldIdx: 2
    }))
    await waitNT(wrapper.vm)
    await waitRAF()

    expect(wrapper.find('#sodar-ss-col-btn-copy').attributes().disabled).toBe(undefined)
    expect(wrapper.find('#sodar-ss-col-input-paste').attributes().disabled).toBe(undefined)
    expect(wrapper.vm.fieldConfig.editable).toBe(true)
    expect(wrapper.find('#sodar-ss-col-td-allow-list').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-col-table-basic').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-col-tr-format').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-col-tr-select').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-col-tr-range').exists()).toBe(true)
    expect(wrapper.vm.fieldConfig.range).toEqual(['0', '150'])
    expect(wrapper.find('#sodar-ss-col-tr-regex').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-col-input-default').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-col-select-default').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-col-tr-unit').exists()).toBe(true)
    expect(wrapper.vm.unitOptions).toBe('day\nyear')
    expect(wrapper.find('#sodar-ss-col-tr-unit-default').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-col-tr-unit-default').findAll(
      'option').length).toBe(3)
  })

  it('renders modal with protocol config', async () => {
    mountSheetTable()
    const wrapper = mount(ColumnConfigModal, {
      localVue, propsData: getPropsData({ app: app })
    })
    wrapper.vm.showModal(getShowModalParams('col3', {
      colType: 'PROTOCOL',
      configNodeIdx: 1,
      configFieldIdx: 0
    }))
    await waitNT(wrapper.vm)
    await waitRAF()

    expect(wrapper.find('#sodar-ss-col-btn-copy').attributes().disabled).toBe('disabled')
    expect(wrapper.find('#sodar-ss-col-input-paste').attributes().disabled).toBe('disabled')
    expect(wrapper.vm.fieldConfig.editable).toBe(true)
    expect(wrapper.find('#sodar-ss-col-td-allow-list').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-col-table-protocol').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-col-select-default').exists()).toBe(true)
    const options = wrapper.find(
      '#sodar-ss-col-select-default').findAll('option')
    for (let i = 1; i < options.length; i++) {
      expect(options.at(i).attributes().value).toBe(
        app.editContext.protocols[i - 1].uuid)
      expect(options.at(i).text()).toBe(app.editContext.protocols[i - 1].name)
    }
  })

  it('renders modal with null/string config', async () => {
    mountSheetTable()
    const wrapper = mount(ColumnConfigModal, {
      localVue, propsData: getPropsData({ app: app })
    })
    wrapper.vm.showModal(getShowModalParams('col4', {
      colType: null,
      configNodeIdx: 1,
      configFieldIdx: 1
    }))
    await waitNT(wrapper.vm)
    await waitRAF()

    expect(wrapper.find('#sodar-ss-col-btn-copy').attributes().disabled).toBe(undefined)
    expect(wrapper.find('#sodar-ss-col-input-paste').attributes().disabled).toBe(undefined)
    expect(wrapper.vm.fieldConfig.editable).toBe(true)
    expect(wrapper.find('#sodar-ss-col-td-allow-list').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-col-table-basic').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-col-tr-format').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-col-tr-select').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-col-tr-range').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-col-tr-regex').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-col-input-default').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-col-select-default').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-col-tr-unit').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-col-tr-unit-default').exists()).toBe(false)
  })

  it('renders modal with contact config', async () => {
    mountSheetTable()
    const wrapper = mount(ColumnConfigModal, {
      localVue, propsData: getPropsData({ app: app })
    })
    wrapper.vm.showModal(getShowModalParams('col5', {
      colType: 'CONTACT',
      configNodeIdx: 1,
      configFieldIdx: 2
    }))
    await waitNT(wrapper.vm)
    await waitRAF()

    expect(wrapper.find('#sodar-ss-col-btn-copy').attributes().disabled).toBe(undefined)
    expect(wrapper.find('#sodar-ss-col-input-paste').attributes().disabled).toBe(undefined)
    expect(wrapper.vm.fieldConfig.editable).toBe(true)
    expect(wrapper.find('#sodar-ss-col-td-allow-list').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-col-table-contact').exists()).toBe(true)
  })

  it('renders modal with date config', async () => {
    mountSheetTable()
    const wrapper = mount(ColumnConfigModal, {
      localVue, propsData: getPropsData({ app: app })
    })
    wrapper.vm.showModal(getShowModalParams('col6', {
      colType: 'DATE',
      configNodeIdx: 1,
      configFieldIdx: 3
    }))
    await waitNT(wrapper.vm)
    await waitRAF()

    expect(wrapper.find('#sodar-ss-col-btn-copy').attributes().disabled).toBe(undefined)
    expect(wrapper.find('#sodar-ss-col-input-paste').attributes().disabled).toBe(undefined)
    expect(wrapper.vm.fieldConfig.editable).toBe(true)
    expect(wrapper.find('#sodar-ss-col-td-allow-list').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-col-table-date').exists()).toBe(true)
  })

  it('renders modal with sample name config', async () => {
    mountSheetTable()
    const wrapper = mount(ColumnConfigModal, {
      localVue, propsData: getPropsData({ app: app })
    })
    wrapper.vm.showModal(getShowModalParams('col7', {
      colType: 'NAME',
      configNodeIdx: 2,
      configFieldIdx: 0
    }))
    await waitNT(wrapper.vm)
    await waitRAF()

    expect(wrapper.find('#sodar-ss-col-btn-copy').attributes().disabled).toBe('disabled')
    expect(wrapper.find('#sodar-ss-col-input-paste').attributes().disabled).toBe('disabled')
    expect(wrapper.vm.fieldConfig.editable).toBe(true)
    expect(wrapper.find('#sodar-ss-col-table-name').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-col-tr-name-suffix').exists()).toBe(true)
    expect(wrapper.vm.fieldConfig.default).toBe('-N1')
  })

  it('renders modal with integer config without unit', async () => {
    mountSheetTable()
    const wrapper = mount(ColumnConfigModal, {
      localVue, propsData: getPropsData({ app: app })
    })
    wrapper.vm.showModal(getShowModalParams('col8', {
      colType: null,
      configNodeIdx: 2,
      configFieldIdx: 1
    }))
    await waitNT(wrapper.vm)
    await waitRAF()

    expect(wrapper.find('#sodar-ss-col-btn-copy').attributes().disabled).toBe(undefined)
    expect(wrapper.find('#sodar-ss-col-input-paste').attributes().disabled).toBe(undefined)
    expect(wrapper.vm.fieldConfig.editable).toBe(true)
    expect(wrapper.find('#sodar-ss-col-td-allow-list').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-col-table-basic').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-col-tr-format').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-col-tr-select').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-col-tr-range').exists()).toBe(true)
    expect(wrapper.vm.fieldConfig.range).toEqual(['0', '2'])
    expect(wrapper.find('#sodar-ss-col-tr-regex').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-col-input-default').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-col-select-default').exists()).toBe(false)
    expect(wrapper.vm.fieldConfig.default).toBe('0')
    expect(wrapper.find('#sodar-ss-col-tr-unit').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-col-tr-unit-default').exists()).toBe(false)
  })

  it('renders modal with select config', async () => {
    mountSheetTable()
    const wrapper = mount(ColumnConfigModal, {
      localVue, propsData: getPropsData({ app: app })
    })
    wrapper.vm.showModal(getShowModalParams('col9', {
      colType: null,
      configNodeIdx: 2,
      configFieldIdx: 2
    }))
    await waitNT(wrapper.vm)
    await waitRAF()

    expect(wrapper.find('#sodar-ss-col-btn-copy').attributes().disabled).toBe(undefined)
    expect(wrapper.find('#sodar-ss-col-input-paste').attributes().disabled).toBe(undefined)
    expect(wrapper.vm.fieldConfig.editable).toBe(true)
    expect(wrapper.find('#sodar-ss-col-td-allow-list').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-col-table-basic').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-col-tr-format').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-col-tr-select').exists()).toBe(true)
    expect(wrapper.vm.valueOptions).toBe('yes\nno')
    expect(wrapper.find('#sodar-ss-col-tr-range').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-col-tr-regex').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-col-input-default').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-col-select-default').exists()).toBe(true)
    expect(wrapper.vm.fieldConfig.default).toBe('')
    expect(wrapper.find('#sodar-ss-col-tr-unit').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-col-tr-unit-default').exists()).toBe(false)
  })

  it('renders modal with source name config in assay table', async () => {
    mountSheetTable({ assayMode: true })
    const wrapper = mount(ColumnConfigModal, {
      localVue, propsData: getPropsData({ app: app })
    })
    wrapper.vm.showModal(getShowModalParams('col0', {
      colType: 'NAME',
      configNodeIdx: 0,
      configFieldIdx: 0
    }, true))
    await waitNT(wrapper.vm)
    await waitRAF()

    expect(wrapper.vm.fieldConfig.editable).toBe(true)
    expect(wrapper.find('#sodar-ss-col-content').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-col-table-name').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-col-tr-name-suffix').exists()).toBe(false)
  })

  it('renders modal with material name config in assay table', async () => {
    mountSheetTable({ assayMode: true })
    const wrapper = mount(ColumnConfigModal, {
      localVue, propsData: getPropsData({ app: app })
    })
    wrapper.vm.showModal(getShowModalParams('col11', {
      colType: 'NAME',
      configNodeIdx: 4, // NOTE: Add in study columns
      configFieldIdx: 0
    }, true))
    await waitNT(wrapper.vm)
    await waitRAF()

    expect(wrapper.vm.fieldConfig.editable).toBe(true)
    expect(wrapper.find('#sodar-ss-col-table-name').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-col-tr-name-suffix').exists()).toBe(true)
    expect(wrapper.vm.fieldConfig.default).toBe('-N1-DNA1')
  })

  it('renders modal with process name config in assay table', async () => {
    mountSheetTable({ assayMode: true })
    const wrapper = mount(ColumnConfigModal, {
      localVue, propsData: getPropsData({ app: app })
    })
    wrapper.vm.showModal(getShowModalParams('col13', {
      colType: 'NAME',
      configNodeIdx: 5, // NOTE: Add in study columns
      configFieldIdx: 1
    }, true))
    await waitNT(wrapper.vm)
    await waitRAF()

    expect(wrapper.vm.fieldConfig.editable).toBe(true)
    expect(wrapper.find('#sodar-ss-col-table-name').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-col-tr-name-suffix').exists()).toBe(true)
    expect(wrapper.vm.fieldConfig.default).toBe('-N1-DNA1-WES1')
  })

  it('renders modal with data file name config in assay table', async () => {
    mountSheetTable({ assayMode: true })
    const wrapper = mount(ColumnConfigModal, {
      localVue, propsData: getPropsData({ app: app })
    })
    wrapper.vm.showModal(getShowModalParams('col14', {
      colType: 'LINK_FILE',
      configNodeIdx: 6, // NOTE: Add in study columns
      configFieldIdx: 0
    }, true))
    await waitNT(wrapper.vm)
    await waitRAF()

    expect(wrapper.vm.fieldConfig.editable).toBe(true)
    expect(wrapper.find('#sodar-ss-col-table-name').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-col-tr-name-suffix').exists()).toBe(false)
  })

  // TODO: Test extract label
  // TODO: Test EXTERNAL_LINKS

  it('renders modal with new source name config', async () => {
    const newConfig = copy(sheetEditConfigNew)
    mountSheetTable({}, newConfig.studies[studyUuid])
    const wrapper = mount(ColumnConfigModal, {
      localVue, propsData: getPropsData({ app: app })
    })
    wrapper.vm.showModal(
      getShowModalParams('col0', {
        colType: 'NAME',
        configNodeIdx: 0,
        configFieldIdx: 0,
        newConfig: true
      }, false, newConfig))
    await waitNT(wrapper.vm)
    await waitRAF()

    expect(wrapper.vm.fieldConfig.editable).toBe(false)
    expect(wrapper.find('#sodar-ss-col-content').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-col-table-name').exists()).toBe(true)
  })

  it('renders modal with new ontology config', async () => {
    const newConfig = copy(sheetEditConfigNew)
    mountSheetTable({}, newConfig.studies[studyUuid])
    const wrapper = mount(ColumnConfigModal, {
      localVue, propsData: getPropsData({ app: app })
    })
    wrapper.vm.showModal(
      getShowModalParams('col1', {
        colType: 'ONTOLOGY',
        configNodeIdx: 0,
        configFieldIdx: 1,
        newConfig: true
      }, false, newConfig))
    await waitNT(wrapper.vm)
    await waitRAF()

    expect(wrapper.vm.fieldConfig.editable).toBe(false)
    expect(wrapper.vm.fieldConfig.allow_list).toBe(false)
    expect(wrapper.find('#sodar-ss-col-table-ontology').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-col-td-allow-list').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-col-post-ontology').exists()).toBe(true)
    expect(wrapper.find('.sodar-ss-col-tr-ontology-enabled').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-col-ontology-select-insert').exists()).toBe(true)
  })

  // TODO: Test newConfig with HPO/OMIM/ORDO and EXTERNAL_LINKS

  /* Config updating -------------------------------------------------------- */

  it('changes from select to string config', async () => {
    mountSheetTable()
    const wrapper = mount(ColumnConfigModal, {
      localVue,
      propsData: getPropsData({ app: app }),
      methods: { postUpdate: mockPostUpdate }
    })
    const spyPostUpdate = jest.spyOn(wrapper.vm, 'postUpdate')
    const spyHandleUpdate = jest.spyOn(wrapper.vm, 'handleUpdate')
    wrapper.vm.showModal(getShowModalParams('col9', {
      colType: null,
      configNodeIdx: 2,
      configFieldIdx: 2
    }))
    await waitNT(wrapper.vm)
    await waitRAF()

    const fieldConfig = copy(wrapper.vm.fieldConfig)
    fieldConfig.format = 'string'
    await wrapper.setData({ fieldConfig: fieldConfig })
    wrapper.vm.onFormatChange() // TODO: How to get around manual triggering?

    expect(wrapper.vm.fieldConfig.editable).toBe(true)
    expect(wrapper.find('#sodar-ss-col-tr-select').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-col-tr-range').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-col-tr-regex').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-col-input-default').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-col-select-default').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-col-tr-unit').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-col-tr-unit-default').exists()).toBe(false)
    expect(wrapper.vm.$refs.updateBtn.disabled).toBe(false)

    await wrapper.find('#sodar-ss-col-btn-update').trigger('click')
    await waitNT(wrapper.vm)
    delete fieldConfig.options
    delete fieldConfig.range
    const upData = {
      fields: [{
        action: 'update',
        study: studyUuid,
        assay: null,
        node_idx: 2,
        field_idx: 2,
        config: fieldConfig
      }]
    }
    expect(spyPostUpdate).toBeCalledWith(upData)
    await waitNT(wrapper.vm)
    expect(spyHandleUpdate).toBeCalled()
  })

  it('changes from select to integer config', async () => {
    mountSheetTable()
    const wrapper = mount(ColumnConfigModal, {
      localVue,
      propsData: getPropsData({ app: app }),
      methods: { postUpdate: mockPostUpdate }
    })
    const spyPostUpdate = jest.spyOn(wrapper.vm, 'postUpdate')
    const spyHandleUpdate = jest.spyOn(wrapper.vm, 'handleUpdate')
    wrapper.vm.showModal(getShowModalParams('col9', {
      colType: null,
      configNodeIdx: 2,
      configFieldIdx: 2
    }))
    await waitNT(wrapper.vm)
    await waitRAF()

    const fieldConfig = copy(wrapper.vm.fieldConfig)
    fieldConfig.format = 'integer'
    await wrapper.setData({ fieldConfig: fieldConfig })
    wrapper.vm.onFormatChange()

    expect(wrapper.vm.fieldConfig.editable).toBe(true)
    expect(wrapper.find('#sodar-ss-col-tr-select').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-col-tr-range').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-col-tr-regex').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-col-input-default').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-col-select-default').exists()).toBe(false)
    // NOTE: No unit for this column due to ISAtab
    expect(wrapper.find('#sodar-ss-col-tr-unit').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-col-tr-unit-default').exists()).toBe(false)
    expect(wrapper.vm.$refs.updateBtn.disabled).toBe(false)

    await wrapper.find('#sodar-ss-col-btn-update').trigger('click')
    await waitNT(wrapper.vm)
    delete fieldConfig.options
    const upData = {
      fields: [{
        action: 'update',
        study: studyUuid,
        assay: null,
        node_idx: 2,
        field_idx: 2,
        config: fieldConfig
      }]
    }
    expect(spyPostUpdate).toBeCalledWith(upData)
    await waitNT(wrapper.vm)
    expect(spyHandleUpdate).toBeCalled()
  })

  it('changes from integer to select config', async () => {
    mountSheetTable()
    const wrapper = mount(ColumnConfigModal, {
      localVue,
      propsData: getPropsData({ app: app }),
      methods: { postUpdate: mockPostUpdate }
    })
    wrapper.vm.showModal(getShowModalParams('col8', {
      colType: null,
      configNodeIdx: 2,
      configFieldIdx: 1
    }))
    await waitNT(wrapper.vm)
    await waitRAF()

    const fieldConfig = copy(wrapper.vm.fieldConfig)
    fieldConfig.format = 'select'
    await wrapper.setData({ fieldConfig: fieldConfig })
    wrapper.vm.onFormatChange()

    expect(wrapper.vm.fieldConfig.editable).toBe(true)
    expect(wrapper.find('#sodar-ss-col-tr-select').exists()).toBe(true)
    expect(wrapper.vm.valueOptions).toBe('')
    expect(wrapper.find('#sodar-ss-col-tr-range').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-col-tr-regex').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-col-input-default').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-col-select-default').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-col-tr-unit').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-col-tr-unit-default').exists()).toBe(false)
    // Update should be disabled as there are no choices
    expect(wrapper.vm.$refs.updateBtn.disabled).toBe(true)
  })

  /* Validation ------------------------------------------------------------- */

  it('validates minimum range', async () => {
    mountSheetTable()
    const wrapper = mount(ColumnConfigModal, {
      localVue, propsData: getPropsData({ app: app })
    })
    wrapper.vm.showModal(getShowModalParams('col2', {
      colType: 'UNIT',
      configNodeIdx: 0,
      configFieldIdx: 2
    }))
    await waitNT(wrapper.vm)
    await waitRAF()

    expect(wrapper.vm.fieldConfig.range).toEqual(['0', '150'])
    expect(wrapper.vm.formClasses.range).not.toContain('text-danger')
    expect(wrapper.vm.$refs.updateBtn.disabled).toBe(false)

    const fieldConfig = copy(wrapper.vm.fieldConfig)
    fieldConfig.range[0] = '151'
    await wrapper.setData({ fieldConfig: fieldConfig })
    await wrapper.find('#sodar-ss-col-input-range-min').vm.$emit('input')
    expect(wrapper.vm.formClasses.range).toContain('text-danger')
    expect(wrapper.vm.$refs.updateBtn.disabled).toBe(true)

    fieldConfig.range[0] = '149'
    await wrapper.setData({ fieldConfig: fieldConfig })
    await wrapper.find('#sodar-ss-col-input-range-min').vm.$emit('input')
    expect(wrapper.vm.formClasses.range).not.toContain('text-danger')
    expect(wrapper.vm.$refs.updateBtn.disabled).toBe(false)
  })

  it('validates maximum range', async () => {
    mountSheetTable()
    const wrapper = mount(ColumnConfigModal, {
      localVue, propsData: getPropsData({ app: app })
    })
    wrapper.vm.showModal(getShowModalParams('col2', {
      colType: 'UNIT',
      configNodeIdx: 0,
      configFieldIdx: 2
    }))
    await waitNT(wrapper.vm)
    await waitRAF()

    expect(wrapper.vm.fieldConfig.range).toEqual(['0', '150'])
    expect(wrapper.vm.formClasses.default).not.toContain('text-danger')
    expect(wrapper.vm.$refs.updateBtn.disabled).toBe(false)

    const fieldConfig = copy(wrapper.vm.fieldConfig)
    fieldConfig.range[1] = '0'
    await wrapper.setData({ fieldConfig: fieldConfig })
    await wrapper.find('#sodar-ss-col-input-range-min').vm.$emit('input')
    expect(wrapper.vm.formClasses.range).toContain('text-danger')
    expect(wrapper.vm.$refs.updateBtn.disabled).toBe(true)

    fieldConfig.range[1] = '1'
    await wrapper.setData({ fieldConfig: fieldConfig })
    await wrapper.find('#sodar-ss-col-input-range-min').vm.$emit('input')
    expect(wrapper.vm.formClasses.range).not.toContain('text-danger')
    expect(wrapper.vm.$refs.updateBtn.disabled).toBe(false)
  })

  it('validates default value against range', async () => {
    mountSheetTable()
    const wrapper = mount(ColumnConfigModal, {
      localVue, propsData: getPropsData({ app: app })
    })
    wrapper.vm.showModal(getShowModalParams('col2', {
      colType: 'UNIT',
      configNodeIdx: 0,
      configFieldIdx: 2
    }))
    await waitNT(wrapper.vm)
    await waitRAF()

    expect(wrapper.vm.fieldConfig.range).toEqual(['0', '150'])
    expect(wrapper.vm.fieldConfig.default).toBe('')
    expect(wrapper.vm.formClasses.default).not.toContain('text-danger')
    expect(wrapper.vm.$refs.updateBtn.disabled).toBe(false)

    const fieldConfig = copy(wrapper.vm.fieldConfig)
    fieldConfig.default = '151'
    await wrapper.setData({ fieldConfig: fieldConfig })
    await wrapper.find('#sodar-ss-col-input-range-min').vm.$emit('input')
    expect(wrapper.vm.formClasses.default).toContain('text-danger')
    expect(wrapper.vm.$refs.updateBtn.disabled).toBe(true)

    fieldConfig.default = '150'
    await wrapper.setData({ fieldConfig: fieldConfig })
    await wrapper.find('#sodar-ss-col-input-range-min').vm.$emit('input')
    expect(wrapper.vm.formClasses.default).not.toContain('text-danger')
    expect(wrapper.vm.$refs.updateBtn.disabled).toBe(false)
  })

  // TODO: Test regex validation

  /* Event handling --------------------------------------------------------- */

  it('calls hideModal() with update', async () => {
    mountSheetTable()
    const wrapper = mount(ColumnConfigModal, {
      localVue, propsData: getPropsData({ app: app })
    })
    const spyHideModal = jest.spyOn(
      wrapper.vm, 'hideModal').mockImplementation(jest.fn())
    wrapper.vm.showModal(getShowModalParams('col0', {
      colType: 'NAME',
      configNodeIdx: 0,
      configFieldIdx: 0
    }))
    await waitNT(wrapper.vm)
    await waitRAF()

    await wrapper.find('#sodar-ss-col-btn-update').trigger('click')
    expect(spyHideModal).toBeCalledWith(true)
  })

  it('calls hideModal() with cancel', async () => {
    mountSheetTable()
    const wrapper = mount(ColumnConfigModal, {
      localVue, propsData: getPropsData({ app: app })
    })
    const spyHideModal = jest.spyOn(
      wrapper.vm, 'hideModal').mockImplementation(jest.fn())
    wrapper.vm.showModal(getShowModalParams('col0', {
      colType: 'NAME',
      configNodeIdx: 0,
      configFieldIdx: 0
    }))
    await waitNT(wrapper.vm)
    await waitRAF()

    await wrapper.find('#sodar-ss-col-btn-cancel').trigger('click')
    expect(spyHideModal).toBeCalledWith(false)
  })

  it('moves ontology down in list on button click', async () => {
    mountSheetTable()
    const wrapper = mount(ColumnConfigModal, {
      localVue, propsData: getPropsData({ app: app })
    })
    const modalParams = getShowModalParams('col1', {
      colType: 'ONTOLOGY',
      configNodeIdx: 0,
      configFieldIdx: 1
    })
    modalParams.fieldConfig.ontologies.push('CL')
    wrapper.vm.showModal(modalParams)
    await waitNT(wrapper.vm)
    await waitRAF()

    expect(wrapper.findAll('.sodar-ss-col-tr-ontology-enabled').at(0).find(
      '.sodar-ss-col-td-ontology-name').text()).toBe('NCBITAXON')
    await wrapper.findAll('.sodar-ss-col-tr-ontology-enabled').at(0).find(
      '.sodar-ss-btn-ontology-down').trigger('click')
    expect(wrapper.findAll('.sodar-ss-col-tr-ontology-enabled').at(0).find(
      '.sodar-ss-col-td-ontology-name').text()).toBe('CL')
  })

  it('moves ontology up in list on button click', async () => {
    mountSheetTable()
    const wrapper = mount(ColumnConfigModal, {
      localVue, propsData: getPropsData({ app: app })
    })
    const modalParams = getShowModalParams('col1', {
      colType: 'ONTOLOGY',
      configNodeIdx: 0,
      configFieldIdx: 1
    })
    modalParams.fieldConfig.ontologies.push('CL')
    wrapper.vm.showModal(modalParams)
    await waitNT(wrapper.vm)
    await waitRAF()

    expect(wrapper.findAll('.sodar-ss-col-tr-ontology-enabled').at(0).find(
      '.sodar-ss-col-td-ontology-name').text()).toBe('NCBITAXON')
    await wrapper.findAll('.sodar-ss-col-tr-ontology-enabled').at(1).find(
      '.sodar-ss-btn-ontology-up').trigger('click')
    expect(wrapper.findAll('.sodar-ss-col-tr-ontology-enabled').at(0).find(
      '.sodar-ss-col-td-ontology-name').text()).toBe('CL')
  })

  it('deletes ontology from list on button click', async () => {
    mountSheetTable()
    const wrapper = mount(ColumnConfigModal, {
      localVue, propsData: getPropsData({ app: app })
    })
    const modalParams = getShowModalParams('col1', {
      colType: 'ONTOLOGY',
      configNodeIdx: 0,
      configFieldIdx: 1
    })
    modalParams.fieldConfig.ontologies.push('CL')
    wrapper.vm.showModal(modalParams)
    await waitNT(wrapper.vm)
    await waitRAF()

    let ontologies = wrapper.findAll('.sodar-ss-col-tr-ontology-enabled')
    expect(ontologies.length).toBe(2)
    expect(ontologies.at(0).find(
      '.sodar-ss-col-td-ontology-name').text()).toBe('NCBITAXON')
    await ontologies.at(0).find('.sodar-ss-btn-ontology-delete').trigger('click')
    ontologies = wrapper.findAll('.sodar-ss-col-tr-ontology-enabled')
    expect(ontologies.length).toBe(1)
    expect(ontologies.at(0).find('.sodar-ss-col-td-ontology-name').text()).toBe('CL')
  })

  it('inserts ontology from list on button click', async () => {
    mountSheetTable()
    const wrapper = mount(ColumnConfigModal, {
      localVue, propsData: getPropsData({ app: app })
    })
    wrapper.vm.showModal(getShowModalParams('col1', {
      colType: 'ONTOLOGY',
      configNodeIdx: 0,
      configFieldIdx: 1
    }))
    await waitNT(wrapper.vm)
    await waitRAF()

    wrapper.setData({ insertOntology: 'CL' })
    await waitNT(wrapper.vm)

    let ontologies = wrapper.findAll('.sodar-ss-col-tr-ontology-enabled')
    expect(ontologies.length).toBe(1)
    expect(ontologies.at(0).find(
      '.sodar-ss-col-td-ontology-name').text()).toBe('NCBITAXON')
    await wrapper.find('#sodar-ss-col-ontology-btn-insert').trigger('click')
    ontologies = wrapper.findAll('.sodar-ss-col-tr-ontology-enabled')
    expect(ontologies.length).toBe(2)
    expect(ontologies.at(1).find('.sodar-ss-col-td-ontology-name').text()).toBe('CL')
  })

  it('returns config for clipboard copy', async () => {
    mountSheetTable()
    const wrapper = mount(ColumnConfigModal, {
      localVue, propsData: getPropsData({ app: app })
    })
    wrapper.vm.showModal(getShowModalParams('col9', {
      colType: null,
      configNodeIdx: 2,
      configFieldIdx: 2
    }))

    const copyConfig = wrapper.vm.getCopyData()
    const expectedConfig = copy(
      sheetEditConfigModified.studies[studyUuid].nodes[2].fields[2])
    delete expectedConfig.name
    delete expectedConfig.type
    expect(JSON.parse(copyConfig)).toEqual(expectedConfig)
  })

  it('copies config to clipboard', async () => {
    mountSheetTable()
    const wrapper = mount(ColumnConfigModal, {
      localVue, propsData: getPropsData({ app: app })
    })
    const spyGetCopyData = jest.spyOn(wrapper.vm, 'getCopyData')
    wrapper.vm.showModal(getShowModalParams('col9', {
      colType: null,
      configNodeIdx: 2,
      configFieldIdx: 2
    }))
    await waitNT(wrapper.vm)
    await waitRAF()

    await wrapper.find('#sodar-ss-col-btn-copy').trigger('v-clipboard:copy')
    expect(spyGetCopyData).toBeCalled()
  })

  it('handles config paste from clipboard', async () => {
    mountSheetTable()
    const wrapper = mount(ColumnConfigModal, {
      localVue, propsData: getPropsData({ app: app })
    })
    const spyOnPasteInput = jest.spyOn(wrapper.vm, 'onPasteInput')
    wrapper.vm.showModal(getShowModalParams('col9', {
      colType: null,
      configNodeIdx: 2,
      configFieldIdx: 2
    }))
    await waitNT(wrapper.vm)
    await waitRAF()

    const pasteData = {
      format: 'string',
      editable: false,
      regex: '',
      default: '',
    }
    await wrapper.setData({ pasteData: JSON.stringify(pasteData) })
    const inputField = wrapper.find('#sodar-ss-col-input-paste')
    await inputField.vm.$emit('input')

    expect(spyOnPasteInput).toBeCalled()
    expect(wrapper.vm.fieldConfig.editable).toBe(false)
    expect(wrapper.find('#sodar-ss-col-tr-format').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-col-tr-select').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-col-tr-range').exists()).toBe(false)
    expect(wrapper.vm.fieldConfig.range).toEqual([null, null])
    expect(wrapper.find('#sodar-ss-col-tr-regex').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-col-input-default').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-col-select-default').exists()).toBe(false)
    expect(wrapper.vm.fieldConfig.default).toBe('')
    expect(wrapper.find('#sodar-ss-col-tr-unit').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-col-tr-unit-default').exists()).toBe(false)
  })

  // TODO: Test clipboard paste with incompatible columns (see issue #1029)
  // TODO: Test cell updating and redrawing
})
