import { nextTick } from 'vue'
import { beforeEach, describe, expect, test, vi } from 'vitest'
import { config, mount, type VueWrapper } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { createBootstrap } from 'bootstrap-vue-next/plugins/createBootstrap'

import InvestigationEditModal from '@/components/modals/InvestigationEditModal.vue'
import { useAppStore } from '@/stores/appStore.ts'
import {
  type SodarContext,
  type SodarContextInvestigation,
} from '@/types.ts'
import {
  AJAX_RES_OK,
  INV_UPDATE_FAIL_PREFIX,
  INV_UPDATE_OK_MSG,
  URL_INV_UPDATE_PREFIX,
  VARIANT_DANGER,
  VARIANT_SUCCESS,
} from '@/constants.ts'

import { sodarContext } from '../data/sodarContext.ts'
import { INV_UUID } from '../testConstants.ts'
import { copy } from '../testUtils.ts'


// Test Data -------------------------------------------------------------------

let fetchDetail: string
let fetchStatus: number
const url = URL_INV_UPDATE_PREFIX + INV_UUID

const metaDescUp = 'Updated description'
const metaFileUp = 'i_small_update.txt'
const metaIdUp = 'updated_id'
const metaPubDateUp = '2026-02-02'
const metaSubDateUp = '2026-01-01'
const metaTitleUp = 'Updated Title'

const metaIdSel = '#sodar-ss-inv-input-meta-id'
const metaTitleSel = '#sodar-ss-inv-input-meta-title'
const metaFileSel = '#sodar-ss-inv-input-meta-file'
const metaDescSel = '#sodar-ss-inv-input-meta-desc'
const metaSubDateSel = '#sodar-ss-inv-input-meta-sub-date'
const metaPubDateSel = '#sodar-ss-inv-input-meta-pub-date'
const updateBtnSel = '#sodar-ss-inv-edit-btn-update'

const INVALID_CLASS = 'text-danger'

// Global Setup ----------------------------------------------------------------

config.global.plugins = [createBootstrap()]
const mockNotifyCb = vi.fn()

// Tests -----------------------------------------------------------------------

describe('InvestigationEditModal.vue', () => {
  async function showModal (): Promise<VueWrapper> {
    // Mock fetch with current return data
    global.fetch = vi.fn(() => Promise.resolve({
      json: () => Promise.resolve(
        { detail: fetchDetail }), status: fetchStatus} as Response)
    )
    // Mount and return
    const wrapper = mount(InvestigationEditModal)
    wrapper.vm.show()
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
    const ic = appStore.sodarContext!.investigation as SodarContextInvestigation
    const wrapper = await showModal()
    expect(wrapper.find('#sodar-ss-inv-edit-content').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-inv-edit-table').exists()).toBe(true)
    expect(wrapper.find(metaIdSel).attributes().value).toBe(ic.identifier)
    expect(wrapper.find(metaTitleSel).attributes().value).toBe(ic.title)
    expect(wrapper.find(metaFileSel).attributes().value).toBe(
      appStore.sodarContext!.inv_file_name)
    expect(wrapper.find(metaDescSel).attributes().value).toBe(ic.description)
    expect(wrapper.find(
      metaSubDateSel).attributes().value).toBe(ic.submission_date)
    expect(wrapper.find(
      metaPubDateSel).attributes().value).toBe(ic.public_release_date)
    expect(wrapper.find(updateBtnSel).attributes().disabled).not.toBeDefined()
  })

  test('update study metadata', async () => {
    const appStore = useAppStore()
    const ic = appStore.sodarContext!.investigation as SodarContextInvestigation

    const wrapper = await showModal()
    expect(fetch).not.toHaveBeenCalled()
    await wrapper.find(metaIdSel).setValue(metaIdUp)
    await wrapper.find(metaTitleSel).setValue(metaTitleUp)
    await wrapper.find(metaFileSel).setValue(metaFileUp)
    await wrapper.find(metaDescSel).setValue(metaDescUp)
    await wrapper.find(metaSubDateSel).setValue(metaSubDateUp)
    await wrapper.find(metaPubDateSel).setValue(metaPubDateUp)
    await wrapper.find('#sodar-ss-inv-edit-btn-update').trigger('click')

    const expMeta = {
      description: metaDescUp,
      file_name: metaFileUp,
      identifier: metaIdUp,
      public_release_date: metaPubDateUp,
      submission_date: metaSubDateUp,
      title: metaTitleUp,
    }
    expect(fetch).toHaveBeenCalledWith(
      url, expect.objectContaining(
        { body: JSON.stringify({ inv_meta: expMeta })}))
    expect(mockNotifyCb).toHaveBeenCalledWith(
      INV_UPDATE_OK_MSG, VARIANT_SUCCESS)

    expect(ic.identifier).toBe(metaIdUp)
    expect(ic.title).toBe(metaTitleUp)
    expect(appStore.sodarContext!.inv_file_name).toBe(metaFileUp)
    expect(ic.description).toBe(metaDescUp)
    expect(ic.submission_date).toBe(metaSubDateUp)
    expect(ic.public_release_date).toBe(metaPubDateUp)
  })

  test('handle failed update', async () => {
    // Suppress logging as error message is expected
    vi.spyOn(console, 'error').mockImplementation(() => undefined)
    const appStore = useAppStore()
    const ic = appStore.sodarContext!.investigation as SodarContextInvestigation
    const og = sodarContext.investigation! as SodarContextInvestigation
    const og_file_name = sodarContext.inv_file_name
    fetchDetail = 'Error'
    fetchStatus = 400

    const wrapper = await showModal()
    await wrapper.find(metaIdSel).setValue(metaIdUp)
    await wrapper.find(metaTitleSel).setValue(metaTitleUp)
    await wrapper.find(metaFileSel).setValue(metaFileUp)
    await wrapper.find(metaDescSel).setValue(metaDescUp)
    await wrapper.find('#sodar-ss-inv-edit-btn-update').trigger('click')

    expect(fetch).toHaveBeenCalled()
    expect(mockNotifyCb).toHaveBeenCalledWith(
      INV_UPDATE_FAIL_PREFIX + 'Error', VARIANT_DANGER)

    // Original values should be retained
    expect(ic.identifier).toBe(og.identifier)
    expect(ic.title).toBe(og.title)
    expect(appStore.sodarContext!.inv_file_name).toBe(og_file_name)
    expect(ic.description).toBe(og.description)
    expect(ic.submission_date).toBe(og.submission_date)
    expect(ic.public_release_date).toBe(og.public_release_date)
  })

  test('cancel investigation metadata update', async () => {
    const appStore = useAppStore()
    const ic = appStore.sodarContext!.investigation as SodarContextInvestigation
    const og = sodarContext.investigation as SodarContextInvestigation

    const wrapper = await showModal()
    await wrapper.find(metaIdSel).setValue(metaIdUp)
    await wrapper.find(metaTitleSel).setValue(metaTitleUp)
    await wrapper.find(metaFileSel).setValue(metaFileUp)
    await wrapper.find(metaDescSel).setValue(metaDescUp)
    await wrapper.find(metaSubDateSel).setValue(metaSubDateUp)
    await wrapper.find(metaPubDateSel).setValue(metaPubDateUp)
    await wrapper.find('#sodar-ss-inv-edit-btn-cancel').trigger('click')

    expect(fetch).not.toHaveBeenCalled()
    expect(ic.identifier).toBe(og.identifier)
    expect(ic.title).toBe(og.title)
    expect(appStore.sodarContext!.inv_file_name).toBe(
      sodarContext.inv_file_name)
    expect(ic.description).toBe(og.description)
    expect(ic.submission_date).toBe(og.submission_date)
    expect(ic.public_release_date).toBe(og.public_release_date)
  })


  test('input valid identifier', async () => {
    const wrapper = await showModal()
    const input = wrapper.find(metaIdSel)
    await input.setValue('new_identifier')
    expect(input.classes()).not.toContain(INVALID_CLASS)
    expect(wrapper.find(updateBtnSel).attributes().disabled).not.toBeDefined()
  })

  test('input empty identifier', async () => {
    const wrapper = await showModal()
    const input = wrapper.find(metaIdSel)
    await input.setValue('')
    expect(wrapper.find(updateBtnSel).attributes().disabled).toBeDefined()
  })

  test('input valid file name', async () => {
    const wrapper = await showModal()
    const input = wrapper.find(metaFileSel)
    await input.setValue('i_new_name.txt')
    expect(input.classes()).not.toContain(INVALID_CLASS)
    expect(wrapper.find(updateBtnSel).attributes().disabled).not.toBeDefined()
  })

  test('input file name with invalid prefix', async () => {
    const wrapper = await showModal()
    const input = wrapper.find(metaFileSel)
    await input.setValue('s_new_name.txt') // Not starting with "i_"
    expect(input.classes()).toContain(INVALID_CLASS)
    expect(wrapper.find(updateBtnSel).attributes().disabled).toBeDefined()
  })

  test('input file name with invalid suffix', async () => {
    const wrapper = await showModal()
    const input = wrapper.find(metaFileSel)
    await input.setValue('i_new_name.tsv') // Not ending with ".txt"
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
    await input.setValue('i_new name.txt')
    expect(input.classes()).toContain(INVALID_CLASS)
    expect(wrapper.find(updateBtnSel).attributes().disabled).toBeDefined()
  })

  test('input file name with disallowed characters', async () => {
    const wrapper = await showModal()
    const input = wrapper.find(metaFileSel)
    await input.setValue('i_(new)_name.txt')
    expect(input.classes()).toContain(INVALID_CLASS)
    expect(wrapper.find(updateBtnSel).attributes().disabled).toBeDefined()
  })

  test('input valid submission date', async () => {
    const wrapper = await showModal()
    const input = wrapper.find(metaSubDateSel)
    await input.setValue('1900-01-01')
    expect(input.classes()).not.toContain(INVALID_CLASS)
    expect(wrapper.find(updateBtnSel).attributes().disabled).not.toBeDefined()
  })

  test('input empty submission date', async () => {
    const wrapper = await showModal()
    const input = wrapper.find(metaSubDateSel)
    await input.setValue('')
    expect(input.classes()).not.toContain(INVALID_CLASS)
    expect(wrapper.find(updateBtnSel).attributes().disabled).not.toBeDefined()
  })

  test('input invalid submission date', async () => {
    const wrapper = await showModal()
    const input = wrapper.find(metaSubDateSel)
    await input.setValue('123-5-99')
    expect(input.classes()).toContain(INVALID_CLASS)
    expect(wrapper.find(updateBtnSel).attributes().disabled).toBeDefined()
  })

  test('input valid public release date', async () => {
    const wrapper = await showModal()
    const input = wrapper.find(metaPubDateSel)
    await input.setValue('1900-01-01')
    expect(input.classes()).not.toContain(INVALID_CLASS)
    expect(wrapper.find(updateBtnSel).attributes().disabled).not.toBeDefined()
  })

  test('input empty public release date', async () => {
    const wrapper = await showModal()
    const input = wrapper.find(metaPubDateSel)
    await input.setValue('')
    expect(input.classes()).not.toContain(INVALID_CLASS)
    expect(wrapper.find(updateBtnSel).attributes().disabled).not.toBeDefined()
  })

  test('input invalid public release date', async () => {
    const wrapper = await showModal()
    const input = wrapper.find(metaPubDateSel)
    await input.setValue('123-5-99')
    expect(input.classes()).toContain(INVALID_CLASS)
    expect(wrapper.find(updateBtnSel).attributes().disabled).toBeDefined()
  })
})
