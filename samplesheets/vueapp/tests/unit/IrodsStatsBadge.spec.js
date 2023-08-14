import { createLocalVue, mount } from '@vue/test-utils'
import { projectUuid } from '../testUtils.js'
import IrodsStatsBadge from '@/components/IrodsStatsBadge.vue'
import '@/filters/prettyBytes.js'
import fetch from 'node-fetch'

// Set up extended Vue constructor
const localVue = createLocalVue()

// Init data
let propsData

// Mock fetch
global.fetch = fetch

describe('IrodsStatsBadge.vue', () => {
  function getPropsData () {
    return {
      projectUuid: projectUuid,
      irodsStatus: true,
      irodsPath: '/sodarZone/projects/00/00000000-0000-0000-0000-000000000000' +
                 '/sample_data/study_11111111-1111-1111-1111-111111111111'
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

  it('renders default badge', () => {
    const wrapper = mount(IrodsStatsBadge, { localVue, propsData: propsData })

    expect(wrapper.find('.sodar-ss-irods-stats').find('span').text()).toBe('Updating..')
  })

  it('updates and renders stats in badge', async () => {
    const wrapper = mount(IrodsStatsBadge, { localVue, propsData: propsData })

    await wrapper.vm.setStats({ file_count: 2, total_size: 170 })
    expect(wrapper.vm.fileCount).toBe(2)
    expect(wrapper.vm.totalSize).toBe(170)
    expect(wrapper.vm.error).toBe(false)
    expect(wrapper.find('.sodar-ss-irods-stats').find(
      'span').text().replace(/\s+/g, ' ')).toBe('2 files (170 B)')
  })

  it('renders error state', async () => {
    const wrapper = mount(IrodsStatsBadge, { localVue, propsData: propsData })

    await wrapper.setData({ error: true })
    expect(wrapper.find('.sodar-ss-irods-stats').find('span').text()).toBe('Error')
  })
})
