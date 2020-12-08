import { createLocalVue, mount } from '@vue/test-utils'
import {
  projectUuid,
  studyUuid,
  assayUuid,
  waitNT,
  waitRAF
} from '../testUtils.js'
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
      projectUuid: projectUuid,
      studyUuid: studyUuid
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

    expect(wrapper.find('#sodar-ss-shortcut-modal').exists()).toBe(true)
    expect(wrapper.findAll('.sodar-ss-shortcut-item').length).toBe(3)
    expect(wrapper.findAll('.sodar-ss-shortcut-extra').length).toBe(4)
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

    expect(wrapper.find('.sodar-ss-shortcut-table').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-shortcuts-message').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-shortcuts-message').text()).toBe('Message')
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

    expect(wrapper.find('.sodar-ss-shortcut-table').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-shortcuts-message').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-shortcuts-wait').exists()).toBe(true)
  })
})
