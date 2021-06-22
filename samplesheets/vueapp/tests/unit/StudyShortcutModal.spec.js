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

// Set up fetch-mock-jest
const fetchMock = require('fetch-mock-jest')

// Init data
let propsData
const ajaxUrl = '/samplesheets/ajax/study/links/' + studyUuid + '?case=A001'

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
    fetchMock.reset()
  })

  it('renders modal with study shortcut data', async () => {
    fetchMock.mock(ajaxUrl, studyShortcuts)
    const wrapper = mount(StudyShortcutModal, {
      localVue, propsData: propsData
    })
    wrapper.vm.showModal({ key: 'case', value: 'A001' })
    await waitNT(wrapper.vm)
    await waitRAF()

    expect(fetchMock.called(ajaxUrl)).toBe(true)
    expect(wrapper.find('#sodar-ss-shortcut-modal').exists()).toBe(true)
    expect(wrapper.findAll('.sodar-ss-shortcut-item').length).toBe(3)
    expect(wrapper.findAll('.sodar-ss-shortcut-extra').length).toBe(4)
  })

  it('renders modal with message', async () => {
    fetchMock.mock(ajaxUrl, { detail: 'Message' })
    const wrapper = mount(StudyShortcutModal, {
      localVue, propsData: propsData
    })
    wrapper.vm.showModal({ key: 'case', value: 'A001' })
    await waitNT(wrapper.vm)
    await waitRAF()

    expect(wrapper.find('.sodar-ss-shortcut-table').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-shortcuts-message').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-shortcuts-message').text()).toBe('Message')
  })

  it('renders modal while waiting for data', async () => {
    fetchMock.mock(ajaxUrl, studyShortcuts, { delay: 5000 })
    const wrapper = mount(StudyShortcutModal, {
      localVue, propsData: propsData
    })
    wrapper.vm.showModal({ key: 'case', value: 'A001' })
    await waitNT(wrapper.vm)
    await waitRAF()

    expect(wrapper.find('.sodar-ss-shortcut-table').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-shortcuts-message').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-shortcuts-wait').exists()).toBe(true)
  })
})
