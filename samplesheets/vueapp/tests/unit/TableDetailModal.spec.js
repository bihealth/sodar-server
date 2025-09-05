import { createLocalVue, mount } from '@vue/test-utils'
import {
  studyUuid,
  assayUuid,
  getAppStub,
  waitNT,
  waitRAF
} from '../testUtils.js'
import BootstrapVue from 'bootstrap-vue'
import TableDetailModal from '@/components/modals/TableDetailModal.vue'

// Set up extended Vue constructor
const localVue = createLocalVue()
localVue.use(BootstrapVue)

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

    expect(wrapper.find('#sodar-ss-table-detail-modal-container').exists()).toBe(true)
    expect(wrapper.findAll('.sodar-ss-table-detail-row').length).toBe(8)
    expect(wrapper.findAll('.sodar-ss-table-detail-legend').length).toBe(8)
    expect(wrapper.findAll('.sodar-ss-table-detail-value').length).toBe(8)
    expect(wrapper.findAll('.sodar-ss-table-detail-value').length).toBe(8)
    // 3 empty values
    expect(wrapper.findAll('.sodar-ss-table-detail-value-empty').length).toBe(3)
    // No comments
    expect(wrapper.findAll('.sodar-ss-table-detail-row-comment').length).toBe(0)
    expect(wrapper.findAll('.sodar-ss-table-detail-legend-comment').length).toBe(0)
    expect(wrapper.findAll('.sodar-ss-table-detail-value-comment').length).toBe(0)
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

    expect(wrapper.find('#sodar-ss-table-detail-modal-container').exists()).toBe(true)
    expect(wrapper.findAll('.sodar-ss-table-detail-row').length).toBe(8)
    // Comments
    expect(wrapper.findAll('.sodar-ss-table-detail-row-comment').length).toBe(2)
    expect(wrapper.findAll('.sodar-ss-table-detail-legend-comment').length).toBe(2)
    expect(wrapper.findAll('.sodar-ss-table-detail-value-comment').length).toBe(2)
    expect(wrapper.findAll('.sodar-ss-table-detail-value-comment-empty').length).toBe(1)
  })
})
