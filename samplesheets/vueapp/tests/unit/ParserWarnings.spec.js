import { createLocalVue, mount } from '@vue/test-utils'
import BootstrapVue from 'bootstrap-vue'
import { waitNT, waitRAF } from '../testUtils.js'
import ParserWarnings from '@/components/ParserWarnings.vue'
import sodarContext from './data/sodarContext.json'
import parserWarnings from './data/parserWarnings.json'

// Set up extended Vue constructor
const localVue = createLocalVue()
localVue.use(BootstrapVue)

// Set up fetch-mock-jest
const fetchMock = require('fetch-mock-jest')

// Init data
let propsData
const projectUuid = '00000000-0000-0000-0000-000000000000'
const ajaxUrl = '/samplesheets/ajax/warnings/' + projectUuid

describe('ParserWarnings.vue', () => {
  function getPropsData () {
    return {
      projectUuid: projectUuid,
      sodarContext: JSON.parse(JSON.stringify(sodarContext))
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

  it('renders parser warnings', async () => {
    fetchMock.mock(ajaxUrl, parserWarnings)
    const wrapper = mount(ParserWarnings, {
      localVue,
      propsData: propsData
    })
    await waitNT(wrapper.vm)
    await waitRAF()

    expect(fetchMock.called(ajaxUrl)).toBe(true)
    expect(wrapper.find('#sodar-ss-warnings-card').exists()).toBe(true)
    expect(wrapper.findAll('.sodar-ss-warnings-item').length).toBe(3)
  })

  it('renders parser message', async () => {
    fetchMock.mock(ajaxUrl, { detail: 'message' })
    const wrapper = mount(ParserWarnings, {
      localVue,
      propsData: propsData
    })
    await waitNT(wrapper.vm)
    await waitRAF()

    expect(fetchMock.called(ajaxUrl)).toBe(true)
    expect(wrapper.find('#sodar-ss-warnings-message').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-warnings-message').text()).toBe('message')
    expect(wrapper.find('#sodar-ss-warnings-card').exists()).toBe(false)
  })
})
