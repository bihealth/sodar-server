import { nextTick } from 'vue'
import { beforeEach, describe, expect, test, vi } from 'vitest'
import { config, mount, type VueWrapper } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { createBootstrap } from 'bootstrap-vue-next/plugins/createBootstrap'

import AssayEditModal from '@/components/modals/AssayEditModal.vue'
import { useAppStore } from '@/stores/appStore.ts'
import { type SodarContext } from '@/types.ts'
import {
  AJAX_RES_OK,
  ASSAY_UPDATE_FAIL_PREFIX,
  ASSAY_UPDATE_OK_MSG,
  SODAR_ISA_ASSAY_DISPLAY_NAME,
  URL_ASSAY_EDIT_PREFIX,
  VARIANT_DANGER,
  VARIANT_SUCCESS,
} from '@/constants.ts'

import { sodarContext } from '../data/sodarContext.ts'
import { ASSAY_UUID, STUDY_UUID } from '../testConstants.ts'
import { copy } from '../testUtils.ts'

// Test Data -------------------------------------------------------------------

let fetchDetail: string
let fetchStatus: number
const url = URL_ASSAY_EDIT_PREFIX + ASSAY_UUID

const metaFileUp = 'a_small_update.txt'
const metaTechPlatUp = 'Sequencer McSequencerface 9000'

const metaFileSel = '#sodar-ss-assay-input-meta-file'
const metaTechPlatSel = '#sodar-ss-assay-input-meta-tech-platform'
const updateBtnSel = '#sodar-ss-assay-edit-btn-update'

const INVALID_CLASS = 'text-danger'

// Global Setup ----------------------------------------------------------------

config.global.plugins = [createBootstrap()]
const mockNotifyCb = vi.fn()

// Tests -----------------------------------------------------------------------

describe('AssayEditModal.vue', () => {
  async function showModal(): Promise<VueWrapper> {
    // Mock fetch with current return data
    global.fetch = vi.fn(() => Promise.resolve({
        json: () => Promise.resolve(
          {detail: fetchDetail}), status: fetchStatus
      } as Response)
    )
    // Mount and return
    const wrapper = mount(AssayEditModal)
    wrapper.vm.show(ASSAY_UUID)
    await nextTick() // Must wait for all reactive vals to update
    return wrapper
  }

  beforeEach(() => {
    vi.resetAllMocks()
    setActivePinia(createPinia())

    const appStore = useAppStore()
    appStore.currentStudyUuid = STUDY_UUID
    appStore.notifyCb = mockNotifyCb
    appStore.sodarContext = copy(sodarContext) as SodarContext

    fetchDetail = AJAX_RES_OK
    fetchStatus = 200
  })

  test('render component', async () => {
    const appStore = useAppStore()
    const ac = appStore.sodarContext!.studies[STUDY_UUID]!.assays[ASSAY_UUID]!
    const wrapper = await showModal()
    expect(wrapper.find('#sodar-ss-assay-edit-content').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-assay-edit-table').exists()).toBe(true)
    expect(wrapper.find(metaFileSel).attributes().value).toBe(ac.file_name)
    expect(wrapper.find(
      metaTechPlatSel).attributes().value).toBe(ac.technology_platform)
    expect(wrapper.find(updateBtnSel).attributes().disabled).not.toBeDefined()
  })

  test('update assay metadata', async () => {
    const appStore = useAppStore()
    const ac = appStore.sodarContext!.studies[STUDY_UUID]!.assays[ASSAY_UUID]!
    expect(ac.comments).toBe(null)
    expect(fetch).not.toHaveBeenCalled()

    const wrapper = await showModal()
    await wrapper.find(metaFileSel).setValue(metaFileUp)
    await wrapper.find(metaTechPlatSel).setValue(metaTechPlatUp)
    await wrapper.find('#sodar-ss-assay-edit-btn-update').trigger('click')

    const expMeta = {
      file_name: metaFileUp,
      technology_platform: metaTechPlatUp,
    }
    expect(fetch).toHaveBeenCalledWith(
      url, expect.objectContaining(
        { body: JSON.stringify({ assay_meta: expMeta })}))
    expect(mockNotifyCb).toHaveBeenCalledWith(
      ASSAY_UPDATE_OK_MSG, VARIANT_SUCCESS)

    expect(ac.file_name).toBe(metaFileUp)
    expect(ac.technology_platform).toBe(metaTechPlatUp)
    // No override in comments = display name should be updated
    expect(ac.display_name).toBe('Small Update')
  })

  test('update file name with metadata display name set', async () => {
    const appStore = useAppStore()
    const ac = appStore.sodarContext!.studies[STUDY_UUID]!.assays[ASSAY_UUID]!
    ac.comments = { [SODAR_ISA_ASSAY_DISPLAY_NAME]: 'Small' }
    expect(ac.display_name).toBe('Small')

    const wrapper = await showModal()
    expect(fetch).not.toHaveBeenCalled()
    await wrapper.find(metaFileSel).setValue(metaFileUp)
    await wrapper.find(metaTechPlatSel).setValue(metaTechPlatUp)
    await wrapper.find('#sodar-ss-assay-edit-btn-update').trigger('click')

    expect(fetch).toHaveBeenCalled()
    expect(ac.technology_platform).toBe(metaTechPlatUp)
    // Override in comments = display name should remain
    expect(ac.display_name).toBe('Small')
  })

  test('handle failed update', async () => {
    // Suppress logging as error message is expected
    vi.spyOn(console, 'error').mockImplementation(() => undefined)
    const appStore = useAppStore()
    const ac = appStore.sodarContext!.studies[STUDY_UUID]!.assays[ASSAY_UUID]!
    // Original unaltered data
    const og = sodarContext.studies[STUDY_UUID]!.assays[ASSAY_UUID]!
    fetchDetail = 'Error'
    fetchStatus = 400

    const wrapper = await showModal()
    await wrapper.find(metaFileSel).setValue(metaFileUp)
    await wrapper.find(metaTechPlatSel).setValue(metaTechPlatUp)
    await wrapper.find('#sodar-ss-assay-edit-btn-update').trigger('click')

    expect(fetch).toHaveBeenCalled()
    expect(mockNotifyCb).toHaveBeenCalledWith(
      ASSAY_UPDATE_FAIL_PREFIX + 'Error', VARIANT_DANGER)

    // Original values should be retained
    expect(ac.file_name).toBe(og.file_name)
    expect(ac.technology_platform).toBe(og.technology_platform)
  })

  test('cancel assay metadata update', async () => {
    const appStore = useAppStore()
    const ac = appStore.sodarContext!.studies[STUDY_UUID]!.assays[ASSAY_UUID]!
    const og = sodarContext.studies[STUDY_UUID]!.assays[ASSAY_UUID]!

    const wrapper = await showModal()
    await wrapper.find(metaFileSel).setValue(metaFileUp)
    await wrapper.find(metaTechPlatSel).setValue(metaTechPlatUp)
    await wrapper.find('#sodar-ss-assay-edit-btn-cancel').trigger('click')

    expect(fetch).not.toHaveBeenCalled()
    expect(ac.file_name).toBe(og.file_name)
    expect(ac.technology_platform).toBe(og.technology_platform)
  })

  test('input valid file name', async () => {
    const wrapper = await showModal()
    const input = wrapper.find(metaFileSel)
    await input.setValue('a_new_name.txt')
    expect(input.classes()).not.toContain(INVALID_CLASS)
    expect(wrapper.find(updateBtnSel).attributes().disabled).not.toBeDefined()
  })

  test('input file name with invalid prefix', async () => {
    const wrapper = await showModal()
    const input = wrapper.find(metaFileSel)
    await input.setValue('s_new_name.txt') // Not starting with "a_"
    expect(input.classes()).toContain(INVALID_CLASS)
    expect(wrapper.find(updateBtnSel).attributes().disabled).toBeDefined()
  })

  test('input file name with invalid suffix', async () => {
    const wrapper = await showModal()
    const input = wrapper.find(metaFileSel)
    await input.setValue('a_new_name.tsv') // Not ending with ".txt"
    expect(input.classes()).toContain(INVALID_CLASS)
    expect(wrapper.find(updateBtnSel).attributes().disabled).toBeDefined()
  })

  test('input empty file name', async () => {
    const wrapper = await showModal()
    const input = wrapper.find(metaFileSel)
    await input.setValue('')
    expect(wrapper.find(updateBtnSel).attributes().disabled).toBeDefined()
  })

  test('input file name with whitespace', async () => {
    const wrapper = await showModal()
    const input = wrapper.find(metaFileSel)
    await input.setValue('a_new name.txt')
    expect(input.classes()).toContain(INVALID_CLASS)
    expect(wrapper.find(updateBtnSel).attributes().disabled).toBeDefined()
  })

  test('input file name with disallowed characters', async () => {
    const wrapper = await showModal()
    const input = wrapper.find(metaFileSel)
    await input.setValue('a_(new)_name.txt')
    expect(input.classes()).toContain(INVALID_CLASS)
    expect(wrapper.find(updateBtnSel).attributes().disabled).toBeDefined()
  })
})
