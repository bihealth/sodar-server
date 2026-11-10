import { nextTick } from 'vue'
import { beforeEach, describe, expect, test, vi } from 'vitest'
import { config, mount, type VueWrapper } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { createBootstrap } from 'bootstrap-vue-next/plugins/createBootstrap'

import AssayEditModal from '@/components/modals/AssayEditModal.vue'
import { useAppStore } from '@/stores/appStore.ts'
import { useEditStore } from '@/stores/editStore.ts'
import {
  type SodarContext,
  type SodarContextAssay,
  type SodarContextComments
} from '@/types.ts'
import {
  AJAX_RES_OK,
  ASSAY_UPDATE_FAIL_PREFIX,
  ASSAY_UPDATE_OK_MSG,
  SODAR_ISA_ASSAY_DISPLAY_NAME,
  SODAR_ISA_ASSAY_LINK_ROW,
  SODAR_ISA_ASSAY_PATH_PREFIX,
  SODAR_ISA_ASSAY_PLUGIN,
  URL_ASSAY_UPDATE_PREFIX,
  VARIANT_DANGER,
  VARIANT_SUCCESS,
} from '@/constants.ts'

import { sodarContext } from '../data/sodarContext.ts'
import { ASSAY_UUID, STUDY_UUID, TMP_UUID } from '../testConstants.ts'
import { copy } from '../testUtils.ts'

// Test Data -------------------------------------------------------------------

let fetchDetail: string
let fetchStatus: number
const url = URL_ASSAY_UPDATE_PREFIX + ASSAY_UUID

const defaultComments: SodarContextComments = {
  [SODAR_ISA_ASSAY_DISPLAY_NAME]: 'Custom Assay Name',
  'Test Assay Comment': 'test value',
}

const metaFileUp = 'a_small_update.txt'
const metaTechPlatUp = 'Sequencer McSequencerface 9000'
const pluginName = 'samplesheets_assay_dna_sequencing'

const metaFileSel = '#sodar-ss-assay-input-meta-file'
const metaTechPlatSel = '#sodar-ss-assay-input-meta-tech-platform'
const commInputSel = '.sodar-ss-isa-comment-input'
const commInsKeySel = '.sodar-ss-isa-comment-insert-key'
const commInsValSel = '.sodar-ss-isa-comment-insert-value'
const commInsBtnSel = '.sodar-ss-isa-comment-insert-btn'
const commDelBtnSel = '.sodar-ss-isa-comment-delete-btn'
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
    appStore.sodarContext.studies[STUDY_UUID]!.assays[
      ASSAY_UUID]!.comments = copy(defaultComments) as SodarContextComments

    fetchDetail = AJAX_RES_OK
    fetchStatus = 200
  })

  test('render component', async () => {
    const appStore = useAppStore()
    const ac = appStore.sodarContext!.studies[STUDY_UUID]!.assays[ASSAY_UUID]!
    const wrapper = await showModal()
    expect(wrapper.find('#sodar-ss-assay-edit-content').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-assay-edit-table').exists()).toBe(true)
    expect(wrapper.find('.sodar-ss-isa-comment-edit-body').exists()).toBe(true)
    expect(wrapper.find(metaFileSel).attributes().value).toBe(ac.file_name)
    expect(wrapper.find(
      metaTechPlatSel).attributes().value).toBe(ac.technology_platform)
    expect(wrapper.find(updateBtnSel).attributes().disabled).not.toBeDefined()
  })

  test('render component with null comments', async () => {
    const appStore = useAppStore()
    const ac = appStore.sodarContext!.studies[STUDY_UUID]!.assays[ASSAY_UUID]!
    ac.comments = null
    const wrapper = await showModal()
    expect(wrapper.find('.sodar-ss-isa-comment-edit-body').exists()).toBe(true)
  })

  test('update assay metadata', async () => {
    const appStore = useAppStore()
    const editStore = useEditStore()
    const ac = appStore.sodarContext!.studies[STUDY_UUID]!.assays[ASSAY_UUID]!
    expect(ac.comments).toEqual(defaultComments)
    expect(editStore.updateCache).toBe(false)

    const wrapper = await showModal()
    expect(fetch).not.toHaveBeenCalled()
    await wrapper.find(metaFileSel).setValue(metaFileUp)
    await wrapper.find(metaTechPlatSel).setValue(metaTechPlatUp)
    await wrapper.find('#sodar-ss-assay-edit-btn-update').trigger('click')

    const expMeta = {
      file_name: metaFileUp,
      technology_platform: metaTechPlatUp,
    }
    expect(fetch).toHaveBeenCalledWith(
      url, expect.objectContaining({
        body: JSON.stringify({
          assay_meta: expMeta,
          comments: defaultComments })}))
    expect(mockNotifyCb).toHaveBeenCalledWith(
      ASSAY_UPDATE_OK_MSG, VARIANT_SUCCESS)

    expect(ac.file_name).toBe(metaFileUp)
    expect(ac.technology_platform).toBe(metaTechPlatUp)
    // Display name updated to override
    expect(ac.display_name).toBe(defaultComments[SODAR_ISA_ASSAY_DISPLAY_NAME])
    expect(editStore.updateCache).toBe(false) // Should be unchanged
  })

    test('update assay metadata with empty display name', async () => {
    const appStore = useAppStore()
    const ac = appStore.sodarContext!.studies[STUDY_UUID]!.assays[ASSAY_UUID]!
    ac.comments![SODAR_ISA_ASSAY_DISPLAY_NAME] = ''

    const wrapper = await showModal()
    await wrapper.find(metaFileSel).setValue(metaFileUp)
    await wrapper.find(metaTechPlatSel).setValue(metaTechPlatUp)
    await wrapper.find('#sodar-ss-assay-edit-btn-update').trigger('click')

    const expMeta = {
      file_name: metaFileUp,
      technology_platform: metaTechPlatUp,
    }
    const expComments = {
      [SODAR_ISA_ASSAY_DISPLAY_NAME]: '',
      'Test Assay Comment': 'test value',
    }
    expect(fetch).toHaveBeenCalledWith(
      url, expect.objectContaining({
        body: JSON.stringify({
          assay_meta: expMeta,
          comments: expComments })}))
    expect(mockNotifyCb).toHaveBeenCalledWith(
      ASSAY_UPDATE_OK_MSG, VARIANT_SUCCESS)

    expect(ac.file_name).toBe(metaFileUp)
    expect(ac.technology_platform).toBe(metaTechPlatUp)
    // No override = display name updated to match assay name
    expect(ac.display_name).toBe('Small Update')
  })

  test('update file name with metadata display name set', async () => {
    const appStore = useAppStore()
    const ac = appStore.sodarContext!.studies[STUDY_UUID]!.assays[ASSAY_UUID]!
    ac.comments = { [SODAR_ISA_ASSAY_DISPLAY_NAME]: 'Small' }
    expect(ac.display_name).toBe('Small')

    const wrapper = await showModal()
    await wrapper.find(metaFileSel).setValue(metaFileUp)
    await wrapper.find(metaTechPlatSel).setValue(metaTechPlatUp)
    await wrapper.find('#sodar-ss-assay-edit-btn-update').trigger('click')

    expect(fetch).toHaveBeenCalled()
    expect(ac.technology_platform).toBe(metaTechPlatUp)
    // Override in comments = display name should remain
    expect(ac.display_name).toBe('Small')
  })

  test('update assay comments with plugin name inserted', async () => {
    const editStore = useEditStore()
    expect(editStore.updateCache).toBe(false)

    const wrapper = await showModal()
    await wrapper.find(commInsKeySel).setValue(SODAR_ISA_ASSAY_PLUGIN)
    await wrapper.find(commInsValSel).setValue(pluginName)
    await wrapper.find(commInsBtnSel).trigger('click')
    await wrapper.find('#sodar-ss-assay-edit-btn-update').trigger('click')

    expect(fetch).toHaveBeenCalled()
    expect(mockNotifyCb).toHaveBeenCalledWith(
      ASSAY_UPDATE_OK_MSG, VARIANT_SUCCESS)
    expect(editStore.updateCache).toBe(true) // Should be updated
  })

  test('update assay comments with plugin name unchanged', async () => {
    const appStore = useAppStore()
    const editStore = useEditStore()
    const comments = appStore.sodarContext!.studies[STUDY_UUID]!.assays[
      ASSAY_UUID]!.comments as SodarContextComments
    comments[SODAR_ISA_ASSAY_PLUGIN] = pluginName
    expect(editStore.updateCache).toBe(false)

    const wrapper = await showModal()
    await wrapper.find(metaFileSel).setValue(metaFileUp)
    await wrapper.find(commInsBtnSel).trigger('click')
    await wrapper.find('#sodar-ss-assay-edit-btn-update').trigger('click')

    expect(fetch).toHaveBeenCalled()
    expect(mockNotifyCb).toHaveBeenCalledWith(
      ASSAY_UPDATE_OK_MSG, VARIANT_SUCCESS)
    expect(editStore.updateCache).toBe(false) // Should be unchanged
  })

  test('update assay comments with plugin name changed', async () => {
    const appStore = useAppStore()
    const editStore = useEditStore()
    const comments = appStore.sodarContext!.studies[STUDY_UUID]!.assays[
      ASSAY_UUID]!.comments as SodarContextComments
    comments[SODAR_ISA_ASSAY_PLUGIN] = pluginName
    expect(editStore.updateCache).toBe(false)

    const wrapper = await showModal()
    const commFields = wrapper.findAll(commInputSel)
    await commFields![2]!.setValue('updated_plugin_name')
    await wrapper.find('#sodar-ss-assay-edit-btn-update').trigger('click')

    expect(fetch).toHaveBeenCalled()
    expect(mockNotifyCb).toHaveBeenCalledWith(
      ASSAY_UPDATE_OK_MSG, VARIANT_SUCCESS)
    expect(editStore.updateCache).toBe(true) // Should be updated
  })

  test('update comments with generic plugin link row inserted', async () => {
    const editStore = useEditStore()
    expect(editStore.updateCache).toBe(false)

    const wrapper = await showModal()
    await wrapper.find(commInsKeySel).setValue(SODAR_ISA_ASSAY_LINK_ROW)
    await wrapper.find(commInsValSel).setValue('abc;def')
    await wrapper.find(commInsBtnSel).trigger('click')
    await wrapper.find('#sodar-ss-assay-edit-btn-update').trigger('click')

    expect(fetch).toHaveBeenCalled()
    expect(mockNotifyCb).toHaveBeenCalledWith(
      ASSAY_UPDATE_OK_MSG, VARIANT_SUCCESS)
    expect(editStore.updateCache).toBe(true) // Should be updated
  })

  test('update comments with generic plugin row path inserted', async () => {
    const editStore = useEditStore()
    expect(editStore.updateCache).toBe(false)

    const wrapper = await showModal()
    await wrapper.find(commInsKeySel).setValue(
      SODAR_ISA_ASSAY_PATH_PREFIX + ' 1')
    await wrapper.find(commInsValSel).setValue('abc')
    await wrapper.find(commInsBtnSel).trigger('click')
    await wrapper.find('#sodar-ss-assay-edit-btn-update').trigger('click')

    expect(fetch).toHaveBeenCalled()
    expect(mockNotifyCb).toHaveBeenCalledWith(
      ASSAY_UPDATE_OK_MSG, VARIANT_SUCCESS)
    expect(editStore.updateCache).toBe(true) // Should be updated
  })

  test('update comments with generic plugin row path deleted', async () => {
    const appStore = useAppStore()
    const editStore = useEditStore()
    const comments = appStore.sodarContext!.studies[STUDY_UUID]!.assays[
      ASSAY_UUID]!.comments as SodarContextComments
    comments[SODAR_ISA_ASSAY_PATH_PREFIX + ' 1'] = 'abc'
    expect(editStore.updateCache).toBe(false)

    const wrapper = await showModal()
    const delButtons = wrapper.findAll(commDelBtnSel)
    expect(delButtons.length).toBe(3)
    await delButtons![2]!.trigger('click')
    await wrapper.find('#sodar-ss-assay-edit-btn-update').trigger('click')

    expect(fetch).toHaveBeenCalled()
    expect(mockNotifyCb).toHaveBeenCalledWith(
      ASSAY_UPDATE_OK_MSG, VARIANT_SUCCESS)
    expect(editStore.updateCache).toBe(true) // Should be updated
  })

  test('update comments with generic plugin row path changed', async () => {
    const appStore = useAppStore()
    const editStore = useEditStore()
    const comments = appStore.sodarContext!.studies[STUDY_UUID]!.assays[
      ASSAY_UUID]!.comments as SodarContextComments
    comments[SODAR_ISA_ASSAY_PATH_PREFIX + ' 1'] = 'abc'
    expect(editStore.updateCache).toBe(false)

    const wrapper = await showModal()
    const commFields = wrapper.findAll(commInputSel)
    await commFields![2]!.setValue('def')
    await wrapper.find('#sodar-ss-assay-edit-btn-update').trigger('click')

    expect(fetch).toHaveBeenCalled()
    expect(mockNotifyCb).toHaveBeenCalledWith(
      ASSAY_UPDATE_OK_MSG, VARIANT_SUCCESS)
    expect(editStore.updateCache).toBe(true) // Should be updated
  })

  test('update comments with generic plugin row path unchanged', async () => {
    const appStore = useAppStore()
    const editStore = useEditStore()
    const comments = appStore.sodarContext!.studies[STUDY_UUID]!.assays[
      ASSAY_UUID]!.comments as SodarContextComments
    comments[SODAR_ISA_ASSAY_PATH_PREFIX + ' 1'] = 'abc'
    expect(editStore.updateCache).toBe(false)

    const wrapper = await showModal()
    await wrapper.find('#sodar-ss-assay-edit-btn-update').trigger('click')

    expect(fetch).toHaveBeenCalled()
    expect(mockNotifyCb).toHaveBeenCalledWith(
      ASSAY_UPDATE_OK_MSG, VARIANT_SUCCESS)
    expect(editStore.updateCache).toBe(false) // Should be unchanged
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

  test('cancel assay property update', async () => {
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

  test('input duplicate file name', async () => {
    const appStore = useAppStore()
    const assay = copy(appStore.sodarContext!.studies[STUDY_UUID]!.assays[
        ASSAY_UUID]!) as SodarContextAssay
    assay.file_name = metaFileUp
    appStore.sodarContext!.studies[STUDY_UUID]!.assays[TMP_UUID] = assay

    const wrapper = await showModal()
    const input = wrapper.find(metaFileSel)
    await input.setValue(metaFileUp)
    expect(input.classes()).toContain(INVALID_CLASS)
    expect(wrapper.find(updateBtnSel).attributes().disabled).toBeDefined()
  })
})
