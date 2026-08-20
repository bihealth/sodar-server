import { nextTick } from 'vue'
import { beforeEach, describe, expect, test, vi } from 'vitest'
import { config, mount, type VueWrapper } from '@vue/test-utils'
import { createBootstrap } from 'bootstrap-vue-next/plugins/createBootstrap'

import WinExportModal from '@/components/modals/WinExportModal.vue'

import { PROJECT_UUID } from '../testConstants.ts'

// Global Setup ----------------------------------------------------------------

config.global.plugins = [createBootstrap()]

// Tests -----------------------------------------------------------------------

describe('WinExportModal.vue', () => {
  beforeEach(() => {
    Object.defineProperty(
      window, 'location', { value: vi.fn(), configurable: true })
  })

  async function showModal (): Promise<VueWrapper> {
    const wrapper = mount(
      WinExportModal, { props: { projectUuid: PROJECT_UUID } })
    wrapper.vm.show()
    await nextTick() // Must wait for all reactive vals to update
    return wrapper
  }

  test('render component', async () => {
    const wrapper = await showModal()
    expect(wrapper.find('#sodar-ss-win-export-modal').exists()).toBe(true)
    expect(wrapper.find(
      '#sodar-ss-win-export-modal-content').exists()).toBe(true)
  })

  test('redirect browser on button click', async () => {
    const wrapper = await showModal()
    const btn = wrapper.find('#sodar-ss-win-export-btn')
    await btn.trigger('click')
    expect(window.location.href).toContain('export/isa/' + PROJECT_UUID)
  })
})
