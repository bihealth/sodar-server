import { createLocalVue, mount } from '@vue/test-utils'
import {
  studyUuid,
  assayUuid,
  getAppStub,
  waitNT,
  waitRAF
} from '../testUtils.js'
import BootstrapVue from 'bootstrap-vue'
import VueClipboard from 'vue-clipboard2'
import TableDetailModal from '@/components/modals/TableDetailModal.vue'

// Set up extended Vue constructor
const localVue = createLocalVue()
localVue.use(BootstrapVue)
localVue.use(VueClipboard)

describe('TableDetailModal.vue', () => {
  beforeEach(() => {
    jest.resetModules()
    jest.clearAllMocks()
  })

  it('renders modal with assay details', async () => {
    const wrapper = mount(
      TableDetailModal, { localVue, propsData: { app: getAppStub() } })
    wrapper.vm.showModal(studyUuid, assayUuid)
    await waitNT(wrapper.vm)
    await waitRAF()

    expect(wrapper.find('#sodar-ss-table-detail-container').exists()).toBe(true)
    expect(wrapper.findAll('.sodar-ss-table-detail-row').length).toBe(9)
    expect(wrapper.findAll('.sodar-ss-table-detail-legend').length).toBe(9)
    expect(wrapper.findAll('.sodar-ss-table-detail-value').length).toBe(9)
    expect(wrapper.findAll('.sodar-ss-table-detail-value-empty').length).toBe(3)
    expect(wrapper.findAll('.sodar-ss-table-detail-row-meta').length).toBe(4)
    expect(wrapper.findAll('.sodar-ss-table-detail-row-comment').length).toBe(0)
    expect(wrapper.findAll('.sodar-ss-table-detail-row-sodar').length).toBe(5)
  })

  it('renders modal with study details', async () => {
    const wrapper = mount(
      TableDetailModal, { localVue, propsData: { app: getAppStub() } })
    wrapper.vm.showModal(studyUuid, studyUuid) // NOTE: Same UUID for both
    await waitNT(wrapper.vm)
    await waitRAF()

    expect(wrapper.find('#sodar-ss-table-detail-container').exists()).toBe(true)
    expect(wrapper.findAll('.sodar-ss-table-detail-row').length).toBe(10)
    expect(wrapper.findAll('.sodar-ss-table-detail-value-empty').length).toBe(5)
    expect(wrapper.findAll('.sodar-ss-table-detail-row-meta').length).toBe(4)
    expect(wrapper.findAll('.sodar-ss-table-detail-row-comment').length).toBe(2)
    expect(wrapper.findAll('.sodar-ss-table-detail-row-sodar').length).toBe(4)
  })

  it('renders modal with assay comments', async () => {
    const app = getAppStub()
    app.sodarContext.studies[studyUuid].assays[assayUuid].comments = {
      'Test Comment': 'xxx', 'Empty Comment': ''
    }
    const wrapper = mount(
      TableDetailModal, { localVue, propsData: { app: app } })
    wrapper.vm.showModal(studyUuid, assayUuid)
    await waitNT(wrapper.vm)
    await waitRAF()

    expect(wrapper.find('#sodar-ss-table-detail-container').exists()).toBe(true)
    expect(wrapper.findAll('.sodar-ss-table-detail-row').length).toBe(11)
    expect(wrapper.findAll('.sodar-ss-table-detail-row-comment').length).toBe(2)
    expect(wrapper.findAll('.sodar-ss-table-detail-value-empty').length).toBe(4)
  })
})
