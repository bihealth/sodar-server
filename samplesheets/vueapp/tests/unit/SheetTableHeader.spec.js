import { createLocalVue, mount } from '@vue/test-utils'
import { copy, waitNT, waitRAF } from '../testUtils.js'
import BootstrapVue from 'bootstrap-vue'
import VueClipboard from 'vue-clipboard2'
import SheetTableHeader from '@/components/SheetTableHeader.vue'
import sodarContext from './data/sodarContext.json'

// Set up extended Vue constructor
const localVue = createLocalVue()
localVue.use(BootstrapVue)
localVue.use(VueClipboard)

describe('SheetTableHeader.vue', () => {
  function getPropsData (params = {}) {
    let gridUuid = '11111111-1111-1111-1111-111111111111'
    if (params.assayMode) gridUuid = '22222222-2222-2222-2222-222222222222'
    return {
      params: {
        assayMode: params.assayMode,
        editMode: params.editMode,
        gridUuid: gridUuid,
        projectUuid: '00000000-0000-0000-0000-000000000000',
        sodarContext: copy(sodarContext),
        studyUuid: '11111111-1111-1111-1111-111111111111',
        showNotificationCb: jest.fn()
      }
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
    jest.resetModules()
    jest.clearAllMocks()
  })

  it('renders study table header', async () => {
    const wrapper = mount(SheetTableHeader, {
      localVue,
      propsData: getPropsData(),
      stubs: getStubs()
    })

    // General
    expect(wrapper.find('#sodar-ss-section-study').exists()).toBe(true)
    expect(wrapper.find('h4').classes()).toContain('text-info')
    expect(wrapper.find('h4').text()).toContain('Study:')
    expect(wrapper.find('.sodar-ss-table-plugin').exists()).toBe(false)

    // Badges
    expect(wrapper.find('.sodar-ss-irods-stats').exists()).toBe(true)

    // IrodsButtons
    expect(wrapper.find('.sodar-ss-irods-links').exists()).toBe(true)
    expect(wrapper.find('.sodar-irods-copy-path-btn')
      .attributes().disabled).toBe(undefined)
  })

  it('renders assay table header', async () => {
    const wrapper = mount(SheetTableHeader, {
      localVue,
      propsData: getPropsData({ assayMode: true }),
      stubs: getStubs()
    })

    // General
    expect(wrapper.find('#sodar-ss-section-assay-22222222-2222-2222-2222-222222222222')
      .exists()).toBe(true)
    expect(wrapper.find('h4').classes()).toContain('text-danger')
    expect(wrapper.find('h4').text()).toContain('Assay:')
    expect(wrapper.find('.sodar-ss-table-plugin').exists()).toBe(true)

    // Badges
    expect(wrapper.find('.sodar-ss-irods-stats').exists()).toBe(false)

    // IrodsButtons
    expect(wrapper.find('.sodar-ss-irods-links').exists()).toBe(true)
    expect(wrapper.find('.sodar-irods-copy-path-btn')
      .attributes().disabled).toBe(undefined)
  })

  it('renders study table header in edit mode', async () => {
    const wrapper = mount(SheetTableHeader, {
      localVue,
      propsData: getPropsData({ editMode: true }),
      stubs: getStubs()
    })

    expect(wrapper.find('.sodar-ss-irods-stats').exists()).toBe(false)
    expect(wrapper.find('.sodar-ss-irods-links').exists()).toBe(true)
    expect(wrapper.find('.sodar-irods-copy-path-btn')
      .attributes().disabled).toBe('disabled')
  })

  it('renders assay table header in edit mode', async () => {
    const wrapper = mount(SheetTableHeader, {
      localVue,
      propsData: getPropsData({ assayMode: true, editMode: true }),
      stubs: getStubs()
    })

    expect(wrapper.find('.sodar-ss-irods-stats').exists()).toBe(false)
    expect(wrapper.find('.sodar-ss-irods-links').exists()).toBe(true)
    expect(wrapper.find('.sodar-irods-copy-path-btn')
      .attributes().disabled).toBe('disabled')
  })

  it('renders study table header with no irods collections', async () => {
    const propsData = getPropsData()
    propsData.params.sodarContext.irods_status = false
    const wrapper = mount(SheetTableHeader, {
      localVue,
      propsData: propsData,
      stubs: getStubs()
    })

    expect(wrapper.find('.sodar-ss-irods-stats').exists()).toBe(false)
    expect(wrapper.find('.sodar-ss-irods-links').exists()).toBe(true)
    expect(wrapper.find('.sodar-irods-copy-path-btn')
      .attributes().disabled).toBe('disabled')
  })

  it('renders assay table header with no irods collections', async () => {
    const propsData = getPropsData({ assayMode: true })
    propsData.params.sodarContext.irods_status = false
    const wrapper = mount(SheetTableHeader, {
      localVue,
      propsData: propsData,
      stubs: getStubs()
    })

    expect(wrapper.find('.sodar-ss-irods-stats').exists()).toBe(false)
    expect(wrapper.find('.sodar-ss-irods-links').exists()).toBe(true)
    expect(wrapper.find('.sodar-irods-copy-path-btn')
      .attributes().disabled).toBe('disabled')
  })

  it('renders study plugin icon with edit_sheet false', async () => {
    const propsData = getPropsData({ assayMode: true })
    propsData.params.sodarContext.perms.edit_sheet = false
    const wrapper = mount(SheetTableHeader, {
      localVue,
      propsData: propsData,
      stubs: getStubs()
    })
    expect(wrapper.find('.sodar-ss-table-plugin').exists()).toBe(false)
  })

  it('renders study plugin icon with edit_sheet true', async () => {
    const propsData = getPropsData({ assayMode: true })
    propsData.params.sodarContext.perms.edit_sheet = true
    const wrapper = mount(SheetTableHeader, {
      localVue,
      propsData: propsData,
      stubs: getStubs()
    })
    expect(wrapper.find('.sodar-ss-table-plugin').exists()).toBe(true)
  })
})
