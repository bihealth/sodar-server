import { createLocalVue, mount } from '@vue/test-utils'
import BootstrapVue from 'bootstrap-vue'
import Overview from '@/components/Overview.vue'
import sodarContext from './data/sodarContext.json'

// Set up extended Vue constructor
const localVue = createLocalVue()
localVue.use(BootstrapVue)

// Init data
let propsData

describe('Overview.vue', () => {
  function getPropsData () {
    return {
      sodarContext: JSON.parse(JSON.stringify(sodarContext))
    }
  }

  function getStubs () {
    return {
      IrodsStatsBadge: {
        template: '<div class="sodar-ss-irods-stats" />',
        methods: { updateStats: jest.fn() }
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

  it('renders overview subpage', () => {
    const wrapper = mount(Overview, {
      localVue,
      propsData: propsData,
      stubs: getStubs()
    })

    expect(wrapper.find('#sodar-ss-overview-investigation').exists()).toBe(true)
    expect(wrapper.findAll('.sodar-ss-overview-study').length).toBe(1)
    expect(wrapper.find('#sodar-ss-overview-stats').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-overview-irods').exists()).toBe(true)
    expect(wrapper.find('.sodar-ss-irods-stats').exists()).toBe(true)
  })
  it('renders overview subpage with no view files perm', () => {
    propsData.sodarContext.perms.view_files = false
    const wrapper = mount(Overview, {
      localVue,
      propsData: propsData,
      stubs: getStubs()
    })

    expect(wrapper.find('#sodar-ss-overview-investigation').exists()).toBe(true)
    expect(wrapper.findAll('.sodar-ss-overview-study').length).toBe(1)
    expect(wrapper.find('#sodar-ss-overview-stats').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-overview-irods').exists()).toBe(false)
    expect(wrapper.find('.sodar-ss-irods-stats').exists()).toBe(false)
  })
})
