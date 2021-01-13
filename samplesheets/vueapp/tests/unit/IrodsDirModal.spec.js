import { createLocalVue, mount } from '@vue/test-utils'
import { createContainer, waitNT, waitRAF } from '../testUtils.js'
import BootstrapVue from 'bootstrap-vue'
import IrodsDirModal from '@/components/modals/IrodsDirModal.vue'
import irodsObjectList from './data/irodsObjectList.json'
import '@/filters/prettyBytes.js'

// Set up extended Vue constructor
const localVue = createLocalVue()
localVue.use(BootstrapVue)

// Init data
let propsData
const rootIrodsPath = (
  '/omicsZone/projects/00/00000000-0000-0000-0000-000000000000/sample_data/' +
  'study_11111111-1111-1111-1111-111111111111/' +
  'assay_22222222-2222-2222-2222-222222222222/0815-N1-DNA1'
)

describe('IrodsDirModal.vue', () => {
  function getPropsData () {
    return {
      irodsWebdavUrl: 'http://davrods.local',
      projectUuid: '00000000-0000-0000-0000-000000000000'
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

  it('renders object list with irods object data', async () => {
    const wrapper = mount(IrodsDirModal, {
      localVue,
      propsData: propsData,
      attachTo: createContainer(), // NOTE: Doesn't seem to be required?
      methods: { getObjList: jest.fn() }
    })
    wrapper.vm.showModal(rootIrodsPath)
    wrapper.vm.handleObjListResponse(irodsObjectList)
    await waitNT(wrapper.vm)
    await waitRAF()

    expect(wrapper.find('#sodar-irods-modal-content').exists()).toBe(true)
    expect(wrapper.findAll('.sodar-ss-irods-obj').length).toBe(2)
    expect(wrapper.find('#sodar-ss-irods-empty').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-irods-message').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-irods-wait').exists()).toBe(false)
  })

  it('renders modal with empty object list', async () => {
    const wrapper = mount(IrodsDirModal, {
      localVue, propsData: propsData, methods: { getObjList: jest.fn() }
    })
    wrapper.vm.showModal(rootIrodsPath)
    wrapper.vm.handleObjListResponse({ data_objects: [] })
    await waitNT(wrapper.vm)
    await waitRAF()

    expect(wrapper.vm.message).toBe('Empty collection')
    expect(wrapper.find('#sodar-irods-obj-table').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-irods-empty').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-irods-message').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-irods-wait').exists()).toBe(false)
  })

  it('renders modal with a returned message', async () => {
    const wrapper = mount(IrodsDirModal, {
      localVue, propsData: propsData, methods: { getObjList: jest.fn() }
    })
    wrapper.vm.showModal(rootIrodsPath)
    wrapper.vm.handleObjListResponse({ detail: 'Message' })
    await waitNT(wrapper.vm)
    await waitRAF()

    expect(wrapper.find('#sodar-irods-obj-table').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-irods-empty').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-irods-message').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-irods-message').text()).toBe('Message')
    expect(wrapper.find('#sodar-ss-irods-wait').exists()).toBe(false)
  })

  it('renders modal while waiting for data', async () => {
    const wrapper = mount(IrodsDirModal, {
      localVue, propsData: propsData, methods: { getObjList: jest.fn() }
    })
    wrapper.vm.showModal(rootIrodsPath)
    await waitNT(wrapper.vm)
    await waitRAF()

    expect(wrapper.find('#sodar-irods-modal-content').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-irods-empty').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-irods-message').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-irods-wait').exists()).toBe(true)
  })

  it('updates list on onFilterUpdate()', async () => {
    const wrapper = mount(IrodsDirModal, {
      localVue, propsData: propsData, methods: { getObjList: jest.fn() }
    })
    wrapper.vm.showModal(rootIrodsPath)
    wrapper.vm.handleObjListResponse(irodsObjectList)
    await waitNT(wrapper.vm)
    await waitRAF()

    await wrapper.vm.onFilterUpdate('test2')
    expect(wrapper.find('.sodar-irods-obj-table').exists()).toBe(true)
    expect(wrapper.findAll('.sodar-ss-irods-obj').length).toBe(2)
    expect(wrapper.findAll('.sodar-ss-irods-obj').at(0).isVisible()).toBe(false)
    expect(wrapper.findAll('.sodar-ss-irods-obj').at(1).isVisible()).toBe(true)
    await wrapper.vm.onFilterUpdate('')
    expect(wrapper.findAll('.sodar-ss-irods-obj').at(0).isVisible()).toBe(true)
    expect(wrapper.findAll('.sodar-ss-irods-obj').at(1).isVisible()).toBe(true)
  })

  it('updates modal title on setTitle()', async () => {
    const updatedTitle = 'Updated title'
    const wrapper = mount(IrodsDirModal, {
      localVue, propsData: propsData, methods: { getObjList: jest.fn() }
    })
    wrapper.vm.showModal(rootIrodsPath)
    wrapper.vm.handleObjListResponse(irodsObjectList)
    await waitNT(wrapper.vm)
    await waitRAF()

    expect(wrapper.find('.modal-title').text()).not.toBe(updatedTitle)
    await wrapper.vm.setTitle(updatedTitle)
    expect(wrapper.find('.modal-title').text()).toBe(updatedTitle)
  })

  it('returns relative path to data object on getRelativePath()', () => {
    const subCollPath = (
      '/omicsZone/projects/00/00000000-0000-0000-0000-000000000000/' +
      'sample_data/study_11111111-1111-1111-1111-111111111111/' +
      'assay_22222222-2222-2222-2222-222222222222/0815-N1-DNA1/subcoll/test2.txt'
    )
    const wrapper = mount(IrodsDirModal, {
      localVue,
      propsData: propsData,
      methods: { getObjList: jest.fn() }
    })
    wrapper.vm.showModal(rootIrodsPath)
    expect(wrapper.vm.getRelativePath(irodsObjectList.data_objects[0].path)).toBe('')
    expect(wrapper.vm.getRelativePath(subCollPath)).toBe('subcoll')
  })
})
