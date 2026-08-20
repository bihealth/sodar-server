import { nextTick } from 'vue'
import { beforeEach, describe, expect, test, vi } from 'vitest'
import { config, mount, type VueWrapper } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { createBootstrap } from 'bootstrap-vue-next/plugins/createBootstrap'

import StudyShortcutModal from '@/components/modals/StudyShortcutModal.vue'
import { useAppStore } from '@/stores/appStore.ts'
import {
  type StudyShortcutCell,
  type StudyShortcutResponseBody,
  type StudyShortcutResponseCategory,
  type StudyShortcutResponseFile
} from '@/types.ts'

import { studyShortcutResponse } from '../data/studyShortcutResponse.ts'
import { copy, waitSelector } from '../testUtils.ts'
import { STUDY_UUID } from '../testConstants.ts'

// Test Data -------------------------------------------------------------------

const urlPrefix: string = 'http://localhost:8000/samplesheets/study/germline/' +
                          'render/igv/'
const famUuid: string = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
const cellValueDefault: StudyShortcutCell = {
  igv: { url: urlPrefix + famUuid, enabled: true },
  files: { query: { key: 'source', value: '0814' }, enabled: true }
}
const errorMsg: string = 'Error'
let cellValue: StudyShortcutCell
let resBody: StudyShortcutResponseBody

// Global Setup ----------------------------------------------------------------

config.global.plugins = [createBootstrap()]

// Tests -----------------------------------------------------------------------

describe('StudyShortcutModal.vue', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    const appStore = useAppStore()
    appStore.currentStudyUuid = STUDY_UUID
    cellValue = copy(cellValueDefault) as StudyShortcutCell
    resBody = copy(studyShortcutResponse) as StudyShortcutResponseBody
  })

  async function showModal (): Promise<VueWrapper> {
    global.fetch = vi.fn(() =>
      Promise.resolve({
        json: () => Promise.resolve(resBody), status: 200
      } as Response)
    )
    const wrapper = mount(StudyShortcutModal)
    wrapper.vm.show(cellValue)
    await nextTick() // Must wait for all reactive vals to update
    return wrapper
  }

  test('render component with default data', async () => {
    const wrapper = await showModal()
    await waitSelector(wrapper, '#sodar-ss-shortcut-modal-content', 1)
    expect(wrapper.find(
      '.modal-title').text()).toBe(studyShortcutResponse.title)
    expect(wrapper.find('#sodar-ss-shortcut-modal-content').exists()).toBe(true)
    expect(wrapper.findAll('.sodar-ss-shortcut-table').length).toBe(3)
    expect(wrapper.find('#sodar-ss-shortcuts-message').exists()).toBe(false)
    expect(wrapper.find('.sodar-ss-shortcuts-no-files').exists()).toBe(false)
  })

  test('render session category', async () => {
    const cat = studyShortcutResponse?.data?.session as
      StudyShortcutResponseCategory
    const wrapper = await showModal()
    await waitSelector(wrapper, '#sodar-ss-shortcut-modal-content', 1)
    const table = wrapper.findAll('.sodar-ss-shortcut-table')[0]

    expect(table?.find('th').text()).toBe(cat.title)
    expect(table?.find('.sodar-ss-shortcut-info').exists()).toBe(false)

    expect(table?.findAll('.sodar-ss-shortcut-item').length).toBe(1)
    const file = cat.files[0] as StudyShortcutResponseFile
    const cols = table?.findAll('td')
    expect(cols![0]?.find('a').text()).toBe(file.label)
    expect(cols![0]?.find('a').attributes().title).toBe('')

    expect(cols![1]?.findAll('.sodar-ss-irods-btn').length).toBe(2)
    for (let i = 0; i < 2; i++) {
      const btn = cols![1]?.findAll('.sodar-ss-irods-btn')[i]
      expect(btn?.attributes().href).toBe(file?.extra_links[i]?.url)
      expect(btn?.attributes().title).toBe(file?.extra_links[i]?.label)
      expect(btn?.find('i').attributes()['data-icon']).toBe(
        file?.extra_links[i]?.icon)
    }
  })

  test('render bam category', async () => {
    const cat = studyShortcutResponse?.data?.bam as
      StudyShortcutResponseCategory
    const wrapper = await showModal()
    await waitSelector(wrapper, '#sodar-ss-shortcut-modal-content', 1)
    const table = wrapper.findAll('.sodar-ss-shortcut-table')[1]

    expect(table?.find('th').text()).toBe(cat.title)
    expect(table?.find('.sodar-ss-shortcut-info').exists()).toBe(true)
    expect(table?.find('.sodar-ss-shortcut-info').attributes().title).toBe(
      'Omitted from IGV: ' + cat.omit_info
    )

    expect(table?.findAll('.sodar-ss-shortcut-item').length).toBe(1)
    const file = cat.files[0] as StudyShortcutResponseFile
    const cols = table?.findAll('td')
    expect(cols![0]?.find('a').attributes().title).toBe(file.title)
  })

  test('render category with no files', async () => {
    resBody!.data!.session!.files = []
    const wrapper = await showModal()
    await waitSelector(wrapper, '#sodar-ss-shortcut-modal-content', 1)
    const table = wrapper.findAll('.sodar-ss-shortcut-table')[0]
    expect(table?.findAll('.sodar-ss-shortcut-item').length).toBe(0)
    expect(table?.find('.sodar-ss-shortcuts-no-files').exists()).toBe(true)
  })

  test('render component with error message', async () => {
    resBody = { title: studyShortcutResponse.title, error: errorMsg }
    const wrapper = await showModal()
    await waitSelector(wrapper, '#sodar-ss-shortcuts-message', 1)
    expect(wrapper.find(
      '#sodar-ss-shortcut-modal-content').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-shortcuts-message').text()).toBe(errorMsg)
  })
})
