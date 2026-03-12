import { beforeEach, describe, expect, test } from 'vitest'
import { config, mount, type VueWrapper } from '@vue/test-utils'
import { createBootstrap } from 'bootstrap-vue-next/plugins/createBootstrap'

import TableDetailListRow from '@/components/TableDetailListRow.vue'
import { copy } from '../testUtils.ts'
import { type TableDetailListRowProps } from '../testTypes.ts'

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

config.global.plugins = [createBootstrap()]

describe('TableDetailListRow.vue', () => {
  function mountComponent (): VueWrapper {
    return mount(TableDetailListRow, { props: props })
  }
  beforeEach(() => {
    props = copy(defaultProps) as TableDetailListRowProps
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

  // TODO: Test clipboard copying
})
