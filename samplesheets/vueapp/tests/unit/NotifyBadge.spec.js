import { createLocalVue, mount } from '@vue/test-utils'
import { waitSelector } from '../testUtils.js'
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

    expect(wrapper.find('.sodar-ss-notify-badge').exists()).toBe(false)
  })

  it('renders badge when show() is called', async () => {
    const wrapper = mount(NotifyBadge, { localVue })

    expect(wrapper.find('.sodar-ss-notify-badge').exists()).toBe(false)
    wrapper.vm.show('Message', 'primary', 3000)
    await waitSelector(wrapper, '.sodar-ss-notify-badge', 1)
    expect(wrapper.find('.sodar-ss-notify-badge').exists()).toBe(true)
    expect(wrapper.find('.sodar-ss-notify-badge').text()).toBe('Message')
    expect(wrapper.find('.sodar-ss-notify-badge')
      .classes()).toContain('badge-primary')
    await waitSelector(wrapper, '.sodar-ss-notify-badge', 0)
    expect(wrapper.find('.sodar-ss-notify-badge').exists()).toBe(false)
  })
})
