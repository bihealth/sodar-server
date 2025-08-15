import { createLocalVue, mount } from '@vue/test-utils'
import BootstrapVue from 'bootstrap-vue'
import VueClipboard from 'vue-clipboard2'
import AssayShortcutCard from '@/components/AssayShortcutCard.vue'
import sodarContext from './data/sodarContext.json'
import assayShortcuts from './data/assayShortcuts.json'

// Set up extended Vue constructor
const localVue = createLocalVue()
localVue.use(BootstrapVue)
localVue.use(VueClipboard)

// Init data
let propsData

describe('AssayShortcutCard.vue', () => {
  function getPropsData () {
    return {
      sodarContext: JSON.parse(JSON.stringify(sodarContext)),
      assayShortcuts: JSON.parse(JSON.stringify(assayShortcuts)),
      modalComponent: null,
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

  it('renders assay shortcuts', () => {
    const wrapper = mount(AssayShortcutCard, { localVue, propsData: propsData })

    expect(wrapper.findAll('.sodar-ss-assay-shortcut').length).toBe(3)
    expect(wrapper.findAll('[data-icon="mdi:puzzle"]').length).toBe(0)
    for (let i = 0; i < 3; i++) {
      expect(wrapper.findAll('.sodar-ss-popup-list-btn').at(i).exists()).toBe(true)
      expect(wrapper.findAll('.sodar-irods-copy-path-btn').at(i).attributes().disabled).toBe(undefined)
      expect(wrapper.findAll('.sodar-irods-copy-dav-btn').at(i).attributes().disabled).toBe(undefined)
      expect(wrapper.findAll('.sodar-irods-dav-btn').at(i).attributes().disabled).toBe(undefined)
    }
    expect(wrapper.findAll('.sodar-irods-ticket-access-1-btn').at(0)
      .attributes().disabled).toBe(undefined)
  })

  it('renders extra assay plugin shortcut', () => {
    propsData.assayShortcuts.push({
      id: 'plugin_shortcut',
      label: 'Plugin Shortcut',
      path: '/sodarZone/projects/00/00000000-0000-0000-0000-000000000000/' +
            'sample_data/study_11111111-1111-1111-1111-111111111111/' +
            'assay_22222222-2222-2222-2222-222222222222/PluginShortcut',
      icon: 'mdi:puzzle',
      title: 'Defined in assay plugin',
      assay_plugin: true
    })
    const wrapper = mount(AssayShortcutCard, { localVue, propsData: propsData })

    expect(wrapper.findAll('.sodar-ss-assay-shortcut').length).toBe(4)
    expect(wrapper.findAll('[data-icon="mdi:puzzle"]').length).toBe(1)
  })

  it('renders disabled shortcuts', () => {
    propsData.assayShortcuts[0].enabled = false
    propsData.assayShortcuts[1].enabled = false
    propsData.assayShortcuts[2].extra_links[0].enabled = false
    const wrapper = mount(AssayShortcutCard, { localVue, propsData: propsData })

    expect(wrapper.findAll('.sodar-ss-assay-shortcut').length).toBe(3)
    for (let i = 0; i < 2; i++) {
      expect(wrapper.findAll('.sodar-ss-popup-list-btn').at(i).exists()).toBe(true)
      expect(wrapper.findAll('.sodar-ss-popup-list-btn').at(i).attributes().disabled).toBe('disabled')
      expect(wrapper.findAll('.sodar-irods-copy-path-btn').at(i).attributes().disabled).toBe('disabled')
      expect(wrapper.findAll('.sodar-irods-copy-dav-btn').at(i).attributes().disabled).toBe('disabled')
      expect(wrapper.findAll('.sodar-irods-dav-btn').at(i).classes()).toContain('disabled')
    }
    expect(wrapper.findAll('.sodar-ss-popup-list-btn').at(2).exists()).toBe(true)
    expect(wrapper.findAll('.sodar-irods-copy-path-btn').at(2)).not.toContain('disabled')
    expect(wrapper.findAll('.sodar-irods-copy-dav-btn').at(2)).not.toContain('disabled')
    expect(wrapper.findAll('.sodar-irods-dav-btn').at(2)).not.toContain('disabled')
    expect(wrapper.findAll('.sodar-irods-ticket-access-1-btn').at(0).classes()).toContain('disabled')
  })

  it('calls copy event and notifyCallback on iRODS path copy button click', () => {
    propsData.notifyCallback = jest.fn()
    const wrapper = mount(AssayShortcutCard, { localVue, propsData: propsData })
    const spyNotifyCallback = jest.spyOn(wrapper.vm, 'notifyCallback')

    expect(spyNotifyCallback).not.toHaveBeenCalled()
    wrapper.find('.sodar-irods-copy-path-btn').trigger('click')
    expect(spyNotifyCallback).toHaveBeenCalled()
  })

  it('opens modal component on iRODS dir list button click', () => {
    propsData.showFileList = true
    propsData.modalComponent = {
      setTitle: jest.fn(),
      showModal: jest.fn()
    }
    const wrapper = mount(AssayShortcutCard, { localVue, propsData: propsData })
    const spySetTitle = jest.spyOn(wrapper.props().modalComponent, 'setTitle')
    const spyShowModal = jest.spyOn(wrapper.props().modalComponent, 'showModal')

    expect(spySetTitle).not.toHaveBeenCalled()
    expect(spyShowModal).not.toHaveBeenCalled()
    wrapper.find('.sodar-ss-popup-list-btn').trigger('click')
    expect(spySetTitle).toHaveBeenCalled()
    expect(spyShowModal).toHaveBeenCalled()
  })

  it('does not render assay shortcuts if user lacks view files perm', () => {
    propsData.sodarContext.perms.view_files = false
    const wrapper = mount(AssayShortcutCard, { localVue, propsData: propsData })

    expect(wrapper.find('.sodar-ss-assay-shortcut-card').exists()).toBe(false)
  })
})
