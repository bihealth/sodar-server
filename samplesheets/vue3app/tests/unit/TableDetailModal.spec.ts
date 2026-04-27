import { nextTick } from 'vue'
import { beforeEach, describe, expect, test } from 'vitest'
import { config, mount, type VueWrapper } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { createBootstrap } from 'bootstrap-vue-next/plugins/createBootstrap'

import TableDetailModal from '@/components/modals/TableDetailModal.vue'
import { useAppStore } from '@/stores/appStore.ts'
import { type SodarContextAssay, type SodarContextStudy } from '@/types.ts'
import {
  STUDY_META_FIELDS,
  STUDY_SODAR_FIELDS,
  ASSAY_META_FIELDS,
  ASSAY_SODAR_FIELDS
} from '@/constants.ts'

import { sodarContextAssay, sodarContextStudy } from '../data/sodarContext.ts'
import { ASSAY_UUID, STUDY_UUID } from '../testConstants.ts'

config.global.plugins = [createBootstrap()]

describe('TableDetailModal.vue', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    const appStore = useAppStore()
    appStore.currentStudyUuid = STUDY_UUID
  })

  async function showModal (
      tableUuid: string,
      context: SodarContextAssay | SodarContextStudy
  ): Promise<VueWrapper> {
    const wrapper = mount(TableDetailModal)
    wrapper.vm.show(tableUuid, context)
    await nextTick() // Must wait for all reactive vals to update
    return wrapper
  }

  test('render component with study', async () => {
    const wrapper = await showModal(STUDY_UUID, sodarContextStudy)
    expect(wrapper.find('#sodar-ss-table-detail-modal').exists()).toBe(true)
    expect(wrapper.find('.modal-title').text()).toBe('Study Details')
    expect(wrapper.find(
      '#sodar-ss-table-detail-container-' + STUDY_UUID).exists()).toBe(true)
    expect(wrapper.findAll(
      '.sodar-ss-table-detail-row-meta').length).toBe(STUDY_META_FIELDS.length)
    expect(wrapper.findAll('.sodar-ss-table-detail-row-comment').length).toBe(
      Object.entries(
        sodarContextStudy.comments as { [s: string]: string } ).length)
    expect(wrapper.findAll('.sodar-ss-table-detail-row-sodar').length).toBe(
      STUDY_SODAR_FIELDS.length + 1) // +1 for SODAR UUID
    expect(wrapper.find(
      '.sodar-ss-table-detail-uuid dd').text()).toBe(STUDY_UUID)
  })

  test('render component with assay', async () => {
    const wrapper = await showModal(ASSAY_UUID, sodarContextAssay)
    expect(wrapper.find('#sodar-ss-table-detail-modal').exists()).toBe(true)
    expect(wrapper.find('.modal-title').text()).toBe('Assay Details')
    expect(wrapper.find(
      '#sodar-ss-table-detail-container-' + ASSAY_UUID).exists()).toBe(true)
    expect(wrapper.findAll(
      '.sodar-ss-table-detail-row-meta').length).toBe(ASSAY_META_FIELDS.length)
    expect(sodarContextAssay.comments).toBe(null) // Assay has no comments
    expect(wrapper.find(
      '.sodar-ss-table-detail-row-comment').exists()).toBe(false)
    expect(wrapper.findAll('.sodar-ss-table-detail-row-sodar').length).toBe(
      ASSAY_SODAR_FIELDS.length + 1)
    expect(wrapper.find(
      '.sodar-ss-table-detail-uuid dd').text()).toBe(ASSAY_UUID)
  })
})
