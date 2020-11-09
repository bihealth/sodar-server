import { createLocalVue, mount } from '@vue/test-utils'
import BootstrapVue from 'bootstrap-vue'
import ParserWarnings from '@/components/ParserWarnings.vue'
import sodarContext from './data/sodarContext.json'
import parserWarnings from './data/parserWarnings.json'

// Set up extended Vue constructor
const localVue = createLocalVue()
localVue.use(BootstrapVue)

// Init data
let propsData

describe('ParserWarnings.vue', () => {
  function getPropsData () {
    return {
      projectUuid: '00000000-0000-0000-0000-000000000000',
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
  })

  it('renders parser warnings', () => {
    const wrapper = mount(ParserWarnings, {
      localVue,
      propsData: propsData,
      methods: { getWarnings: jest.fn() }
    })
    wrapper.vm.handleWarningsResponse(parserWarnings)

    setTimeout(() => {
      expect(wrapper.find('#sodar-ss-warnings-card').exists()).toBe(true)
      expect(wrapper.findAll('.sodar-ss-warnings-item').length).toBe(3)
    }, 100)
  })

  it('renders parser message', () => {
    const wrapper = mount(ParserWarnings, {
      localVue,
      propsData: propsData,
      methods: { getWarnings: jest.fn() }
    })
    wrapper.vm.handleWarningsResponse({ message: 'message' })

    setTimeout(() => {
      expect(wrapper.find('#sodar-ss-warnings-message').exists()).toBe(true)
      expect(wrapper.find('#sodar-ss-warnings-message').text()).toBe('message')
      expect(wrapper.find('#sodar-ss-warnings-card').exists()).toBe(false)
    }, 100)
  })
})
