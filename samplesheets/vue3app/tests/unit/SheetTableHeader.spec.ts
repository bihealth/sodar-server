import { type TemplateRef } from 'vue'
import { beforeEach, describe, expect, test, vi } from 'vitest'
import { config, mount, type VueWrapper } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { createBootstrap } from 'bootstrap-vue-next/plugins/createBootstrap'

import SheetTableHeader from '@/components/SheetTableHeader.vue'
import { useAppStore } from '@/stores/appStore.ts'
import { type SodarContext } from '@/types.ts'
import { IRODS_PATH_COPY_MSG, VARIANT_INFO } from '@/constants.ts'

import { copy } from '../testUtils.ts'
import { sodarContext } from '../data/sodarContext.ts'
import { type SheetTableHeaderProps } from '../testTypes.ts'
import {
  ASSAY_PLUGIN_NAME,
  ASSAY_PLUGIN_TITLE,
  ASSAY_UUID,
  PROJECT_UUID,
  STUDY_PATH,
  STUDY_PLUGIN_NAME,
  STUDY_PLUGIN_TITLE,
  STUDY_UUID,
} from '../testConstants.ts'

// Test Data -------------------------------------------------------------------

const studyProps: SheetTableHeaderProps = {
  assayMode: false,
  tableUuid: STUDY_UUID
}
const assayProps: SheetTableHeaderProps = {
  assayMode: true,
  tableUuid: ASSAY_UUID
}
const statsBadgeClass = 'mock-irods-stats-badge'

// Global Setup ----------------------------------------------------------------

const mockDetailModal = { template: '<div />', methods: {show: vi.fn() } }
const mockEditModal = { show: vi.fn() }
const mockNotifyCb = vi.fn()

config.global.plugins = [createBootstrap()]
config.global.stubs = {
  IrodsStatsBadge: { template: '<span class="' + statsBadgeClass + '" />'},
  TableDetailModal: mockDetailModal
}

// Mock clipboard (NOTE: has to be done in module root)
const mockCopy = vi.fn()
vi.mock('@vueuse/core', async () => {
  const actual = await vi.importActual('@vueuse/core')
  return { ...actual, useClipboard: () => ({ copy: mockCopy }) }
})


// Tests -----------------------------------------------------------------------

describe('SheetTableHeader.vue', () => {
  function mountComponent (propVals: SheetTableHeaderProps): VueWrapper {
    const props = copy(propVals) as SheetTableHeaderProps
    props.editModalRef = mockEditModal as unknown as TemplateRef
    return mount(SheetTableHeader, { props: props })
  }

  beforeEach(() => {
    vi.resetAllMocks()
    setActivePinia(createPinia())
    const appStore = useAppStore()
    appStore.currentStudyUuid = STUDY_UUID
    appStore.notifyCb = mockNotifyCb
    appStore.projectUuid = PROJECT_UUID
    appStore.sodarContext = copy(sodarContext) as SodarContext
  })

  test('render component for study', async () => {
    const appStore = useAppStore()
    const wrapper = mountComponent(studyProps)
    expect(wrapper.find('.sodar-ss-sheet-section-study').exists()).toBe(true)
    expect(wrapper.find(
      '#sodar-ss-sheet-section-study-' + STUDY_UUID).exists()).toBe(true)
    expect(wrapper.find('.sodar-ss-sheet-section-assay').exists()).toBe(false)
    expect(wrapper.find('.sodar-ss-table-title').text()).toContain(
      'Study: ' + appStore.sodarContext!.studies[STUDY_UUID]!.display_name)
    expect(wrapper.find('.sodar-ss-irods-links').exists()).toBe(true)
    expect(wrapper.find('.sodar-ss-btn-edit-study').exists()).toBe(false)
    expect(wrapper.find('.sodar-ss-btn-edit-assay').exists()).toBe(false)
  })

  test('render component for assay', async () => {
    const appStore = useAppStore()
    const wrapper = mountComponent(assayProps)
    expect(wrapper.find('.sodar-ss-sheet-section-study').exists()).toBe(false)
    expect(wrapper.find('.sodar-ss-sheet-section-assay').exists()).toBe(true)
    expect(wrapper.find(
      '#sodar-ss-sheet-section-assay-' + ASSAY_UUID).exists()).toBe(true)
    expect(wrapper.find('.sodar-ss-table-title').text()).toContain(
      'Assay: ' + appStore.sodarContext!.studies[
        STUDY_UUID]!.assays[ASSAY_UUID]!.display_name)
    expect(wrapper.find('.sodar-ss-irods-links').exists()).toBe(true)
  })

  test('hide study plugin icon with no plugin', async () => {
    const appStore = useAppStore()
    expect(appStore.sodarContext!.studies[STUDY_UUID]!.plugin_name).toEqual(null)
    const wrapper = mountComponent(studyProps)
    expect(wrapper.find('.sodar-ss-table-plugin').exists()).toBe(false)
  })

  test('display study plugin icon with plugin', async () => {
    const appStore = useAppStore()
    appStore.sodarContext!.studies[STUDY_UUID]!.plugin_name = STUDY_PLUGIN_NAME
    appStore.sodarContext!.studies[
      STUDY_UUID]!.plugin_title = STUDY_PLUGIN_TITLE
    const wrapper = mountComponent(studyProps)
    expect(wrapper.find('.sodar-ss-table-plugin').exists()).toBe(true)
    const icon = wrapper.find('.sodar-ss-table-plugin i')
    expect(icon.classes()).toContain('text-info')
    expect(icon.classes()).not.toContain('text-danger')
    expect(icon.attributes().title).toBe(STUDY_PLUGIN_TITLE)
  })

  test('hide study plugin icon with edit_sheet=false', async () => {
    const appStore = useAppStore()
    appStore.sodarContext!.studies[STUDY_UUID]!.plugin_name = STUDY_PLUGIN_NAME
    appStore.sodarContext!.studies[
      STUDY_UUID]!.plugin_title = STUDY_PLUGIN_TITLE
    appStore.sodarContext!.perms.edit_sheet = false
    const wrapper = mountComponent(studyProps)
    expect(wrapper.find('.sodar-ss-table-plugin').exists()).toBe(false)
  })

  test('hide assay plugin icon with no plugin', async () => {
    const appStore = useAppStore()
    expect(appStore.sodarContext!.studies[
      STUDY_UUID]!.assays[ASSAY_UUID]!.plugin_name).toEqual(null)
    const wrapper = mountComponent(assayProps)
    expect(wrapper.find('.sodar-ss-table-plugin-no-assay').exists()).toBe(true)
  })

  test(
      'hide assay plugin icon with no plugin and edit_sheet=false',
      async () => {
    const appStore = useAppStore()
    expect(appStore.sodarContext!.studies[
      STUDY_UUID]!.assays[ASSAY_UUID]!.plugin_name).toEqual(null)
    appStore.sodarContext!.perms.edit_sheet = false
    const wrapper = mountComponent(assayProps)
    expect(wrapper.find('.sodar-ss-table-plugin-no-assay').exists()).toBe(false)
  })

  test('display assay plugin icon with plugin', async () => {
    const appStore = useAppStore()
    appStore.sodarContext!.studies[
      STUDY_UUID]!.assays[ASSAY_UUID]!.plugin_name = ASSAY_PLUGIN_NAME
    appStore.sodarContext!.studies[
      STUDY_UUID]!.assays[ASSAY_UUID]!.plugin_title = ASSAY_PLUGIN_TITLE
    const wrapper = mountComponent(assayProps)
    expect(wrapper.find('.sodar-ss-table-plugin').exists()).toBe(true)
    expect(wrapper.find('.sodar-ss-table-plugin-no-assay').exists()).toBe(false)
    const icon = wrapper.find('.sodar-ss-table-plugin i')
    expect(icon.classes()).not.toContain('text-info')
    expect(icon.classes()).toContain('text-danger')
    expect(icon.attributes().title).toBe(ASSAY_PLUGIN_TITLE)
  })

  test('display iRODS stats badge for study', async () => {
    const appStore = useAppStore()
    expect(appStore.editMode).toBe(false)
    expect(appStore.sodarContext?.irods_status).toBe(true)
    expect(appStore.sodarContext?.perms.view_files).toBe(true)
    const wrapper = mountComponent(studyProps)
    expect(wrapper.find('.sodar-ss-study-title-badge').exists()).toBe(true)
    expect(wrapper.find('.' + statsBadgeClass).exists()).toBe(true)
    expect(wrapper.find('.sodar-ss-irods-not-created').exists()).toBe(false)
  })

  test('hide iRODS stats badge for assay', async () => {
    const wrapper = mountComponent(assayProps)
    expect(wrapper.find('.sodar-ss-study-title-badge').exists()).toBe(false)
  })

  test('hide iRODS stats badge with view_files=false', async () => {
    const appStore = useAppStore()
    appStore.sodarContext!.perms.view_files = false
    const wrapper = mountComponent(studyProps)
    expect(wrapper.find('.sodar-ss-study-title-badge').exists()).toBe(true)
    expect(wrapper.find('.' + statsBadgeClass).exists()).toBe(false)
  })

  test('display iRODS stats badge with irods_status=false', async () => {
    const appStore = useAppStore()
    appStore.sodarContext!.irods_status = false
    const wrapper = mountComponent(studyProps)
    expect(wrapper.find('.sodar-ss-study-title-badge').exists()).toBe(true)
    expect(wrapper.find('.' + statsBadgeClass).exists()).toBe(false)
    expect(wrapper.find('.sodar-ss-irods-not-created').exists()).toBe(true)
  })

  test('copy iRODS path to clipboard on button click', async () => {
    expect(mockNotifyCb).not.toHaveBeenCalled()
    const wrapper = mountComponent(studyProps)
    await wrapper.find('.sodar-ss-irods-copy-btn').trigger('click')
    expect(mockCopy).toHaveBeenCalledWith(STUDY_PATH)
    expect(mockNotifyCb).toHaveBeenCalledWith(
      IRODS_PATH_COPY_MSG, VARIANT_INFO)
  })

  test('open table detail modal on button click', async () => {
    expect(mockDetailModal.methods.show).not.toHaveBeenCalled()
    const wrapper = mountComponent(studyProps)
    await wrapper.find('.sodar-ss-btn-table-detail').trigger('click')
    expect(mockDetailModal.methods.show).toHaveBeenCalled()
  })

  test('hide iRODS stats badge with editMode=true', async () => {
    const appStore = useAppStore()
    appStore.editMode = true
    const wrapper = mountComponent(studyProps)
    // NOTE: The container should still exist
    expect(wrapper.find('.sodar-ss-study-title-badge').exists()).toBe(true)
    expect(wrapper.find('.' + statsBadgeClass).exists()).toBe(false)
  })

  test('hide iRODS links with editMode=true', async () => {
    const appStore = useAppStore()
    appStore.editMode = true
    const wrapper = mountComponent(studyProps)
    expect(wrapper.find('.sodar-ss-irods-links').exists()).toBe(false)
  })

  test('display study edit button with editMode=true', async () => {
    const appStore = useAppStore()
    appStore.editMode = true
    const wrapper = mountComponent(studyProps)
    expect(wrapper.find('.sodar-ss-btn-edit-study').exists()).toBe(true)
    expect(wrapper.find('.sodar-ss-btn-edit-assay').exists()).toBe(false)
  })

  test('open study edit modal with button click', async () => {
    const appStore = useAppStore()
    appStore.editMode = true
    expect(mockEditModal.show).not.toHaveBeenCalled()
    const wrapper = mountComponent(studyProps)
    await wrapper.find('.sodar-ss-btn-edit-study').trigger('click')
    expect(mockEditModal.show).toHaveBeenCalledWith(
      STUDY_UUID, appStore.sodarContext!.studies[STUDY_UUID])
  })

  test('display assay edit button with editMode=true', async () => {
    const appStore = useAppStore()
    appStore.editMode = true
    const wrapper = mountComponent(assayProps)
    expect(wrapper.find('.sodar-ss-btn-edit-study').exists()).toBe(false)
    expect(wrapper.find('.sodar-ss-btn-edit-assay').exists()).toBe(true)
  })

  test('open assay edit modal with button click', async () => {
    const appStore = useAppStore()
    appStore.editMode = true
    expect(mockEditModal.show).not.toHaveBeenCalled()
    const wrapper = mountComponent(assayProps)
    await wrapper.find('.sodar-ss-btn-edit-assay').trigger('click')
    expect(mockEditModal.show).toHaveBeenCalledWith(
      ASSAY_UUID, appStore.sodarContext!.studies[
        STUDY_UUID]!.assays[ASSAY_UUID])
  })
})
