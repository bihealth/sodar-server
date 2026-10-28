import { nextTick } from 'vue'
import { beforeEach, describe, expect, test, vi } from 'vitest'
import { config, mount, type VueWrapper } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { createBootstrap } from 'bootstrap-vue-next/plugins/createBootstrap'

import StudyEditModal from '@/components/modals/StudyEditModal.vue'
import { useAppStore } from '@/stores/appStore.ts'
import {
  AJAX_RES_OK,
  STUDY_UPDATE_OK_MSG,
  URL_STUDY_EDIT_PREFIX,
  VARIANT_DANGER,
  VARIANT_SUCCESS,
} from '@/constants.ts'

import { sodarContext } from '../data/sodarContext.ts'
import { STUDY_UUID } from '../testConstants.ts'

// Test Data -------------------------------------------------------------------

let fetchDetail: string
let fetchStatus: number
const url = URL_STUDY_EDIT_PREFIX + STUDY_UUID

const metaIdSel = '#sodar-ss-study-input-meta-id'
const metaTitleSel = '#sodar-ss-study-input-meta-title'
const metaFileSel = '#sodar-ss-study-input-meta-file'
const metaDescSel = '#sodar-ss-study-input-meta-desc'

// Global Setup ----------------------------------------------------------------

config.global.plugins = [createBootstrap()]
const mockNotifyCb = vi.fn()

// Tests -----------------------------------------------------------------------

describe('StudyEditModal.vue', () => {
  async function showModal (): Promise<VueWrapper> {
    // Mock fetch with current return data
    global.fetch = vi.fn(() => Promise.resolve({
      json: () => Promise.resolve(
        { detail: fetchDetail }), status: fetchStatus} as Response)
    )
    // Mount and return
    const wrapper = mount(StudyEditModal)
    wrapper.vm.show(STUDY_UUID, sodarContext.studies[STUDY_UUID]!)
    await nextTick() // Must wait for all reactive vals to update
    return wrapper
  }

  beforeEach(() => {
    vi.resetAllMocks()
    setActivePinia(createPinia())
    const appStore = useAppStore()
    appStore.notifyCb = mockNotifyCb
    fetchDetail = AJAX_RES_OK
    fetchStatus = 200
  })

  test('render component', async () => {
    const sc = sodarContext.studies[STUDY_UUID]!
    const wrapper = await showModal()
    expect(wrapper.find('#sodar-ss-study-edit-content').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-study-edit-table').exists()).toBe(true)
    expect(wrapper.find(metaIdSel).attributes().value).toBe(sc.identifier)
    expect(wrapper.find(metaTitleSel).attributes().value).toBe(sc.title)
    expect(wrapper.find(metaFileSel).attributes().value).toBe(sc.file_name)
    expect(wrapper.find(metaDescSel).attributes().value).toBe(sc.description)
  })

  test('update study metadata', async () => {
    expect(fetch).not.toHaveBeenCalled()

    const wrapper = await showModal()
    await wrapper.find(metaIdSel).setValue('updated_id')
    await wrapper.find(metaTitleSel).setValue('Updated Title')
    await wrapper.find(metaFileSel).setValue('s_small_update.txt')
    await wrapper.find(metaDescSel).setValue('Updated description')
    await wrapper.find('#sodar-ss-study-edit-btn-update').trigger('click')

    const expMeta = {
      description: 'Updated description',
      file_name: 's_small_update.txt',
      identifier: 'updated_id',
      title: 'Updated Title',
    }
    expect(fetch).toHaveBeenCalledWith(
      url, expect.objectContaining(
        { body: JSON.stringify({ study_meta: expMeta })}))
    expect(mockNotifyCb).toHaveBeenCalledWith(
      STUDY_UPDATE_OK_MSG, VARIANT_SUCCESS)

    // TODO: Assert appStore sodarContext study update once refactored
  })
})
