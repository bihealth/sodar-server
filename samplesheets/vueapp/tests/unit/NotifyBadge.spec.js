import { createLocalVue, mount } from '@vue/test-utils'
import NotifyBadge from '@/components/NotifyBadge.vue'
import BootstrapVue from 'bootstrap-vue'

// Set up extended Vue constructor
const localVue = createLocalVue()
localVue.use(BootstrapVue)

describe('NotifyBadge.vue', () => {

  beforeAll(() => {
    // Disable warnings
    jest.spyOn(console, 'warn').mockImplementation(jest.fn())
  })

  beforeEach(() => {
    jest.resetModules()
    jest.clearAllMocks()
  })

  it('renders empty element by default', () => {
    const wrapper = mount(NotifyBadge, { localVue })

    expect(wrapper.find('.sodar-ss-vue-notify').exists()).toBe(false)
  })

  // TODO: Fix
  /*
  it('renders badge temporarily when show() is called', done => {
    const wrapper = mount(NotifyBadge, { localVue })

    expect(wrapper.find('.sodar-ss-vue-notify').exists()).toBe(false)
    wrapper.vm.show('Message', 'primary', 3000)
    setTimeout(() => {
      expect(wrapper.find('.sodar-ss-vue-notify').exists()).toBe(true)
      expect(wrapper.find('.sodar-ss-vue-notify').text()).toBe('Message')
      expect(wrapper.find('.sodar-ss-vue-notify').classes()).not.toContain('badge-primary')
      done()
    }, 100)
    setTimeout(() => {
      expect(wrapper.find('.sodar-ss-vue-notify').exists()).toBe(false)
      done()
    }, 2000)
  })
  */
})
