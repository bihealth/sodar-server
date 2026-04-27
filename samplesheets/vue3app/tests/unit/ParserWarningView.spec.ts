import { beforeEach, describe, expect, test, vi } from 'vitest'
import { mount, type VueWrapper } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

import ParserWarningView from '@/views/ParserWarningView.vue'
import { useAppStore } from '@/stores/appStore.ts'
import { type ParserWarningResponseBody, type SodarContext } from '@/types.ts'

import { copy, waitSelector } from '../testUtils.ts'
import { sodarContext } from '../data/sodarContext.ts'
import parserWarnings from '../data/parserWarnings.json'

const assayFile = 'a_small.txt'
const newLineRegex = /\r\n|\r|\n/g
let fetchBody: ParserWarningResponseBody

describe('ParserWarningView.vue', () => {
  function mountComponent (): VueWrapper {
    global.fetch = vi.fn(() =>
      Promise.resolve({
        json: () => Promise.resolve(fetchBody), status: 200,
      } as Response))
    return mount(ParserWarningView)
  }

  beforeEach(() => {
    setActivePinia(createPinia())
    const appStore = useAppStore()
    appStore.sodarContext = copy(sodarContext) as SodarContext
  })

  test('render component with warnings', async () => {
    fetchBody = copy(parserWarnings) as ParserWarningResponseBody
    const wrapper = mountComponent()
    await waitSelector(wrapper, '#sodar-ss-warnings-card', 1)

    expect(wrapper.find('#sodar-ss-warnings-card').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-warnings-alert-limit').exists()).toBe(false)

    const items = wrapper.findAll('.sodar-ss-warnings-item')
    expect(items.length).toBe(3)

    expect(items[0]?.find('.sodar-ss-warnings-item-source').text()).toBe(
      sodarContext.inv_file_name)
    expect(items[0]?.find('.sodar-ss-warnings-item-message').text()).toBe(
      parserWarnings.warnings.investigation[0]?.message.replace(
        newLineRegex, ''))
    expect(items[0]?.find('.sodar-ss-warnings-item-category').text()).toBe(
      parserWarnings.warnings.investigation[0]?.category)

    expect(items[2]?.find('.sodar-ss-warnings-item-source').text()).toBe(
      assayFile)
    expect(items[2]?.find('.sodar-ss-warnings-item-message').text()).toBe(
      parserWarnings.warnings.assays[assayFile][0]?.message.replace(
        newLineRegex, ''))
    expect(items[2]?.find('.sodar-ss-warnings-item-category').text()).toBe(
      parserWarnings.warnings.assays[assayFile][0]?.category)
  })

  test('render component with limit reached', async () => {
    fetchBody = copy(parserWarnings) as ParserWarningResponseBody
    fetchBody.warnings.limit_reached = true
    const wrapper = mountComponent()
    await waitSelector(wrapper, '#sodar-ss-warnings-card', 1)

    expect(wrapper.find('#sodar-ss-warnings-card').exists()).toBe(true)
    // Limit alert should be visible
    expect(wrapper.find('#sodar-ss-warnings-alert-limit').exists()).toBe(true)
    // Warning content should still be returned
    const items = wrapper.findAll('.sodar-ss-warnings-item')
    expect(items.length).toBe(3)
  })
})
