import { beforeEach, describe, expect, test, vi } from 'vitest'
import { config, mount, type VueWrapper } from '@vue/test-utils'
import { createBootstrap } from 'bootstrap-vue-next/plugins/createBootstrap'

import TableDetailListRow from '@/components/TableDetailListRow.vue'
import { COPY_MSG_SUFFIX, VARIANT_INFO } from '@/constants.ts'

import { copy } from '../testUtils.ts'
import { type TableDetailListRowProps } from '../testTypes.ts'

// Test Data -------------------------------------------------------------------

const defaultProps: TableDetailListRowProps = {
  legend: 'Example legend',
  value: 'Example value',
  icon: 'mdi:info',
  iconClass: 'text-info',
  title: 'Example title',
  rowClass: 'example-row-class',
  copyButton: false
}
let props: TableDetailListRowProps

// Global Setup ----------------------------------------------------------------

config.global.plugins = [createBootstrap()]

// Mock clipboard
const mockCopy = vi.fn()
vi.mock('@vueuse/core', async () => {
  const actual = await vi.importActual('@vueuse/core')
  return { ...actual, useClipboard: () => ({ copy: mockCopy }) }
})

// Tests -----------------------------------------------------------------------

describe('TableDetailListRow.vue', () => {
  function mountComponent (): VueWrapper {
    return mount(TableDetailListRow, { props: props })
  }

  beforeEach(() => {
    vi.resetAllMocks()
    props = copy(defaultProps) as TableDetailListRowProps
    props.notifyCb = vi.fn()
  })

  test('render component with default properties', async () => {
    const wrapper = mountComponent()
    expect(wrapper.find('.' + defaultProps.rowClass).exists()).toBe(true)
    const icon = wrapper.find('.sodar-ss-table-detail-legend-content i')
    expect(icon.classes()).toContain(defaultProps.iconClass)
    expect(icon.attributes()['data-icon']).toBe(defaultProps.icon)
    expect(icon.attributes().title).toBe(defaultProps.title)
    expect(wrapper.find(
      '.sodar-ss-table-detail-legend-content').text()).toBe(defaultProps.legend)
    expect(wrapper.find('.sodar-ss-clip-copy-btn').exists()).toBe(false)
    expect(wrapper.find(
      '.sodar-ss-table-detail-value-empty').exists()).toBe(false)
  })

  test('render component with empty value', async () => {
    props.value = ''
    const wrapper = mountComponent()
    expect(wrapper.find(
      '.sodar-ss-table-detail-value-empty').exists()).toBe(true)
  })

  test('display copy button', async () => {
    props.copyButton = true
    const wrapper = mountComponent()
    expect(wrapper.find('.sodar-ss-clip-copy-btn').exists()).toBe(true)
  })

  test('copy value into clipboard', async () => {
    expect(mockCopy).not.toHaveBeenCalled()
    expect(props.notifyCb).not.toHaveBeenCalled()
    props.copyButton = true

    const wrapper = mountComponent()
    await wrapper.find('.sodar-ss-clip-copy-btn').trigger('click')

    expect(mockCopy).toHaveBeenCalledWith(props.value)
    expect(props.notifyCb).toHaveBeenCalledWith(
      'Example legend' + COPY_MSG_SUFFIX, VARIANT_INFO)
  })
})
