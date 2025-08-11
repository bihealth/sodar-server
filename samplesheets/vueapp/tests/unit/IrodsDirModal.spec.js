import { createLocalVue, mount } from '@vue/test-utils'
import {
  projectUuid,
  copy,
  getAppStub,
  waitNT,
  waitRAF,
  displayNone
} from '../testUtils.js'
import BootstrapVue from 'bootstrap-vue'
import IrodsDirModal from '@/components/modals/IrodsDirModal.vue'
import irodsObjectList from './data/irodsObjectList.json'
import '@/filters/prettyBytes.js'

// Set up extended Vue constructor
const localVue = createLocalVue()
localVue.use(BootstrapVue)

// Set up fetch-mock-jest
const fetchMock = require('fetch-mock-jest')

// Init data
let propsData
let objList
const rootIrodsPath = (
  '/sodarZone/projects/00/00000000-0000-0000-0000-000000000000/sample_data/' +
  'study_11111111-1111-1111-1111-111111111111/' +
  'assay_22222222-2222-2222-2222-222222222222/0815-N1-DNA1'
)
const listAjaxUrl = '/samplesheets/ajax/irods/objects/' +
  projectUuid + '?path=' + encodeURIComponent(rootIrodsPath)

describe('IrodsDirModal.vue', () => {
  function getPropsData () {
    return {
      irodsWebdavUrl: 'http://davrods.local',
      projectUuid: '00000000-0000-0000-0000-000000000000',
      app: getAppStub()
    }
  }

  beforeAll(() => {
    // Disable warnings
    jest.spyOn(console, 'warn').mockImplementation(jest.fn())
  })

  beforeEach(() => {
    propsData = getPropsData()
    objList = copy(irodsObjectList)
    jest.resetModules()
    jest.clearAllMocks()
    fetchMock.reset()
  })

  it('renders object list with irods object data', async () => {
    fetchMock.mock(listAjaxUrl, objList)
    const wrapper = mount(IrodsDirModal, {
      localVue,
      propsData: propsData
    })
    wrapper.vm.showModal(rootIrodsPath)
    await waitNT(wrapper.vm)
    await waitRAF()

    expect(fetchMock.called(listAjaxUrl)).toBe(true)
    expect(wrapper.find('#sodar-irods-modal-content').exists()).toBe(true)
    expect(wrapper.findAll('.sodar-ss-irods-obj').length).toBe(2)
    expect(wrapper.find('#sodar-ss-irods-empty').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-irods-message').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-irods-wait').exists()).toBe(false)
    expect(wrapper.findAll('.sodar-ss-request-delete-btn').length).toBe(1)
    expect(wrapper.findAll('.sodar-ss-request-cancel-btn').length).toBe(1)
    // expect(wrapper.find('.sodar-ss-irods-stats').isVisible()).toBe(true)
    expect(wrapper.find('.sodar-ss-irods-stats').attributes('style')).not.toBe(displayNone)
  })

  it('renders modal with empty object list', async () => {
    fetchMock.mock(listAjaxUrl, { irods_data: [] })
    const wrapper = mount(IrodsDirModal, {
      localVue, propsData: propsData
    })
    wrapper.vm.showModal(rootIrodsPath)
    await waitNT(wrapper.vm)
    await waitRAF()

    expect(fetchMock.called(listAjaxUrl)).toBe(true)
    expect(wrapper.vm.message).toBe('Empty collection')
    expect(wrapper.find('#sodar-irods-obj-table').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-irods-empty').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-irods-message').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-irods-wait').exists()).toBe(false)
    expect(wrapper.find('.sodar-ss-irods-stats').exists()).toBe(false)
  })

  it('renders modal with a returned message', async () => {
    fetchMock.mock(listAjaxUrl, { detail: 'Message' })
    const wrapper = mount(IrodsDirModal, {
      localVue, propsData: propsData
    })
    wrapper.vm.showModal(rootIrodsPath)
    await waitNT(wrapper.vm)
    await waitRAF()

    expect(fetchMock.called(listAjaxUrl)).toBe(true)
    expect(wrapper.find('#sodar-irods-obj-table').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-irods-empty').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-irods-message').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-irods-message').text()).toBe('Message')
    expect(wrapper.find('#sodar-ss-irods-wait').exists()).toBe(false)
  })

  it('renders modal while waiting for data', async () => {
    fetchMock.mock(listAjaxUrl, objList, { delay: 5000 })
    const wrapper = mount(IrodsDirModal, {
      localVue, propsData: propsData
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
    fetchMock.mock(listAjaxUrl, objList)
    const wrapper = mount(IrodsDirModal, {
      localVue, propsData: propsData
    })
    wrapper.vm.showModal(rootIrodsPath)
    await waitNT(wrapper.vm)
    await waitRAF()

    await wrapper.vm.onFilterUpdate('test2')
    expect(wrapper.find('.sodar-irods-obj-table').exists()).toBe(true)
    expect(wrapper.findAll('.sodar-ss-irods-obj').length).toBe(2)
    expect(wrapper.findAll('.sodar-ss-irods-obj').at(0).attributes('style')).toBe(displayNone)
    expect(wrapper.findAll('.sodar-ss-irods-obj').at(1).attributes('style')).not.toBe(displayNone)
    await wrapper.vm.onFilterUpdate('')
    expect(wrapper.findAll('.sodar-ss-irods-obj').at(0).attributes('style')).not.toBe(displayNone)
    expect(wrapper.findAll('.sodar-ss-irods-obj').at(1).attributes('style')).not.toBe(displayNone)
  })

  it('updates list on onFilterUpdate() with different case', async () => {
    fetchMock.mock(listAjaxUrl, objList)
    const wrapper = mount(IrodsDirModal, {
      localVue, propsData: propsData
    })
    wrapper.vm.showModal(rootIrodsPath)
    await waitNT(wrapper.vm)
    await waitRAF()

    await wrapper.vm.onFilterUpdate('Test2') // Different case than in result
    expect(wrapper.find('.sodar-irods-obj-table').exists()).toBe(true)
    expect(wrapper.findAll('.sodar-ss-irods-obj').length).toBe(2)
    expect(wrapper.findAll('.sodar-ss-irods-obj').at(0).attributes('style')).toBe(displayNone)
    expect(wrapper.findAll('.sodar-ss-irods-obj').at(1).attributes('style')).not.toBe(displayNone)
  })

  it('updates list on onFilterUpdate() with full subpath', async () => {
    objList.irods_data[1].path = '/sodarZone/projects/00/' +
        '00000000-0000-0000-0000-000000000000/sample_data/' +
        'study_11111111-1111-1111-1111-111111111111/' +
        'assay_22222222-2222-2222-2222-222222222222/' +
        '0815-N1-DNA1/subcoll/test2.txt'
    fetchMock.mock(listAjaxUrl, objList)
    const wrapper = mount(IrodsDirModal, {
      localVue, propsData: propsData
    })
    wrapper.vm.showModal(rootIrodsPath)
    await waitNT(wrapper.vm)
    await waitRAF()

    await wrapper.vm.onFilterUpdate('subcoll/test2.txt')
    expect(wrapper.find('.sodar-irods-obj-table').exists()).toBe(true)
    expect(wrapper.findAll('.sodar-ss-irods-obj').length).toBe(2)
    expect(wrapper.findAll('.sodar-ss-irods-obj').at(0).attributes('style')).toBe(displayNone)
    expect(wrapper.findAll('.sodar-ss-irods-obj').at(1).attributes('style')).not.toBe(displayNone)
  })

  it('clears filter input on modal re-open', async () => {
    fetchMock.mock(listAjaxUrl, objList)
    const wrapper = mount(IrodsDirModal, {
      localVue, propsData: propsData
    })
    wrapper.vm.showModal(rootIrodsPath)
    await waitNT(wrapper.vm)
    await waitRAF()

    expect(wrapper.find('#sodar-ss-irods-filter').element.value).toBe('')
    await wrapper.find('#sodar-ss-irods-filter').setValue('test2')
    expect(wrapper.find('#sodar-ss-irods-filter').element.value).toBe('test2')
    expect(wrapper.find('.sodar-irods-obj-table').exists()).toBe(true)
    wrapper.vm.hideModal()
    await waitNT(wrapper.vm)
    await waitRAF()

    wrapper.vm.showModal(rootIrodsPath)
    await waitNT(wrapper.vm)
    await waitRAF()
    expect(wrapper.find('#sodar-ss-irods-filter').element.value).toBe('')
  })

  it('displays no results row for filtering', async () => {
    fetchMock.mock(listAjaxUrl, objList)
    const wrapper = mount(IrodsDirModal, {
      localVue, propsData: propsData
    })
    wrapper.vm.showModal(rootIrodsPath)
    await waitNT(wrapper.vm)
    await waitRAF()

    expect(wrapper.find('#sodar-ss-irods-filter-empty').exists()).toBe(false)
    expect(wrapper.findAll('.sodar-ss-irods-obj').length).toBe(2)
    expect(wrapper.findAll('.sodar-ss-irods-obj').at(0).attributes('style')).not.toBe(displayNone)
    expect(wrapper.findAll('.sodar-ss-irods-obj').at(1).attributes('style')).not.toBe(displayNone)
    await wrapper.vm.onFilterUpdate('jee8ITh2')
    expect(wrapper.find('#sodar-ss-irods-filter-empty').exists()).toBe(true)
    expect(wrapper.findAll('.sodar-ss-irods-obj').at(0).attributes('style')).toBe(displayNone)
    expect(wrapper.findAll('.sodar-ss-irods-obj').at(1).attributes('style')).toBe(displayNone)
  })

  it('updates modal title on setTitle()', async () => {
    fetchMock.mock(listAjaxUrl, objList)
    const updatedTitle = 'Updated title'
    const wrapper = mount(IrodsDirModal, {
      localVue, propsData: propsData
    })
    wrapper.vm.showModal(rootIrodsPath)
    await waitNT(wrapper.vm)
    await waitRAF()

    expect(wrapper.find('.modal-title').text()).not.toBe(updatedTitle)
    await wrapper.vm.setTitle(updatedTitle)
    expect(wrapper.find('.modal-title').text()).toBe(updatedTitle)
  })

  it('returns relative path to data object on getRelativePath()', () => {
    fetchMock.mock(listAjaxUrl, objList)
    const subCollPath = (
      '/sodarZone/projects/00/00000000-0000-0000-0000-000000000000/' +
      'sample_data/study_11111111-1111-1111-1111-111111111111/' +
      'assay_22222222-2222-2222-2222-222222222222/0815-N1-DNA1/subcoll/test2.txt'
    )
    const wrapper = mount(IrodsDirModal, {
      localVue,
      propsData: propsData
    })
    wrapper.vm.showModal(rootIrodsPath)
    expect(wrapper.vm.getRelativePath(objList.irods_data[0].path)).toBe('')
    expect(wrapper.vm.getRelativePath(subCollPath)).toBe('subcoll')
  })

  it('renders cancel request button as active for correct user', async () => {
    fetchMock.mock(listAjaxUrl, objList)
    const wrapper = mount(IrodsDirModal, {
      localVue, propsData: propsData
    })
    wrapper.vm.showModal(rootIrodsPath)
    await waitNT(wrapper.vm)
    await waitRAF()
    expect(wrapper.find('.sodar-ss-request-cancel-btn').classes()).not.toContain('disabled')
  })

  it('renders cancel request button as inactive for different user', async () => {
    objList.irods_data[0].irods_request_user = '66666666-6666-6666-6666-777777777777'
    fetchMock.mock(listAjaxUrl, objList)
    const wrapper = mount(IrodsDirModal, {
      localVue, propsData: propsData
    })
    wrapper.vm.showModal(rootIrodsPath)
    await waitNT(wrapper.vm)
    await waitRAF()
    expect(wrapper.find('.sodar-ss-request-cancel-btn').classes()).not.toContain('disabled')
  })

  it('handles delete request issuing', async () => {
    fetchMock.mock(listAjaxUrl, objList)
    const wrapper = mount(IrodsDirModal, {
      localVue, propsData: propsData
    })
    wrapper.vm.showModal(rootIrodsPath)
    await waitNT(wrapper.vm)
    await waitRAF()

    expect(wrapper.findAll('.sodar-ss-request-cancel-btn').length).toBe(1)
    wrapper.vm.handleDeleteRequestResponse({ detail: 'ok', status: 'ACTIVE' }, 1)
    await waitNT(wrapper.vm)
    expect(wrapper.findAll('.sodar-ss-request-cancel-btn').length).toBe(2)
  })

  it('handles delete request cancelling', async () => {
    fetchMock.mock(listAjaxUrl, objList)
    const wrapper = mount(IrodsDirModal, {
      localVue, propsData: propsData
    })
    wrapper.vm.showModal(rootIrodsPath)
    await waitNT(wrapper.vm)
    await waitRAF()

    expect(wrapper.findAll('.sodar-ss-request-cancel-btn').length).toBe(1)
    wrapper.vm.handleDeleteRequestResponse({ detail: 'ok', status: null }, 0)
    await waitNT(wrapper.vm)
    expect(wrapper.findAll('.sodar-ss-request-cancel-btn').length).toBe(0)
  })
})
