import { createLocalVue, mount } from '@vue/test-utils'
import BootstrapVue from 'bootstrap-vue'
import PageHeader from '@/components/PageHeader.vue'
import sodarContext from './data/sodarContext.json'
import sodarContextNoSheet from './data/sodarContextNoSheet.json'
import '@/filters/truncate.js'

// Set up extended Vue constructor
const localVue = createLocalVue()
localVue.use(BootstrapVue)

// Init data
let propsData

describe('PageHeader.vue', () => {
  function getPropsData () {
    return {
      app: { // Mock relevant data & methods in app
        activeSubPage: null,
        currentStudyUuid: '11111111-1111-1111-1111-111111111111',
        editMode: false,
        gridsBusy: false,
        handleStudyNavigation: jest.fn(),
        projectUuid: '00000000-0000-0000-0000-000000000000',
        renderError: false,
        sheetsAvailable: true,
        showSubPage: jest.fn(),
        sodarContext: JSON.parse(JSON.stringify(sodarContext)),
        toggleEditMode: jest.fn(),
        unsavedRow: false,
        windowsOs: false
      },
      editorHelpModal: {
        showModal: jest.fn()
      },
      winExportModal: {
        showModal: jest.fn()
      }
    }
  }

  beforeAll(() => {
    // Disable warnings
    jest.spyOn(console, 'warn').mockImplementation(jest.fn())
  })

  beforeEach(() => {
    propsData = getPropsData()
    jest.resetModules()
    jest.clearAllMocks()
  })

  it('renders page header', () => {
    const wrapper = mount(PageHeader, { localVue, propsData: propsData })

    // Basic elements and nav
    expect(wrapper.find('#sodar-ss-vue-subtitle').exists()).toBe(true)
    expect(wrapper.findAll('.sodar-ss-tab-study').length).toBe(1)
    expect(wrapper.find('#sodar-ss-tab-overview').exists()).toBe(true)

    // Nav dropdown
    expect(wrapper.find('#sodar-ss-nav-dropdown').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-nav-dropdown').find('button').classes()).not.toContain('disabled')
    expect(wrapper.findAll('.sodar-ss-nav-item').length).toBe(3)

    // Edit badge
    expect(wrapper.find('#sodar-ss-vue-badge-edit').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-vue-link-edit-help').exists()).toBe(false)

    // Operations dropdown
    expect(wrapper.find('#sodar-ss-op-dropdown').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-op-item-import').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-op-item-edit').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-op-item-warnings').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-op-item-cache').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-op-item-replace').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-op-item-export').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-op-item-irods').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-op-item-versions').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-op-item-delete').exists()).toBe(true)

    // Finish editing button
    expect(wrapper.find('#sodar-ss-vue-btn-edit-finish').exists()).toBe(false)
  })

  it('renders page header with no sample sheet', () => {
    propsData.app.sodarContext = JSON.parse(JSON.stringify(sodarContextNoSheet))
    propsData.app.sheetsAvailable = false
    propsData.app.irodsStatus = null
    const wrapper = mount(PageHeader, { localVue, propsData: propsData })

    // Nav
    expect(wrapper.findAll('.sodar-ss-tab-study').length).toBe(0)
    expect(wrapper.find('#sodar-ss-tab-overview').exists()).toBe(false)

    // Nav dropdown
    expect(wrapper.find('#sodar-ss-nav-dropdown').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-nav-dropdown').find('button').classes()).toContain('disabled')

    // Operations dropdown
    expect(wrapper.find('#sodar-ss-op-dropdown').exists()).toBe(true)
    expect(wrapper.findAll('.sodar-ss-op-item').length).toBe(1)
    expect(wrapper.find('#sodar-ss-op-item-import').exists()).toBe(true)
  })

  it('renders page header in edit mode', () => {
    propsData.app.editMode = true
    const wrapper = mount(PageHeader, { localVue, propsData: propsData })

    // Nav
    expect(wrapper.find('#sodar-ss-tab-overview').find('a').classes()).toContain('disabled')

    // Nav dropdown
    expect(wrapper.find('#sodar-ss-nav-dropdown').find('button').classes()).not.toContain('disabled')
    expect(wrapper.findAll('.sodar-ss-nav-item').length).toBe(3)
    expect(wrapper.findAll('.sodar-ss-nav-item').at(2).find('a').classes()).toContain('disabled')

    // Edit badge
    expect(wrapper.find('#sodar-ss-vue-badge-edit').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-vue-link-edit-help').exists()).toBe(true)

    // Operations dropdown
    expect(wrapper.find('#sodar-ss-op-dropdown').exists()).toBe(false)

    // Finish editing button
    expect(wrapper.find('#sodar-ss-vue-btn-edit-finish').exists()).toBe(true)
  })

  it('renders disabled finish editing button with unsaved row', () => {
    propsData.app.editMode = true
    propsData.app.unsavedRow = true
    const wrapper = mount(PageHeader, { localVue, propsData: propsData })

    // Finish editing button
    expect(wrapper.find('#sodar-ss-vue-btn-edit-finish').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-vue-btn-edit-finish').classes()).toContain('disabled')
  })

  it('renders page header while rendering grid', () => {
    propsData.app.gridsBusy = true
    const wrapper = mount(PageHeader, { localVue, propsData: propsData })

    // Nav
    expect(wrapper.find('.sodar-ss-tab-study').find('a').classes()).toContain('disabled')
    expect(wrapper.find('#sodar-ss-tab-overview').find('a').classes()).toContain('disabled')

    // Nav dropdown
    expect(wrapper.find('#sodar-ss-nav-dropdown').find('button').classes()).toContain('disabled')

    // Edit badge
    expect(wrapper.find('#sodar-ss-vue-badge-edit').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-vue-link-edit-help').exists()).toBe(false)

    // Operations dropdown
    expect(wrapper.find('#sodar-ss-op-dropdown').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-op-dropdown').find('button').classes()).toContain('disabled')

    // Finish editing button
    expect(wrapper.find('#sodar-ss-vue-btn-edit-finish').exists()).toBe(false)
  })

  it('renders operations dropdown header with sheet render error', () => {
    propsData.app.renderError = true
    const wrapper = mount(PageHeader, { localVue, propsData: propsData })

    // Operations dropdown
    expect(wrapper.findAll('.sodar-ss-op-item').length).toBe(7)
    expect(wrapper.find('#sodar-ss-op-item-irods').exists()).toBe(false)
  })

  it('renders operations dropdown header with no irods collections', () => {
    propsData.app.sodarContext.irods_status = false
    const wrapper = mount(PageHeader, { localVue, propsData: propsData })

    // Operations dropdown
    expect(wrapper.findAll('.sodar-ss-op-item').length).toBe(7)
    expect(wrapper.find('#sodar-ss-op-item-cache').exists()).toBe(false)
  })

  it('renders operations dropdown header with no delete_sheet perm', () => {
    propsData.app.sodarContext.perms.delete_sheet = false
    const wrapper = mount(PageHeader, { localVue, propsData: propsData })

    // Operations dropdown
    expect(wrapper.findAll('.sodar-ss-op-item').length).toBe(7)
    expect(wrapper.find('#sodar-ss-op-item-delete').exists()).toBe(false)
  })

  it('calls handleStudyNavigation() when study tab is clicked', () => {
    // Add extra study
    /*
    propsData.app.sodarContext.studies['11111111-1111-1111-1111-222222222222'] = {
      display_name: 'Second Study',
      identifier: 's_small2',
      description: ''
    }
    */
    const wrapper = mount(PageHeader, { localVue, propsData: propsData })
    const spyHandleStudyNav = jest.spyOn(wrapper.props().app, 'handleStudyNavigation')

    expect(wrapper.findAll('.sodar-ss-tab-study').at(0).find('a').classes()).not.toContain('disabled')
    wrapper.findAll('.sodar-ss-tab-study').at(0).trigger('click')
    setTimeout(() => { expect(spyHandleStudyNav).toHaveBeenCalled() }, 100)
  })

  it('calls handleStudyNavigation() when nav dropdown study link is clicked', () => {
    const wrapper = mount(PageHeader, { localVue, propsData: propsData })
    const spyHandleStudyNav = jest.spyOn(wrapper.props().app, 'handleStudyNavigation')

    wrapper.findAll('.sodar-ss-nav-item').at(0).trigger('click') // Study
    setTimeout(() => { expect(spyHandleStudyNav).toHaveBeenCalled() }, 100)
    wrapper.findAll('.sodar-ss-nav-item').at(1).trigger('click') // Assay
    setTimeout(() => { expect(spyHandleStudyNav).toHaveBeenCalled() }, 100)
  })

  it('calls showSubPage() when overview tab is clicked', () => {
    const wrapper = mount(PageHeader, { localVue, propsData: propsData })
    const spyHandleStudyNav = jest.spyOn(wrapper.props().app, 'handleStudyNavigation')

    wrapper.find('#sodar-ss-tab-overview').trigger('click')
    setTimeout(() => { expect(spyHandleStudyNav).toHaveBeenCalled() }, 100)
  })

  it('calls showSubPage() when nav dropdown overview link is clicked', () => {
    const wrapper = mount(PageHeader, { localVue, propsData: propsData })
    const spyHandleStudyNav = jest.spyOn(wrapper.props().app, 'handleStudyNavigation')

    wrapper.find('#sodar-ss-nav-overview').trigger('click')
    setTimeout(() => { expect(spyHandleStudyNav).toHaveBeenCalled() }, 100)
  })

  it('calls showSubPage() when op dropdown warnings link is clicked', () => {
    const wrapper = mount(PageHeader, { localVue, propsData: propsData })
    const spyHandleStudyNav = jest.spyOn(wrapper.props().app, 'handleStudyNavigation')

    wrapper.find('#sodar-ss-op-item-warnings').trigger('click')
    setTimeout(() => { expect(spyHandleStudyNav).toHaveBeenCalled() }, 100)
  })

  it('calls toggleEditMode() when op dropdown edit link is clicked', () => {
    const wrapper = mount(PageHeader, { localVue, propsData: propsData })
    const spyHandleStudyNav = jest.spyOn(wrapper.props().app, 'handleStudyNavigation')

    wrapper.find('#sodar-ss-op-item-edit').trigger('click')
    setTimeout(() => { expect(spyHandleStudyNav).toHaveBeenCalled() }, 100)
  })

  it('calls toggleEditMode() when finish editing button is clicked', () => {
    propsData.app.editMode = true
    const wrapper = mount(PageHeader, { localVue, propsData: propsData })
    const spyHandleStudyNav = jest.spyOn(wrapper.props().app, 'handleStudyNavigation')

    wrapper.find('#sodar-ss-vue-btn-edit-finish').trigger('click')
    setTimeout(() => { expect(spyHandleStudyNav).toHaveBeenCalled() }, 100)
  })

  it('opens editorHelpModal when editor help icon is clicked', () => {
    propsData.app.editMode = true
    const wrapper = mount(PageHeader, { localVue, propsData: propsData })
    const spyShowModal = jest.spyOn(wrapper.props().editorHelpModal, 'showModal')

    wrapper.find('#sodar-ss-vue-btn-edit-finish').trigger('click')
    setTimeout(() => { expect(spyShowModal).toHaveBeenCalled() }, 100)
  })

  it('opens winExportModal when export link is clicked', () => {
    propsData.app.windowsOs = true
    const wrapper = mount(PageHeader, { localVue, propsData: propsData })
    const spyShowModal = jest.spyOn(wrapper.props().winExportModal, 'showModal')

    wrapper.find('#sodar-ss-op-item-export').trigger('click')
    setTimeout(() => { expect(spyShowModal).toHaveBeenCalled() }, 100)
  })

  it('does not open winExportModal if os is not windows', () => {
    const wrapper = mount(PageHeader, { localVue, propsData: propsData })
    const spyShowModal = jest.spyOn(wrapper.props().winExportModal, 'showModal')

    wrapper.find('#sodar-ss-op-item-export').trigger('click')
    setTimeout(() => { expect(spyShowModal).not.toHaveBeenCalled() }, 100)
  })
})
