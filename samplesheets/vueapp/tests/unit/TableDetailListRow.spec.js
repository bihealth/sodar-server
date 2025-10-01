import { createLocalVue, mount } from '@vue/test-utils'
import TableDetailListRow from '@/components/TableDetailListRow'
import BootstrapVue from 'bootstrap-vue'
import VueClipboard from 'vue-clipboard2'

// Set up extended Vue constructor
const localVue = createLocalVue()
localVue.use(BootstrapVue)
localVue.use(VueClipboard)

// Init data
let propsData

describe('TableDetailListRow.vue', () => {
  function getPropsData () {
    return {
      legend: 'Legend',
      value: 'Value',
      icon: 'mdi:file',
      iconClass: 'text-primary',
      title: 'Row Title',
      rowClass: 'row-class'
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

  it('renders list row', () => {
    const wrapper = mount(
      TableDetailListRow, { localVue, propsData: propsData })

    expect(wrapper.find('dl').classes()).toContain('row-class')
    expect(wrapper.find('dt').text()).toBe(propsData.legend)
    expect(wrapper.find('dt').find('i').attributes('data-icon')).toBe('mdi:file')
    expect(wrapper.find('dt').find('i').attributes('title')).toBe('Row Title')
    expect(wrapper.find('dt').find('i').attributes('class')).toBe('iconify text-primary')
    expect(wrapper.find('dd').text()).toBe(propsData.value)
    expect(wrapper.find('dd').classes()).not.toContain('sodar-ss-table-detail-value-empty')
    expect(wrapper.find('dd').classes()).not.toContain('text-muted')
    expect(wrapper.find('.sodar-ss-clip-copy-btn').exists()).toBe(false)
  })

  it('renders list row with empty value', () => {
    propsData.value = null
    const wrapper = mount(
      TableDetailListRow, { localVue, propsData: propsData })

    expect(wrapper.find('dd').text()).toBe('N/A')
    expect(wrapper.find('dd').classes()).toContain('sodar-ss-table-detail-value-empty')
    expect(wrapper.find('dd').classes()).toContain('text-muted')
  })

  it('renders list row with copy button', () => {
    propsData.copyButton = true
    const wrapper = mount(
      TableDetailListRow, { localVue, propsData: propsData })

    expect(wrapper.find('dl').classes()).toContain('row-class')
    expect(wrapper.find('dt').text()).toBe(propsData.legend)
    expect(wrapper.find('dt').find('i').attributes('data-icon')).toBe('mdi:file')
    expect(wrapper.find('dt').find('i').attributes('title')).toBe('Row Title')
    expect(wrapper.find('dt').find('i').attributes('class')).toBe('iconify text-primary')
    expect(wrapper.find('dd').text()).toBe(propsData.value)
    expect(wrapper.find('dd').classes()).not.toContain('sodar-ss-table-detail-value-empty')
    expect(wrapper.find('dd').classes()).not.toContain('text-muted')
    expect(wrapper.find('.sodar-ss-clip-copy-btn').exists()).toBe(true)
  })
})
