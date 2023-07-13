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
    const wrapper = mount(Overview, { localVue, propsData: propsData })

    expect(wrapper.find('#sodar-ss-overview-investigation').exists()).toBe(true)
    expect(wrapper.findAll('.sodar-ss-overview-study').length).toBe(1)
    expect(wrapper.find('#sodar-ss-overview-stats').exists()).toBe(true)

    // IrodsStatsBadge
    expect(wrapper.find('.sodar-ss-irods-stats').exists()).toBe(true)
  })
})
