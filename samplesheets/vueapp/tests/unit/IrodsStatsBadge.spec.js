import { createLocalVue, mount } from '@vue/test-utils'
import IrodsStatsBadge from '@/components/IrodsStatsBadge.vue'
// TODO: Import prettybytes filter

// Set up extended Vue constructor
const localVue = createLocalVue()
// Mock filter
localVue.filter('prettyBytes', function (num) { return num + ' B' })

// Init data
let propsData

describe('IrodsStatsBadge.vue', () => {
  function getPropsData () {
    return {
      projectUuid: '00000000-0000-0000-0000-000000000000',
      irodsStatus: true,
      irodsPath: '/omicsZone/projects/00/00000000-0000-0000-0000-000000000000/sample_data/study_11111111-1111-1111-1111-111111111111'
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

    expect(wrapper.find('.sodar-vue-irods-stats').find('span').text()).toBe('Updating..')
  })

  it('updates and renders stats in badge', () => {
    const wrapper = mount(IrodsStatsBadge, { localVue, propsData: propsData })

    wrapper.vm.setStats({ file_count: 2, total_size: 170 })
    expect(wrapper.vm.fileCount).toBe(2)
    expect(wrapper.vm.totalSize).toBe(170)
    wrapper.vm.$nextTick(() => {
      expect(wrapper.find('.sodar-vue-irods-stats').find(
        'span').text().replace(/\s+/g, ' ')).toBe('2 files (170 B)')
    })
  })
})
