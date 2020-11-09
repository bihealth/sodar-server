import { createLocalVue, mount } from '@vue/test-utils'
import ListRow from '@/components/ListRow'

// Set up extended Vue constructor
const localVue = createLocalVue()

// Init data
let propsData

describe('ListRow.vue', () => {
  function getPropsData () {
    return {
      legend: 'Legend',
      value: 'Value'
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
    const wrapper = mount(ListRow, { localVue, propsData: propsData })

    expect(wrapper.find('dt').text()).toBe(propsData.legend)
    expect(wrapper.find('dd').text()).toBe(propsData.value)
  })

  it('renders list row with empty value', () => {
    propsData.value = null
    const wrapper = mount(ListRow, { localVue, propsData: propsData })

    expect(wrapper.find('dt').text()).toBe(propsData.legend)
    expect(wrapper.find('dd').text()).toBe('N/A')
  })
})
