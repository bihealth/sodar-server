import { createLocalVue, mount } from '@vue/test-utils'
import {
  assayUuid,
  getSheetTablePropsData,
  waitAG //,
  // waitNT,
  // waitRAF
} from '../testUtils.js'
import { BootstrapVue, BButton, BTooltip } from 'bootstrap-vue'
import VueClipboard from 'vue-clipboard2'
import SheetTable from '@/components/SheetTable.vue'

// Set up extended Vue constructor
const localVue = createLocalVue()
localVue.use(BootstrapVue)
localVue.component('b-button', BButton)
localVue.component('b-tooltip', BTooltip)
localVue.use(VueClipboard)

// Init data
// let propsData

describe('SheetTable.vue', () => {
  beforeAll(() => {
    // TODO: Why do we get bootstrap-vue errors?
    // TODO: See https://stackoverflow.com/questions/51536537/running-jest-with-bootstrap-vue
    jest.spyOn(console, 'error').mockImplementation(jest.fn())
    // Disable warnings
    jest.spyOn(console, 'warn').mockImplementation(jest.fn())
  })

  beforeEach(() => {
    jest.resetModules()
    jest.clearAllMocks()
  })

  it('renders study table', async () => {
    const wrapper = mount(SheetTable, {
      localVue,
      propsData: getSheetTablePropsData()
    })
    await waitAG(wrapper)

    // External elements
    expect(wrapper.find('.sodar-ss-data-card').exists()).toBe(true)
    expect(wrapper.find('.sodar-ss-row-insert-btn').exists()).toBe(false)

    // Ag-grid sanity checks
    expect(wrapper.find('#sodar-ss-grid-study').exists()).toBe(true)
    expect(wrapper.findAll('.ag-row').length).toBe(15) // 3x due to pinned cols
  })

  it('renders assay table', async () => {
    const wrapper = mount(SheetTable, {
      localVue,
      propsData: getSheetTablePropsData({ assayMode: true })
    })
    await waitAG(wrapper)

    // External elements
    expect(wrapper.find('.sodar-ss-data-card').exists()).toBe(true)
    expect(wrapper.find('.sodar-ss-row-insert-btn').exists()).toBe(false)

    // Ag-grid sanity checks
    expect(wrapper.find('#sodar-ss-grid-assay-' + assayUuid).exists()).toBe(true)
    expect(wrapper.findAll('.ag-row').length).toBe(6) // 3x due to pinned cols
  })

  it('renders study table in edit mode', async () => {
    const wrapper = mount(SheetTable, {
      localVue,
      propsData: getSheetTablePropsData({ editMode: true })
    })
    await waitAG(wrapper)

    // External elements
    expect(wrapper.find('.sodar-ss-data-card').exists()).toBe(true)
    expect(wrapper.find('.sodar-ss-row-insert-btn').exists()).toBe(true)

    // Ag-grid sanity checks
    expect(wrapper.find('#sodar-ss-grid-study').exists()).toBe(true)
    expect(wrapper.findAll('.ag-row').length).toBe(15)
  })

  it('renders study table in edit mode', async () => {
    const wrapper = mount(SheetTable, {
      localVue,
      propsData: getSheetTablePropsData({ assayMode: true, editMode: true })
    })
    await waitAG(wrapper)

    // External elements
    expect(wrapper.find('.sodar-ss-data-card').exists()).toBe(true)
    expect(wrapper.find('.sodar-ss-row-insert-btn').exists()).toBe(true)

    // Ag-grid sanity checks
    expect(wrapper.find('#sodar-ss-grid-assay-' + assayUuid).exists()).toBe(true)
    expect(wrapper.findAll('.ag-row').length).toBe(6)
  })

  it('calls onColumnToggle() on study table button click', async () => {
    const wrapper = mount(SheetTable, {
      localVue,
      propsData: getSheetTablePropsData()
    })
    const spyOnColumnToggle = jest.spyOn(wrapper.vm, 'onColumnToggle')
    await waitAG(wrapper)
    await wrapper.find('.sodar-ss-column-toggle-btn').trigger('click')

    expect(spyOnColumnToggle).toHaveBeenCalled()
  })

  it('calls onColumnToggle() on assay table button click', async () => {
    const wrapper = mount(SheetTable, {
      localVue,
      propsData: getSheetTablePropsData({ assayMode: true })
    })
    const spyOnColumnToggle = jest.spyOn(wrapper.vm, 'onColumnToggle')
    await waitAG(wrapper)
    await wrapper.find('.sodar-ss-column-toggle-btn').trigger('click')

    expect(spyOnColumnToggle).toHaveBeenCalled()
  })

  it('calls app.handleRowInsert() on study table button click', async () => {
    const wrapper = mount(SheetTable, {
      localVue,
      propsData: getSheetTablePropsData({ editMode: true })
    })
    await waitAG(wrapper)
    const spyHandleRowInsert = jest.spyOn(wrapper.vm.app, 'handleRowInsert')
    await wrapper.find('.sodar-ss-row-insert-btn').trigger('click')

    expect(spyHandleRowInsert).toHaveBeenCalled()
  })

  it('calls app.handleRowInsert() on assay table button click', async () => {
    const wrapper = mount(SheetTable, {
      localVue,
      propsData: getSheetTablePropsData({ assayMode: true, editMode: true })
    })
    await waitAG(wrapper)
    const spyHandleRowInsert = jest.spyOn(wrapper.vm.app, 'handleRowInsert')
    await wrapper.find('.sodar-ss-row-insert-btn').trigger('click')

    expect(spyHandleRowInsert).toHaveBeenCalled()
  })
})
