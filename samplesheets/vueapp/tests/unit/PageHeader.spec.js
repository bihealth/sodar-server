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
        projectUuid: '00000000-0000-0000-0000-000000000000',
        renderError: false,
        sheetsAvailable: true,
        sheetSyncEnabled: false,
        sodarContext: JSON.parse(JSON.stringify(sodarContext)),
        unsavedRow: null,
        versionSaved: true,
        windowsOs: false
      },
      handleNavCallback: jest.fn(),
      showSubPageCallback: jest.fn(),
      toggleEditModeCallback: jest.fn(),
      editorHelpModal: {
        showModal: jest.fn()
      },
      winExportModal: {
        showModal: jest.fn()
      },
      versionSaveModal: {
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
    expect(wrapper.find('#sodar-ss-subtitle').exists()).toBe(true)
    expect(wrapper.findAll('.sodar-ss-tab-study').length).toBe(1)
    expect(wrapper.find('#sodar-ss-tab-overview').exists()).toBe(true)

    // Nav dropdown
    expect(wrapper.find('#sodar-ss-nav-dropdown').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-nav-dropdown').find('button').classes()).not.toContain('disabled')
    expect(wrapper.findAll('.sodar-ss-nav-item').length).toBe(3)

    // Edit badge
    expect(wrapper.find('#sodar-ss-badge-edit').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-link-edit-help').exists()).toBe(false)

    // Save Version Button
    expect(wrapper.find('#sodar-ss-btn-version-save').exists()).toBe(false)

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
    expect(wrapper.find('#sodar-ss-btn-edit-finish').exists()).toBe(false)
  })

  it('renders page header for guest user', () => {
    propsData.app.sodarContext.perms = {
      edit_sheet: false,
      manage_sheet: false,
      create_colls: false,
      export_sheet: true,
      delete_sheet: false,
      view_versions: true,
      edit_config: false,
      is_superuser: false
    }
    const wrapper = mount(PageHeader, { localVue, propsData: propsData })

    // Operations dropdown
    expect(wrapper.find('#sodar-ss-op-dropdown').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-op-item-import').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-op-item-edit').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-op-item-warnings').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-op-item-cache').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-op-item-replace').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-op-item-export').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-op-item-irods').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-op-item-versions').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-op-item-delete').exists()).toBe(false)
  })

  it('renders page header with sheet sync enabled', () => {
    propsData.app.sheetSyncEnabled = true
    const wrapper = mount(PageHeader, { localVue, propsData: propsData })

    // Basic elements and nav
    expect(wrapper.find('#sodar-ss-subtitle').exists()).toBe(true)
    expect(wrapper.findAll('.sodar-ss-tab-study').length).toBe(1)
    expect(wrapper.find('#sodar-ss-tab-overview').exists()).toBe(true)

    // Nav dropdown
    expect(wrapper.find('#sodar-ss-nav-dropdown').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-nav-dropdown').find('button').classes()).not.toContain('disabled')
    expect(wrapper.findAll('.sodar-ss-nav-item').length).toBe(3)

    // Edit badge
    expect(wrapper.find('#sodar-ss-badge-edit').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-link-edit-help').exists()).toBe(false)

    // Save Version Button
    expect(wrapper.find('#sodar-ss-btn-version-save').exists()).toBe(false)

    // Operations dropdown
    expect(wrapper.find('#sodar-ss-op-dropdown').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-op-item-import').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-op-item-edit').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-op-item-warnings').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-op-item-cache').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-op-item-replace').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-op-item-export').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-op-item-irods').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-op-item-versions').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-op-item-delete').exists()).toBe(false)

    // Finish editing button
    expect(wrapper.find('#sodar-ss-btn-edit-finish').exists()).toBe(false)
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
    expect(wrapper.findAll('.sodar-ss-op-item').length).toBe(2)
    expect(wrapper.find('#sodar-ss-op-item-import').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-op-item-create').exists()).toBe(true)
  })

  it('renders page header with no sample sheet and sheet sync enabled', () => {
    propsData.app.sodarContext = JSON.parse(JSON.stringify(sodarContextNoSheet))
    propsData.app.sheetsAvailable = false
    propsData.app.irodsStatus = null
    propsData.app.sheetSyncEnabled = true
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
    expect(wrapper.find('#sodar-ss-op-item-sync').exists()).toBe(true)
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
    expect(wrapper.find('#sodar-ss-badge-edit').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-link-edit-help').exists()).toBe(true)

    // Save Version Button
    expect(wrapper.find('#sodar-ss-btn-version-save').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-btn-version-save').classes()).toContain('disabled')

    // Operations dropdown
    expect(wrapper.find('#sodar-ss-op-dropdown').exists()).toBe(false)

    // Finish editing button
    expect(wrapper.find('#sodar-ss-btn-edit-finish').exists()).toBe(true)
  })

  it('enables version save button with unsaved version', () => {
    propsData.app.editMode = true
    propsData.app.versionSaved = false
    const wrapper = mount(PageHeader, { localVue, propsData: propsData })

    // Finish editing button
    expect(wrapper.find('#sodar-ss-btn-version-save').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-btn-version-save').classes()).not.toContain('disabled')
  })

  it('renders disabled finish editing button with unsaved row', () => {
    propsData.app.editMode = true
    propsData.app.unsavedRow = true
    const wrapper = mount(PageHeader, { localVue, propsData: propsData })

    // Finish editing button
    expect(wrapper.find('#sodar-ss-btn-edit-finish').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-btn-edit-finish').classes()).toContain('disabled')
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
    expect(wrapper.find('#sodar-ss-badge-edit').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-link-edit-help').exists()).toBe(false)

    // Operations dropdown
    expect(wrapper.find('#sodar-ss-op-dropdown').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-op-dropdown').find('button').classes()).toContain('disabled')

    // Finish editing button
    expect(wrapper.find('#sodar-ss-btn-edit-finish').exists()).toBe(false)
  })

  it('renders operations dropdown header with sheet render error', () => {
    propsData.app.renderError = true
    const wrapper = mount(PageHeader, { localVue, propsData: propsData })

    // Operations dropdown
    expect(wrapper.findAll('.sodar-ss-op-item').length).toBe(9)
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
    expect(wrapper.findAll('.sodar-ss-op-item').length).toBe(9)
    expect(wrapper.find('#sodar-ss-op-item-delete').exists()).toBe(false)
  })

  it('calls handleNavCallback() when study tab is clicked', async () => {
    propsData.app.handleStudyNavigation = jest.fn()
    const wrapper = mount(PageHeader, { localVue, propsData: propsData })
    const spyHandleStudyNav = jest.spyOn(wrapper.vm, 'handleNavCallback')

    expect(wrapper.findAll('.sodar-ss-tab-study').at(0).find('a').classes()).not.toContain('disabled')
    expect(spyHandleStudyNav).not.toHaveBeenCalled()
    await wrapper.findAll('.sodar-ss-tab-study').at(0).find('a').trigger('click')
    expect(spyHandleStudyNav).toHaveBeenCalled()
  })

  it('calls handleNavCallback() when nav dropdown study link is clicked', async () => {
    const wrapper = mount(PageHeader, { localVue, propsData: propsData })
    const spyHandleStudyNav = jest.spyOn(wrapper.vm, 'handleNavCallback')

    expect(spyHandleStudyNav).toBeCalledTimes(0)
    await wrapper.findAll('.sodar-ss-nav-item').at(0).find('a').trigger('click') // Study
    expect(spyHandleStudyNav).toBeCalledTimes(1)
    await wrapper.findAll('.sodar-ss-nav-item').at(1).find('a').trigger('click') // Assay
    expect(spyHandleStudyNav).toBeCalledTimes(2)
  })

  it('calls showSubPageCallback() when overview tab is clicked', async () => {
    const wrapper = mount(PageHeader, { localVue, propsData: propsData })
    const spyShowSubPage = jest.spyOn(wrapper.vm, 'showSubPageCallback')

    expect(spyShowSubPage).not.toHaveBeenCalled()
    await wrapper.find('#sodar-ss-tab-overview').find('a').trigger('click')
    expect(spyShowSubPage).toHaveBeenCalled()
  })

  it('calls showSubPage() when nav dropdown overview link is clicked', async () => {
    const wrapper = mount(PageHeader, { localVue, propsData: propsData })
    const spyShowSubPage = jest.spyOn(wrapper.vm, 'showSubPageCallback')

    expect(spyShowSubPage).not.toHaveBeenCalled()
    await wrapper.find('#sodar-ss-nav-overview').find('a').trigger('click')
    expect(spyShowSubPage).toHaveBeenCalled()
  })

  it('calls showSubPage() when op dropdown warnings link is clicked', async () => {
    const wrapper = mount(PageHeader, { localVue, propsData: propsData })
    const spyShowSubPage = jest.spyOn(wrapper.vm, 'showSubPageCallback')

    expect(spyShowSubPage).not.toHaveBeenCalled()
    await wrapper.find('#sodar-ss-op-item-warnings').trigger('click')
    expect(spyShowSubPage).toHaveBeenCalled()
  })

  it('calls toggleEditModeCallback() when op dropdown edit link is clicked', async () => {
    const wrapper = mount(PageHeader, { localVue, propsData: propsData })
    const spyToggleEditMode = jest.spyOn(wrapper.vm, 'toggleEditModeCallback')

    expect(spyToggleEditMode).not.toHaveBeenCalled()
    await wrapper.find('#sodar-ss-op-item-edit').trigger('click')
    expect(spyToggleEditMode).toHaveBeenCalled()
  })

  it('calls toggleEditModeCallback() when finish editing button is clicked', async () => {
    propsData.app.editMode = true
    const wrapper = mount(PageHeader, { localVue, propsData: propsData })
    const spyToggleEditMode = jest.spyOn(wrapper.vm, 'toggleEditModeCallback')

    expect(wrapper.find('#sodar-ss-btn-edit-finish').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-btn-edit-finish').classes()).not.toContain('disabled')
    expect(spyToggleEditMode).not.toHaveBeenCalled()
    await wrapper.find('#sodar-ss-btn-edit-finish').trigger('click')
    expect(spyToggleEditMode).toHaveBeenCalled()
  })

  it('opens editorHelpModal when editor help icon is clicked', async () => {
    propsData.app.editMode = true
    const wrapper = mount(PageHeader, { localVue, propsData: propsData })
    const spyShowModal = jest.spyOn(wrapper.props().editorHelpModal, 'showModal')

    expect(spyShowModal).not.toHaveBeenCalled()
    await wrapper.find('#sodar-ss-link-edit-help').trigger('click')
    expect(spyShowModal).toHaveBeenCalled()
  })

  it('opens winExportModal when export link is clicked', async () => {
    propsData.app.windowsOs = true
    const wrapper = mount(PageHeader, { localVue, propsData: propsData })
    const spyShowModal = jest.spyOn(wrapper.props().winExportModal, 'showModal')

    expect(spyShowModal).not.toHaveBeenCalled()
    await wrapper.find('#sodar-ss-op-item-export').trigger('click')
    expect(spyShowModal).toHaveBeenCalled()
  })

  it('does not open winExportModal if os is not windows', async () => {
    const wrapper = mount(PageHeader, { localVue, propsData: propsData })
    const spyShowModal = jest.spyOn(wrapper.props().winExportModal, 'showModal')

    await wrapper.find('#sodar-ss-op-item-export').trigger('click')
    expect(spyShowModal).not.toHaveBeenCalled()
  })

  it('opens versionSaveModal when save link is clicked', async () => {
    propsData.app.editMode = true
    propsData.app.versionSaved = false
    const wrapper = mount(PageHeader, { localVue, propsData: propsData })
    const spyShowModal = jest.spyOn(wrapper.props().versionSaveModal, 'showModal')

    expect(spyShowModal).not.toHaveBeenCalled()
    await wrapper.find('#sodar-ss-btn-version-save').trigger('click')
    expect(spyShowModal).toHaveBeenCalled()
  })
})
