import { nextTick } from 'vue'
import { beforeEach, describe, expect, test, vi } from 'vitest'
import { config, mount, type VueWrapper } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { createBootstrap } from 'bootstrap-vue-next/plugins/createBootstrap'

import StudyEditModal from '@/components/modals/StudyEditModal.vue'
import { useAppStore } from '@/stores/appStore.ts'
import { type SodarContext } from '@/types.ts'
import {
  AJAX_RES_OK,
  STUDY_UPDATE_OK_MSG,
  URL_STUDY_EDIT_PREFIX,
  // VARIANT_DANGER,
  VARIANT_SUCCESS,
} from '@/constants.ts'

import { sodarContext } from '../data/sodarContext.ts'
import { STUDY_UUID } from '../testConstants.ts'
import { copy } from '../testUtils.ts'

// Test Data -------------------------------------------------------------------

let fetchDetail: string
let fetchStatus: number
const url = URL_STUDY_EDIT_PREFIX + STUDY_UUID

const studyDescUp = 'Updated description'
const studyFileUp = 's_small_update.txt'
const studyIdUp = 'updated_id'
const studyTitleUp = 'Updated Title'

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
    wrapper.vm.show(STUDY_UUID)
    await nextTick() // Must wait for all reactive vals to update
    return wrapper
  }

  beforeEach(() => {
    vi.resetAllMocks()
    setActivePinia(createPinia())
    const appStore = useAppStore()
    appStore.notifyCb = mockNotifyCb
    appStore.sodarContext = copy(sodarContext) as SodarContext
    fetchDetail = AJAX_RES_OK
    fetchStatus = 200
  })

  test('render component', async () => {
    const appStore = useAppStore()
    const sc = appStore.sodarContext!.studies[STUDY_UUID]!
    const wrapper = await showModal()
    expect(wrapper.find('#sodar-ss-study-edit-content').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-study-edit-table').exists()).toBe(true)
    expect(wrapper.find(metaIdSel).attributes().value).toBe(sc.identifier)
    expect(wrapper.find(metaTitleSel).attributes().value).toBe(sc.title)
    expect(wrapper.find(metaFileSel).attributes().value).toBe(sc.file_name)
    expect(wrapper.find(metaDescSel).attributes().value).toBe(sc.description)
  })

  test('update study metadata', async () => {
    const appStore = useAppStore()
    const sc = appStore.sodarContext!.studies[STUDY_UUID]!
    expect(fetch).not.toHaveBeenCalled()

    const wrapper = await showModal()
    await wrapper.find(metaIdSel).setValue(studyIdUp)
    await wrapper.find(metaTitleSel).setValue(studyTitleUp)
    await wrapper.find(metaFileSel).setValue(studyFileUp)
    await wrapper.find(metaDescSel).setValue(studyDescUp)
    await wrapper.find('#sodar-ss-study-edit-btn-update').trigger('click')

    const expMeta = {
      description: studyDescUp,
      file_name: studyFileUp,
      identifier: studyIdUp,
      title: studyTitleUp,
    }
    expect(fetch).toHaveBeenCalledWith(
      url, expect.objectContaining(
        { body: JSON.stringify({ study_meta: expMeta })}))
    expect(mockNotifyCb).toHaveBeenCalledWith(
      STUDY_UPDATE_OK_MSG, VARIANT_SUCCESS)

    expect(sc.identifier).toBe(studyIdUp)
    expect(sc.title).toBe(studyTitleUp)
    expect(sc.file_name).toBe(studyFileUp)
    expect(sc.description).toBe(studyDescUp)
  })

  // TODO: Test update with failed server response
})
