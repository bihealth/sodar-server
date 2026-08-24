import { nextTick } from 'vue'
import { beforeEach, describe, expect, test, vi } from 'vitest'
import { config, flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { createBootstrap } from 'bootstrap-vue-next/plugins/createBootstrap'

import VersionSaveModal from '@/components/modals/VersionSaveModal.vue'
import { useAppStore } from '@/stores/appStore.ts'
import { useEditStore } from '@/stores/editStore.ts'
import { type SodarContext } from '@/types.ts'
import {
  AJAX_RES_OK,
  EDIT_MSG_SAVE,
  EDIT_MSG_SAVE_FAIL_PREFIX,
  URL_VERSION_SAVE_PREFIX,
  VARIANT_DANGER,
  VARIANT_SUCCESS,
} from '@/constants.ts'

import { PROJECT_UUID } from '../testConstants.ts'

// Test Data -------------------------------------------------------------------

let fetchDetail: string
let fetchStatus: number
const url = URL_VERSION_SAVE_PREFIX + PROJECT_UUID

// Global Setup ----------------------------------------------------------------

config.global.plugins = [createBootstrap()]
const mockNotifyCb = vi.fn()

// Tests -----------------------------------------------------------------------

describe('VersionSaveModal.vue', () => {
  async function showModal (): Promise<VueWrapper> {
    // Mock fetch with current return data
    global.fetch = vi.fn(() => Promise.resolve({
      json: () => Promise.resolve(
        { detail: fetchDetail }), status: fetchStatus} as Response)
    )
    // Mount and return
    const wrapper = mount(VersionSaveModal)
    wrapper.vm.show()
    await nextTick() // Must wait for all reactive vals to update
    return wrapper
  }

  beforeEach(() => {
    vi.resetAllMocks()

    setActivePinia(createPinia())
    const appStore = useAppStore()
    appStore.notifyCb = mockNotifyCb
    appStore.projectUuid = PROJECT_UUID
    appStore.sodarContext = { csrf_token: 'DummyToken' } as SodarContext
    const editStore = useEditStore()
    editStore.versionSaved = false

    fetchDetail = AJAX_RES_OK
    fetchStatus = 200
  })

  test('render component', async () => {
    const wrapper = await showModal()
    expect(wrapper.find('#sodar-ss-version-save-content').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-version-save-desc').exists()).toBe(true)
  })

  test('save version', async () => {
    const editStore = useEditStore()
    expect(editStore.versionSaved).toBe(false)
    expect(fetch).not.toHaveBeenCalled()
    expect(mockNotifyCb).not.toHaveBeenCalled()

    const wrapper = await showModal()
    await wrapper.find('#sodar-ss-version-btn-update').trigger('click')
    await flushPromises()

    expect(editStore.versionSaved).toBe(true)
    expect(fetch).toHaveBeenCalledWith(
      url, expect.objectContaining({
        body: JSON.stringify({ save: true, description: '' }) }))
    expect(mockNotifyCb).toHaveBeenCalledWith(EDIT_MSG_SAVE, VARIANT_SUCCESS)
  })

  test('save version with description', async () => {
    const editStore = useEditStore()

    const wrapper = await showModal()
    await wrapper.find('#sodar-ss-version-save-desc').setValue('description')
    await wrapper.find('#sodar-ss-version-btn-update').trigger('click')
    await flushPromises()

    expect(editStore.versionSaved).toBe(true)
    expect(fetch).toHaveBeenCalledWith(
      url, expect.objectContaining({
        body: JSON.stringify({ save: true, description: 'description' }) }))
  })

  test('cancel without saving', async () => {
    const editStore = useEditStore()
    const wrapper = await showModal()
    await wrapper.find('#sodar-ss-version-btn-cancel').trigger('click')
    await flushPromises()

    expect(editStore.versionSaved).toBe(false)
    expect(fetch).not.toHaveBeenCalled()
    expect(mockNotifyCb).not.toHaveBeenCalled()
  })

  test('handle save failure', async () => {
    // Suppress logging as error message is expected
    vi.spyOn(console, 'error').mockImplementation(() => undefined)
    const editStore = useEditStore()
    fetchDetail = 'error'
    fetchStatus = 500

    const wrapper = await showModal()
    await wrapper.find('#sodar-ss-version-btn-update').trigger('click')
    await flushPromises()

    expect(editStore.versionSaved).toBe(false)
    expect(fetch).toHaveBeenCalled()
    expect(mockNotifyCb).toHaveBeenCalledWith(
      EDIT_MSG_SAVE_FAIL_PREFIX + 'error', VARIANT_DANGER)
  })
})
