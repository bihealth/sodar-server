import { beforeEach, describe, expect, test, vi } from 'vitest'
import { mount, type VueWrapper } from '@vue/test-utils'
import { createRouter, createWebHashHistory, type Router } from 'vue-router'
import { setActivePinia, createPinia } from 'pinia'
import { createBootstrap } from 'bootstrap-vue-next/plugins/createBootstrap'

import OverviewView from '@/views/OverviewView.vue'
import { useAppStore } from '@/stores/appStore.ts'
import { routes } from '@/router/index.ts'
import {
  ASSAY_META_FIELDS,
  ASSAY_SODAR_FIELDS,
  INV_META_FIELDS,
  STUDY_META_FIELDS,
  STUDY_SODAR_FIELDS,
  SHEET_STATS
} from '@/constants.ts'
import {
  type SodarContext,
  type SodarContextAssay,
  type SodarContextInvestigation,
  type SodarContextStudy
} from '@/types.ts'

import { copy, waitSelector } from '../testUtils.ts'
import { sodarContext } from '../data/sodarContext.ts'
import { ASSAY_UUID, PROJECT_UUID, STUDY_UUID } from '../testConstants.ts'

let router: Router

describe('OverviewView.vue', () => {
  function mountComponent (): VueWrapper {
    return mount(OverviewView, {
      global: {plugins: [router, createBootstrap()]} })
  }

  beforeEach(async () => {
    // Setup router
    // NOTE: Router must be initialized before setting up stores
    router = createRouter({history: createWebHashHistory(), routes: routes})
    await router.push('/')
    await router.isReady()

    // Setup stores
    setActivePinia(createPinia())
    const appStore = useAppStore()
    appStore.currentStudyUuid = STUDY_UUID
    appStore.projectUuid = PROJECT_UUID
    appStore.sodarContext = copy(sodarContext) as SodarContext

    // Mock fetch for irodsStatsBadge
    global.fetch = vi.fn(() =>
      Promise.resolve({
        json: () => Promise.resolve({ file_count: 170, total_size: 170000000 }),
        status: 200,
        statusText: 'ok'
      } as Response))
  })

  test('render investigation card', async () => {
    const contextInv = sodarContext.investigation as SodarContextInvestigation
    const wrapper = mountComponent()

    const card = wrapper.find('#sodar-ss-overview-investigation')
    expect(card.exists()).toBe(true)
    expect(card.find('h4').text()).toBe('Investigation: ' + contextInv.title)
    // Meta field for "inv_file_name" is set manually
    expect(card.findAll('.sodar-ss-table-detail-row-meta').length).toBe(
      INV_META_FIELDS.length + 1)
    expect(card.findAll('.sodar-ss-table-detail-row-comment').length).toBe(0)
    expect(card.findAll('.sodar-ss-table-detail-row-sodar').length).toBe(2)

    await waitSelector(wrapper, '.sodar-ss-irods-stats-loading', 0)
    const badge = wrapper.find('.sodar-ss-irods-stats')
    expect(badge.classes()).toContain('badge-info')
    expect(badge.classes()).not.toContain('badge-danger')
    expect(badge.text()).toBe('170 files (170 MB)')
  })

  test('render study card', async () => {
    const contextStudy = sodarContext.studies[STUDY_UUID] as SodarContextStudy
    const wrapper = mountComponent()

    const card = wrapper.find('#sodar-ss-overview-study-' + STUDY_UUID)
    expect(card.find('h4').text()).toBe('Study: ' + contextStudy.display_name)
    expect(card.find('h4').find('a').exists()).toBe(true)

    const detailList = card.find(
      '#sodar-ss-table-detail-container-' + STUDY_UUID)
    expect(detailList.findAll('.sodar-ss-table-detail-row-meta').length).toBe(
      STUDY_META_FIELDS.length)
    expect(detailList.findAll('.sodar-ss-table-detail-row-sodar').length).toBe(
      STUDY_SODAR_FIELDS.length + 1) // The last 1 is for SODAR UUID
  })

  test('render assay card', async () => {
    const contextAssay = sodarContext.studies[
      STUDY_UUID]?.assays[ASSAY_UUID] as SodarContextAssay
    const wrapper = mountComponent()

    const card = wrapper.find('#sodar-ss-overview-assay-' + ASSAY_UUID)
    expect(card.find('h4').text()).toBe('Assay: ' + contextAssay.display_name)
    expect(card.find('h4').find('a').exists()).toBe(true)

    const detailList = card.find(
      '#sodar-ss-table-detail-container-' + ASSAY_UUID)
    expect(detailList.findAll('.sodar-ss-table-detail-row-meta').length).toBe(
      ASSAY_META_FIELDS.length)
    expect(detailList.findAll('.sodar-ss-table-detail-row-sodar').length).toBe(
      ASSAY_SODAR_FIELDS.length + 1) // The last 1 is for SODAR UUID
  })

  test('render statistics card', async () => {
    const appStore = useAppStore()
    const wrapper = mountComponent()
    const table = wrapper.find('#sodar-ss-overview-stats').find('table')
    const headers = table.findAll('th')
    const cells = table.findAll('td')
    expect(headers.length).toBe(SHEET_STATS.length)
    for (let i = 0; i < headers.length; i++) {
      expect(headers[i]?.text()).toBe(SHEET_STATS[i]![0])
      expect(cells[i]?.text()).toBe(
        (appStore.getStat(SHEET_STATS[i]![1] as string) as number).toString()
      )
    }
  })

  test('navigate to study from study card title link', async () => {
    const appStore = useAppStore()
    const wrapper = mountComponent()
    expect(appStore.overviewActive).toBe(true)
    const card = wrapper.find('#sodar-ss-overview-study-' + STUDY_UUID)
    const link = card.find('h4').find('a')
    await link.trigger('click')
    expect(appStore.overviewActive).toBe(false)
  })

  test('navigate to assay from assay card title link', async () => {
    const appStore = useAppStore()
    const wrapper = mountComponent()
    expect(appStore.overviewActive).toBe(true)
    const card = wrapper.find('#sodar-ss-overview-assay-' + ASSAY_UUID)
    const link = card.find('h4').find('a')
    await link.trigger('click')
    expect(appStore.overviewActive).toBe(false)
  })
})
