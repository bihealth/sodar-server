import { createLocalVue, mount } from '@vue/test-utils'
import { waitNT, waitRAF } from '../utils.js'
import BootstrapVue from 'bootstrap-vue'
import StudyShortcutModal from '@/components/modals/StudyShortcutModal.vue'
import studyShortcuts from './data/studyShortcutsCancer.json'

// Set up extended Vue constructor
const localVue = createLocalVue()
localVue.use(BootstrapVue)

// Init data
let propsData

describe('StudyShortcutModal.vue', () => {
  function getPropsData () {
    return {
      irodsWebdavUrl: 'http://davrods.local',
      projectUuid: '00000000-0000-0000-0000-000000000000',
      studyUuid: '11111111-1111-1111-1111-111111111111'
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

  it('renders modal with study shortcut data', async () => {
    const wrapper = mount(StudyShortcutModal, {
      localVue,
      propsData: propsData,
      methods: { getShortcuts: jest.fn() }
    })
    wrapper.vm.showModal({ key: 'case', value: 'A001' })
    wrapper.vm.handleShortcutResponse(studyShortcuts)
    await waitNT(wrapper.vm)
    await waitRAF()

    expect(wrapper.find('#sodar-vue-shortcut-modal').exists()).toBe(true)
    expect(wrapper.findAll('.sodar-ss-vue-shortcut-item').length).toBe(3)
    expect(wrapper.findAll('.sodar-ss-vue-shortcut-extra').length).toBe(4)
  })

  it('renders modal with message', async () => {
    const wrapper = mount(StudyShortcutModal, {
      localVue,
      propsData: propsData,
      methods: { getShortcuts: jest.fn() }
    })
    wrapper.vm.showModal({ key: 'case', value: 'A001' })
    wrapper.vm.handleShortcutResponse({ message: 'Message' })
    await waitNT(wrapper.vm)
    await waitRAF()

    expect(wrapper.find('.sodar-ss-vue-shortcut-table').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-vue-shortcuts-message').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-vue-shortcuts-message').text()).toBe('Message')
  })

  it('renders modal while waiting for data', async () => {
    const wrapper = mount(StudyShortcutModal, {
      localVue,
      propsData: propsData,
      methods: { getShortcuts: jest.fn() }
    })
    wrapper.vm.showModal({ key: 'case', value: 'A001' })
    await waitNT(wrapper.vm)
    await waitRAF()

    expect(wrapper.find('.sodar-ss-vue-shortcut-table').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-vue-shortcuts-message').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-vue-shortcuts-wait').exists()).toBe(true)
  })
})
