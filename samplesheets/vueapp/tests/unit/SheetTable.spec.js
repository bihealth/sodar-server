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
    // NOTE: Workaround for bootstrap-vue "Vue warn" errors, see issue #1034
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

  it('renders row number', async () => {
    const wrapper = mount(SheetTable, {
      localVue,
      propsData: getSheetTablePropsData()
    })
    await waitAG(wrapper)

    const cells = wrapper.findAll('.sodar-ss-data-row-cell')
    expect(cells.at(0).text()).toBe('1')
    expect(cells.at(0).classes()).toContain('text-right')
    expect(cells.at(0).classes()).toContain('text-muted')
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
