import { beforeEach, describe, expect, test, vi } from 'vitest'
import { config, mount, type VueWrapper } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { createBootstrap } from 'bootstrap-vue-next/plugins/createBootstrap'

import AssayShortcutCard from '@/components/AssayShortcutCard.vue'
import { useAppStore } from '@/stores/appStore.ts'
import { useTableStore } from '@/stores/tableStore.ts'
import { type SheetAssayShortcuts, type SodarContext } from '@/types.ts'
import { IRODS_PATH_COPY_MSG, VARIANT_INFO } from '@/constants.ts'

import { copy } from '../testUtils.ts'
import { sodarContext } from '../data/sodarContext.ts'
import { assayShortcuts } from '../data/assayShortcuts.ts'
import {
  ASSAY_PATH,
  ASSAY_UUID,
  RESULTS_REPORTS_DIR
} from '../testConstants.ts'

// Global Setup ----------------------------------------------------------------

// Set up bootstrap-vue-next plugin to enable composable use
config.global.plugins = [createBootstrap()]
// Mock clipboard (NOTE: has to be done in module root)
const mockCopy = vi.fn()
vi.mock('@vueuse/core', async () => {
  const actual = await vi.importActual('@vueuse/core')
  return { ...actual, useClipboard: () => ({ copy: mockCopy }) }
})
const mockNotifyCb = vi.fn()

// Tests -----------------------------------------------------------------------

describe('AssayShortcutCard.vue', () => {
  function mountComponent (): VueWrapper {
    const props = { assayUuid: ASSAY_UUID, modalRef: null }
    return mount(AssayShortcutCard, { props: props })
  }

  beforeEach(() => {
    vi.resetAllMocks()
    setActivePinia(createPinia())
    const appStore = useAppStore()
    appStore.notifyCb = mockNotifyCb
    appStore.sodarContext = copy(sodarContext) as SodarContext
    const tableStore = useTableStore()
    tableStore.assayShortcuts = {
      [ASSAY_UUID]: copy(assayShortcuts)
    } as SheetAssayShortcuts
  })

  test('render component', async () => {
    const appStore = useAppStore()
    expect(appStore.sodarContext?.perms.view_files).toBe(true)
    const wrapper = mountComponent()
    expect(wrapper.find('.sodar-ss-assay-shortcut-card').exists()).toBe(true)
    expect(wrapper.findAll('.sodar-ss-assay-shortcut').length).toBe(4)
  })

  test('render component without view_files perm', async () => {
    const appStore = useAppStore()
    appStore.sodarContext!.perms.view_files = false
    const wrapper = mountComponent()
    expect(wrapper.find('.sodar-ss-assay-shortcut-card').exists()).toBe(false)
  })

  test('render icons for regular user', async () => {
    const appStore = useAppStore()
    expect(appStore.sodarContext?.perms.is_superuser).toBe(false)
    const wrapper = mountComponent()
    expect(wrapper.findAll('.sodar-ss-assay-shortcut-icon').length).toBe(1)
    expect(wrapper.findAll('.sodar-ss-assay-shortcut-icon-hub').length).toBe(1)
    expect(wrapper.findAll(
      '.sodar-ss-assay-shortcut-icon-plugin').length).toBe(0)
  })

  test('render icons for superuser', async () => {
    const appStore = useAppStore()
    appStore.sodarContext!.perms.is_superuser = true
    const wrapper = mountComponent()
    expect(wrapper.findAll('.sodar-ss-assay-shortcut-icon').length).toBe(2)
    expect(wrapper.findAll('.sodar-ss-assay-shortcut-icon-hub').length).toBe(1)
    expect(wrapper.findAll(
      '.sodar-ss-assay-shortcut-icon-plugin').length).toBe(1)
  })

  test('render iRODS button enabled and disabled states', async () => {
    const tableStore = useTableStore()
    const wrapper = mountComponent()
    const shortcuts = wrapper.findAll('.sodar-ss-assay-shortcut')
    const buttons = wrapper.findAll('.sodar-ss-irods-list-btn')
    // Assert order of shortcuts, misc files should be disabled
    expect(buttons[0]?.attributes().disabled).not.toBeDefined()
    expect(shortcuts[1]?.text()).toContain('Misc Files')
    expect(tableStore.assayShortcuts[
      ASSAY_UUID]!['misc_files']!.enabled).toBe(false)
    expect(buttons[1]?.attributes().disabled).toBeDefined()
    expect(buttons[2]?.attributes().disabled).not.toBeDefined()
    expect(buttons[3]?.attributes().disabled).not.toBeDefined()
  })

  test('render extra link in iRODS buttons', async () => {
    const wrapper = mountComponent()
    const shortcuts = wrapper.findAll('.sodar-ss-assay-shortcut')
    expect(shortcuts[2]?.text()).toContain('TrackHubX')
    const buttons = shortcuts[2]?.findAll('.sodar-list-btn')
    expect(buttons?.length).toBe(5)
    const extraBtn = shortcuts[2]?.find('.sodar-irods-ticket-access-1-btn')
    expect(extraBtn?.exists()).toBe(true)
    // Extra link rendering details testsd in IrodsButtons tests
  })

  test('copy iRODS path to clipboard on button click', async () => {
    expect(mockNotifyCb).not.toHaveBeenCalled()
    const wrapper = mountComponent()
    await wrapper.find('.sodar-ss-irods-copy-btn').trigger('click')
    expect(mockCopy).toHaveBeenCalledWith(
      `${ASSAY_PATH}/${RESULTS_REPORTS_DIR}`)
    expect(mockNotifyCb).toHaveBeenCalledWith(
      IRODS_PATH_COPY_MSG, VARIANT_INFO)
  })
})
