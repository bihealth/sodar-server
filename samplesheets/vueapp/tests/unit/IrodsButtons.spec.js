import { createLocalVue, mount } from '@vue/test-utils'
import BootstrapVue from 'bootstrap-vue'
import VueClipboard from 'vue-clipboard2'
import IrodsButtons from '@/components/IrodsButtons.vue'

// Set up extended Vue constructor
const localVue = createLocalVue()
localVue.use(BootstrapVue)
localVue.use(VueClipboard)

// Init data
let propsData

describe('IrodsButtons.vue', () => {
  function getPropsData () {
    return {
      irodsBackendEnabled: true,
      irodsStatus: true,
      irodsWebdavUrl: 'http://davrods.local',
      irodsPath: '/omicsZone/projects/f1/11111111-1111-1111-1111-111111111111',
      showFileList: false,
      modalComponent: null,
      enabled: null,
      editMode: false,
      notifyCallback: null
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

  it('renders default buttons in enabled state', () => {
    const wrapper = mount(IrodsButtons, { localVue, propsData: propsData })

    expect(wrapper.find('.sodar-vue-popup-list-btn').exists()).toBe(false)
    expect(wrapper.find('.sodar-irods-copy-path-btn').exists()).toBe(true)
    expect(wrapper.find('.sodar-irods-copy-path-btn')).not.toContain('disabled')
    expect(wrapper.find('.sodar-irods-copy-dav-btn').exists()).toBe(true)
    expect(wrapper.find('.sodar-irods-copy-dav-btn')).not.toContain('disabled')
    expect(wrapper.find('.sodar-irods-dav-btn').exists()).toBe(true)
    expect(wrapper.find('.sodar-irods-dav-btn')).not.toContain('disabled')
    expect(wrapper.vm.getEnabledState()).toBe(true)
  })

  it('renders default buttons in disabled state if forced', () => {
    propsData.enabled = false
    const wrapper = mount(IrodsButtons, { localVue, propsData: propsData })

    expect(wrapper.find('.sodar-vue-popup-list-btn').exists()).toBe(false)
    expect(wrapper.find('.sodar-irods-copy-path-btn').exists()).toBe(true)
    expect(wrapper.find('.sodar-irods-copy-path-btn').attributes().disabled).toBe('disabled')
    expect(wrapper.find('.sodar-irods-copy-dav-btn').exists()).toBe(true)
    expect(wrapper.find('.sodar-irods-copy-dav-btn').attributes().disabled).toBe('disabled')
    expect(wrapper.find('.sodar-irods-dav-btn').exists()).toBe(true)
    expect(wrapper.find('.sodar-irods-dav-btn').classes()).toContain('disabled')
    expect(wrapper.vm.getEnabledState()).toBe(false)
  })

  it('renders default buttons in disabled state if in edit mode', () => {
    propsData.editMode = true
    const wrapper = mount(IrodsButtons, { localVue, propsData: propsData })

    expect(wrapper.find('.sodar-vue-popup-list-btn').exists()).toBe(false)
    expect(wrapper.find('.sodar-irods-copy-path-btn').attributes().disabled).toBe('disabled')
    expect(wrapper.find('.sodar-irods-copy-dav-btn').attributes().disabled).toBe('disabled')
    expect(wrapper.find('.sodar-irods-dav-btn').classes()).toContain('disabled')
    expect(wrapper.vm.getEnabledState()).toBe(false)
  })

  it('renders default buttons in disabled state without irods collections', () => {
    propsData.irodsStatus = false
    const wrapper = mount(IrodsButtons, { localVue, propsData: propsData })

    expect(wrapper.find('.sodar-vue-popup-list-btn').exists()).toBe(false)
    expect(wrapper.find('.sodar-irods-copy-path-btn').attributes().disabled).toBe('disabled')
    expect(wrapper.find('.sodar-irods-copy-dav-btn').attributes().disabled).toBe('disabled')
    expect(wrapper.find('.sodar-irods-dav-btn').classes()).toContain('disabled')
    expect(wrapper.vm.getEnabledState()).toBe(false)
  })

  it('renders all buttons with showFileList', () => {
    propsData.showFileList = true
    const wrapper = mount(IrodsButtons, { localVue, propsData: propsData })

    expect(wrapper.find('.sodar-vue-popup-list-btn').exists()).toBe(true)
    expect(wrapper.find('.sodar-irods-copy-path-btn')).not.toContain('disabled')
    expect(wrapper.find('.sodar-irods-copy-path-btn')).not.toContain('disabled')
    expect(wrapper.find('.sodar-irods-copy-dav-btn')).not.toContain('disabled')
    expect(wrapper.find('.sodar-irods-dav-btn')).not.toContain('disabled')
    expect(wrapper.vm.getEnabledState()).toBe(true)
  })

  it('calls copy event and notifyCallback on iRODS path copy button click', () => {
    propsData.notifyCallback = jest.fn()
    const wrapper = mount(IrodsButtons, { localVue, propsData: propsData })
    const spyOnCopyBtnClick = jest.spyOn(wrapper.vm, 'onCopyBtnClick')
    const spyNotifyCallback = jest.spyOn(wrapper.vm, 'notifyCallback')
    wrapper.setMethods({
      onCopyBtnClick: spyOnCopyBtnClick,
      notifyCallback: spyNotifyCallback
    })

    expect(spyOnCopyBtnClick).not.toHaveBeenCalled()
    expect(spyNotifyCallback).not.toHaveBeenCalled()
    wrapper.find('.sodar-irods-copy-path-btn').trigger('click')
    expect(spyOnCopyBtnClick).toHaveBeenCalled()
    expect(spyNotifyCallback).toHaveBeenCalled()
  })

  it('opens modal component on iRODS dir list button click', () => {
    propsData.showFileList = true
    propsData.modalComponent = {
      setTitle: jest.fn(),
      showModal: jest.fn()
    }
    const wrapper = mount(IrodsButtons, { localVue, propsData: propsData })
    const spyOnDirListClick = jest.spyOn(wrapper.vm, 'onDirListClick')
    wrapper.setMethods({ onDirListClick: spyOnDirListClick })
    const spySetTitle = jest.spyOn(wrapper.props().modalComponent, 'setTitle')
    const spyShowModal = jest.spyOn(wrapper.props().modalComponent, 'showModal')

    expect(spyOnDirListClick).not.toHaveBeenCalled()
    expect(spySetTitle).not.toHaveBeenCalled()
    expect(spyShowModal).not.toHaveBeenCalled()
    wrapper.find('.sodar-vue-popup-list-btn').trigger('click')
    expect(spyOnDirListClick).toHaveBeenCalled()
    expect(spySetTitle).toHaveBeenCalled()
    expect(spyShowModal).toHaveBeenCalled()
  })
})
