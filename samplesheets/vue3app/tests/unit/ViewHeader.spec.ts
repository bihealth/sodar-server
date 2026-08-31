import { beforeEach, describe, expect, test, vi } from 'vitest'
import { config, flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { createRouter, createWebHashHistory, type Router } from 'vue-router'
import { createBootstrap } from 'bootstrap-vue-next/plugins/createBootstrap'

import ViewHeader from '@/components/ViewHeader.vue'
import { useAppStore } from '@/stores/appStore.ts'
import { useEditStore } from '@/stores/editStore.ts'
import { useTableStore } from '@/stores/tableStore.ts'
import { routes } from '@/router/index.ts'
import { type SodarContext, type SodarContextStudy } from '@/types.ts'
import {
  EDIT_BADGE_DEFAULT_LABEL,
  EDIT_BADGE_SAVED_LABEL,
  EDIT_BADGE_UNSAVED_LABEL,
  EDIT_MODE_EXIT_MSG,
  EDIT_MODE_SAVE_MSG,
  EDIT_MODE_UNSAVED_MSG,
  EDIT_MSG_FINISH,
  EDIT_MSG_SAVE_FAIL_PREFIX,
  STUDY_NAV_DROPDOWN_LEN,
  STUDY_NAV_TAB_LEN,
  URL_EDIT_FINISH_PREFIX,
  VIEW_PARSER_WARNING,
  VIEW_OVERVIEW,
  VIEW_STUDY
} from '@/constants.ts'

import { copy } from '../testUtils.ts'
import { sodarContext } from '../data/sodarContext.ts'
import {
  ASSAY_UUID,
  PROJECT_UUID,
  STUDY_UUID,
  TMP_UUID
} from '../testConstants.ts'

// Test Data -------------------------------------------------------------------

const finishUrl = URL_EDIT_FINISH_PREFIX + PROJECT_UUID
let router: Router

// Global Setup ----------------------------------------------------------------

// Mock modals
const mockVersionSaveModal = { template: '<div />', methods: {show: vi.fn() } }
const mockWinExportModal = { template: '<div />', methods: {show: vi.fn() } }

config.global.stubs = {
  VersionSaveModal: mockVersionSaveModal,
  WinExportModal: mockWinExportModal
}

// Replace useToast with mock
const mockCreate = vi.fn()
vi.mock('bootstrap-vue-next', async () => {
  const actual = await vi.importActual('bootstrap-vue-next')
  return { ...actual, useToast: () => ({ create: mockCreate, show: vi.fn() }) }
})

// Tests -----------------------------------------------------------------------

describe('ViewHeader.vue', () => {
  function expectDropdownItems (
      wrapper: VueWrapper,
      items: { [key: string]: boolean }
  ) {
    for (const [k, v] of Object.entries(items)) {
      expect(
        wrapper.find('#sodar-ss-op-item-' + k).exists(), 'Key = ' + k).toBe(v)
    }
  }

  function mockFetch (detail?: string, status?: number) {
    if (!detail) detail = 'ok'
    if (!status) status = 200
    global.fetch = vi.fn(() => Promise.resolve({
      json: () => Promise.resolve(
        { detail: detail }), status: status} as Response)
    )
  }

  function mountComponent (): VueWrapper {
    return mount(ViewHeader, {
      global: { plugins: [router, createBootstrap()] } })
  }

  beforeEach(async () => {
    vi.resetAllMocks()
    // Setup router
    // NOTE: Router must be initialized before setting up stores
    router = createRouter({history: createWebHashHistory(), routes: routes})
    await router.push('/')
    await router.isReady()
    // Setup stores
    setActivePinia(createPinia())
    const appStore = useAppStore()
    appStore.currentStudyUuid = STUDY_UUID
    appStore.editMode = false
    appStore.gridsBusy = false
    appStore.gridsLoaded = true
    appStore.viewActive = VIEW_STUDY
    appStore.projectUuid = PROJECT_UUID
    appStore.sodarContext = copy(sodarContext) as SodarContext
    appStore.windowsOs = false
    const tableStore = useTableStore()
    tableStore.renderError = null
  })

  test('render study nav tabs with default settings', async () => {
    const wrapper = mountComponent()
    expect(wrapper.find('#sodar-ss-nav-tabs').exists()).toBe(true)
    expect(wrapper.findAll('.sodar-ss-nav-tab-study').length).toBe(1)
    const studyBtn = wrapper.find('.sodar-ss-nav-tab-study')
    expect(studyBtn.attributes().id).toBe(
      'sodar-ss-nav-tab-study-' + STUDY_UUID)
    expect(studyBtn.text()).toBe(
      sodarContext?.studies[STUDY_UUID]?.display_name)
    expect(studyBtn.classes()).toContain('active')
    expect(studyBtn.attributes().disabled).not.toBeDefined()
    const overBtn = wrapper.find('#sodar-ss-nav-tab-overview')
    expect(overBtn.classes()).not.toContain('active')
    expect(overBtn.attributes().disabled).not.toBeDefined()
  })

  test('hide nav tabs with no sheets available', async () => {
    const appStore = useAppStore()
    appStore.currentStudyUuid = ''
    const wrapper = mountComponent()
    expect(wrapper.find('#sodar-ss-nav-tabs').exists()).toBe(false)
  })

  test('truncate long study display name in nav tabs', async () => {
    const appStore = useAppStore()
    appStore.sodarContext!.studies[STUDY_UUID]!.display_name = 'x'.repeat(
      STUDY_NAV_TAB_LEN + 16)
    const wrapper = mountComponent()
    const studyBtn = wrapper.find('.sodar-ss-nav-tab-study')
    expect(studyBtn.text()).toBe('x'.repeat(STUDY_NAV_TAB_LEN) + '...')
  })

  test('render nav tabs with gridsBusy=true', async () => {
    const appStore = useAppStore()
    appStore.gridsBusy = true
    const wrapper = mountComponent()
    expect(wrapper.find(
      '.sodar-ss-nav-tab-study').attributes().disabled).toBeDefined()
    expect(wrapper.find(
      '#sodar-ss-nav-tab-overview').attributes().disabled).toBeDefined()
  })

  test('render nav tabs with editMode=true and multiple studies', async () => {
    const appStore = useAppStore()
    appStore.editMode = true
    // Fake extra study
    appStore.sodarContext!.studies[TMP_UUID] = {
      assays: {},
      display_name: 'Fake Study'
    } as SodarContextStudy

    const wrapper = mountComponent()
    const studyNavs = wrapper.findAll('.sodar-ss-nav-tab-study')
    expect(studyNavs.length).toBe(2)
    for (const s of studyNavs) {
      expect(s.attributes().disabled).toBeDefined()
    }
    expect(wrapper.find(
      '#sodar-ss-nav-tab-overview').attributes().disabled).toBeDefined()
  })

  test('render nav tabs with viewActive=VIEW_OVERVIEW', async () => {
    const appStore = useAppStore()
    appStore.viewActive = VIEW_OVERVIEW
    const wrapper = mountComponent()
    const studyBtn = wrapper.find('.sodar-ss-nav-tab-study')
    expect(studyBtn.classes()).not.toContain('active')
    expect(studyBtn.attributes().disabled).not.toBeDefined()
    const overBtn = wrapper.find('#sodar-ss-nav-tab-overview')
    expect(overBtn.classes()).toContain('active')
    expect(overBtn.attributes().disabled).not.toBeDefined()
  })

  test('render nav tabs with viewActive=VIEW_PARSER_WARNING', async () => {
    const appStore = useAppStore()
    appStore.viewActive = VIEW_PARSER_WARNING
    const wrapper = mountComponent()
    // Neither tab should be active
    const studyBtn = wrapper.find('.sodar-ss-nav-tab-study')
    expect(studyBtn.classes()).not.toContain('active')
    expect(studyBtn.attributes().disabled).not.toBeDefined()
    const overBtn = wrapper.find('#sodar-ss-nav-tab-overview')
    expect(overBtn.classes()).not.toContain('active')
    expect(overBtn.attributes().disabled).not.toBeDefined()
  })

  test('navigate to overview with nav tabs', async () => {
    const appStore = useAppStore()
    expect(appStore.viewActive).toBe(VIEW_STUDY)

    const wrapper = mountComponent()
    const studyBtn = wrapper.find('.sodar-ss-nav-tab-study')
    const overBtn = wrapper.find('#sodar-ss-nav-tab-overview')

    await overBtn.trigger('click')
    expect(appStore.viewActive).toBe(VIEW_OVERVIEW)
    await flushPromises() // Need to wait before checking router update
    await router.isReady()
    expect(router.currentRoute.value.name).toBe('overview')
    expect(studyBtn.classes()).not.toContain('active')
    expect(overBtn.classes()).toContain('active')
  })

  test('navigate to study view with nav tabs', async () => {
    const appStore = useAppStore()
    appStore.viewActive = VIEW_OVERVIEW
    const wrapper = mountComponent()
    const studyBtn = wrapper.find('.sodar-ss-nav-tab-study')
    const overBtn = wrapper.find('#sodar-ss-nav-tab-overview')
    await studyBtn.trigger('click')
    expect(appStore.viewActive).toBe(VIEW_STUDY)
    expect(studyBtn.classes()).toContain('active')
    expect(overBtn.classes()).not.toContain('active')
  })

  test('hide badge container with default settings', async() => {
    const appStore = useAppStore()
    expect(appStore.editMode).toBe(false)
    const editStore = useEditStore()
    expect(editStore.editDataUpdated).toBe(false)
    expect(editStore.unsavedData).toBe(false)
    expect(editStore.unsavedRow).toBe(null)
    const wrapper = mountComponent()
    expect(wrapper.find(
      '#sodar-ss-subtitle-badge-container').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-badge-edit').exists()).toBe(false)
  })

  test('show badge container with editMode=true', async() => {
    const appStore = useAppStore()
    appStore.editMode = true
    const wrapper = mountComponent()
    const badge = wrapper.find('#sodar-ss-badge-edit')
    expect(badge.exists()).toBe(true)
    expect(badge.text()).toBe(EDIT_BADGE_DEFAULT_LABEL)
  })

  test('show badge container with editMode and unsavedData', async() => {
    const appStore = useAppStore()
    appStore.editMode = true
    const editStore = useEditStore()
    editStore.unsavedData = true
    const wrapper = mountComponent()
    const badge = wrapper.find('#sodar-ss-badge-edit')
    expect(badge.exists()).toBe(true)
    expect(badge.text()).toBe(EDIT_BADGE_UNSAVED_LABEL)
  })

  test('show badge container with editMode and unsavedRow', async() => {
    const appStore = useAppStore()
    appStore.editMode = true
    const editStore = useEditStore()
    editStore.unsavedRow = { id: 'row0', tableUuid: STUDY_UUID }
    const wrapper = mountComponent()
    const badge = wrapper.find('#sodar-ss-badge-edit')
    expect(badge.exists()).toBe(true)
    expect(badge.text()).toBe(EDIT_BADGE_UNSAVED_LABEL)
  })

    test('show badge container with editMode and editDataUpdated', async() => {
    const appStore = useAppStore()
    appStore.editMode = true
    const editStore = useEditStore()
    editStore.editDataUpdated = true
    const wrapper = mountComponent()
    const badge = wrapper.find('#sodar-ss-badge-edit')
    expect(badge.exists()).toBe(true)
    expect(badge.text()).toBe(EDIT_BADGE_SAVED_LABEL)
  })

  test('render nav dropdown with default settings', async () => {
    const wrapper = mountComponent()
    expect(wrapper.find('#sodar-ss-nav-dropdown').exists()).toBe(true)
    // We should have nav items for study, assay and overview
    expect(wrapper.findAll('.sodar-ss-nav-item').length).toBe(3)
    expect(wrapper.find(
      '#sodar-ss-nav-study-' + STUDY_UUID).exists()).toBe(true)
    expect(wrapper.find(
      '#sodar-ss-nav-assay-' + ASSAY_UUID).exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-nav-overview').exists()).toBe(true)
    expect(wrapper.find(
      '#sodar-ss-nav-overview').attributes().disabled).not.toBeDefined()
  })

  test('render nav dropdown with editMode=true', async () => {
    const appStore = useAppStore()
    appStore.editMode = true
    const wrapper = mountComponent()
    expect(wrapper.find('#sodar-ss-nav-dropdown').exists()).toBe(true)
    // The entire dropdown should be disabled
    expect(wrapper.find(
      '#sodar-ss-nav-dropdown').attributes().disabled).toBeDefined()
  })

  test('hide nav dropdown with no sheets available', async () => {
    const appStore = useAppStore()
    appStore.currentStudyUuid = ''
    const wrapper = mountComponent()
    expect(wrapper.find('#sodar-ss-nav-dropdown').exists()).toBe(false)
  })

  test('render study and assay links', async () => {
    const wrapper = mountComponent()
    const studyLink = wrapper.find('#sodar-ss-nav-study-' + STUDY_UUID)
    expect(studyLink.text()).toBe(
      sodarContext?.studies[STUDY_UUID]?.display_name)
    expect(studyLink.find('i').attributes()['data-icon']).toBe(
      'mdi:folder-table')
    const assayLink = wrapper.find('#sodar-ss-nav-assay-' + ASSAY_UUID)
    expect(assayLink.text()).toBe(
      sodarContext?.studies[STUDY_UUID]?.assays[ASSAY_UUID]?.display_name)
    expect(assayLink.find('i').attributes()['data-icon']).toBe(
      'mdi:table-large')
  })

  test('truncate long study display name in nav dropdown', async () => {
    const appStore = useAppStore()
    appStore.sodarContext!.studies[STUDY_UUID]!.display_name = 'x'.repeat(
      STUDY_NAV_DROPDOWN_LEN + 16)
    const wrapper = mountComponent()
    const studyLink = wrapper.find('#sodar-ss-nav-study-' + STUDY_UUID)
    expect(studyLink.text()).toBe('x'.repeat(STUDY_NAV_DROPDOWN_LEN) + '...')
  })

  test('navigate to overview with nav dropdown', async () => {
    const appStore = useAppStore()
    expect(appStore.viewActive).toBe(VIEW_STUDY)
    const wrapper = mountComponent()
    const overLink = wrapper.find('#sodar-ss-nav-overview')
    await overLink.trigger('click')
    expect(appStore.viewActive).toBe(VIEW_OVERVIEW)
  })

  test('navigate to study view with nav dropdown', async () => {
    const appStore = useAppStore()
    appStore.viewActive = VIEW_OVERVIEW
    const wrapper = mountComponent()
    const studyLink = wrapper.find('#sodar-ss-nav-study-' + STUDY_UUID)
    await studyLink.trigger('click')
    expect(appStore.viewActive).toBe(VIEW_STUDY)
  })

  test('hide save version button in edit mode', async () => {
    const appStore = useAppStore()
    expect(appStore.editMode).toBe(false)
    const wrapper = mountComponent()
    expect(wrapper.find('#sodar-ss-btn-version-save').exists()).toBe(false)
  })

  test('display save version button in edit mode', async () => {
    const appStore = useAppStore()
    appStore.editMode = true
    const editStore = useEditStore()
    expect(editStore.versionSaved).toBe(true)
    const wrapper = mountComponent()
    // Button should be disabled
    expect(wrapper.find(
      '#sodar-ss-btn-version-save').attributes().disabled).toBeDefined()
  })

  test('display save version button with versionSaved=false', async () => {
    const appStore = useAppStore()
    appStore.editMode = true
    const editStore = useEditStore()
    editStore.versionSaved = false
    const wrapper = mountComponent()
    // Button should be enabled
    expect(wrapper.find(
      '#sodar-ss-btn-version-save').attributes().disabled).not.toBeDefined()
  })

  test('open version save modal on button click', async () => {
    const appStore = useAppStore()
    const editStore = useEditStore()
    appStore.editMode = true
    editStore.versionSaved = false
    expect(mockVersionSaveModal.methods.show).not.toHaveBeenCalled()

    const wrapper = mountComponent()
    await wrapper.find('#sodar-ss-btn-version-save').trigger('click')
    expect(mockVersionSaveModal.methods.show).toHaveBeenCalled()
  })

  test('render ops dropdown with default settings', async () => {
    const wrapper = mountComponent()
    const dropdown = wrapper.find('#sodar-ss-op-dropdown')
    expect(dropdown.exists()).toBe(true)
    expect(dropdown.attributes().disabled).not.toBeDefined()
    expect(wrapper.findAll('.sodar-ss-op-item').length).toBe(10)
    const expected = {
      'sync':       false,
      'import':     false,
      'create':     false,
      'edit':       true,
      'warnings':   true,
      'cache':      true,
      'replace':    true,
      'export':     true,
      'export-win': false,
      'irods':      true,
      'versions':   true,
      'tickets':    true,
      'requests':   true,
      'delete':     true,
    }
    expectDropdownItems(wrapper, expected)
    // Disabled for now
    expect(wrapper.find(
      '#sodar-ss-op-item-edit').attributes().disabled).not.toBeDefined()
    expect(wrapper.find(
      '#sodar-ss-op-item-irods').text()).toBe('Update iRODS Collections')
    expect(wrapper.find(
      '#sodar-ss-op-item-delete').text()).toBe('Delete Sheets and Data')
    // Finish editing button should not be displayed
    expect(wrapper.find('#sodar-ss-btn-edit-finish').exists()).toBe(false)
  })

  test('render ops dropdown with gridsBusy=true', async () => {
    const appStore = useAppStore()
    appStore.gridsBusy = true
    const wrapper = mountComponent()
    expect(wrapper.find(
      '#sodar-ss-op-dropdown').attributes().disabled).toBeDefined()
  })

  test('render ops dropdown with irods_status=false', async () => {
    const appStore = useAppStore()
    appStore.sodarContext!.irods_status = false
    const wrapper = mountComponent()
    const expected = {
      'sync':       false,
      'import':     false,
      'create':     false,
      'edit':       true,
      'warnings':   true,
      'cache':      false, // Changed
      'replace':    true,
      'export':     true,
      'export-win': false,
      'irods':      true,
      'versions':   true,
      'tickets':    false, // Changed
      'requests':   false, // Changed
      'delete':     true,
    }
    expectDropdownItems(wrapper, expected)
    expect(wrapper.find(
      '#sodar-ss-op-item-irods').text()).toBe('Create iRODS Collections')
    expect(wrapper.find(
      '#sodar-ss-op-item-delete').text()).toBe('Delete Sheets')
  })

  test('render ops dropdown with parser_warnings=false', async () => {
    const appStore = useAppStore()
    appStore.sodarContext!.parser_warnings = false
    const wrapper = mountComponent()
    expect(wrapper.find(
      '#sodar-ss-op-item-warnings').classes()).toContain('disabled')
  })

  test('render ops dropdown with perms.create_colls=false', async () => {
    const appStore = useAppStore()
    appStore.sodarContext!.perms.create_colls = false
    const wrapper = mountComponent()
    expect(wrapper.find('#sodar-ss-op-item-irods').exists()).toBe(false)
  })

  test('render ops dropdown with perms.edit_sheet=false', async () => {
    const appStore = useAppStore()
    appStore.sodarContext!.perms.edit_sheet = false
    const wrapper = mountComponent()
    const expected = {
      'sync':       false,
      'import':     false,
      'create':     false,
      'edit':       false, // Changed
      'warnings':   false, // Changed
      'cache':      true,
      'replace':    false, // Changed
      'export':     true,
      'export-win': false,
      'irods':      true,
      'versions':   true,
      'tickets':    true,
      'requests':   false, // Changed
      'delete':     true,
    }
    expectDropdownItems(wrapper, expected)
  })

  test('render ops dropdown with perms.update_cache=false', async () => {
    const appStore = useAppStore()
    appStore.sodarContext!.perms.update_cache = false
    const wrapper = mountComponent()
    expect(wrapper.find('#sodar-ss-op-item-cache').exists()).toBe(false)
  })

  test('render ops dropdown with perms.view_tickets=false', async () => {
    const appStore = useAppStore()
    appStore.sodarContext!.perms.view_tickets = false
    const wrapper = mountComponent()
    expect(wrapper.find('#sodar-ss-op-item-tickets').exists()).toBe(false)
  })

  test('render ops dropdown with renderError', async () => {
    const tableStore = useTableStore()
    // TODO: Review the use of renderError (see #2408)
    tableStore.renderError = 'error'
    const wrapper = mountComponent()
    expect(wrapper.find('#sodar-ss-op-item-irods').exists()).toBe(false)
  })

  test('render ops dropdown with sheet_sync_enabled=true', async () => {
    const appStore = useAppStore()
    appStore.sodarContext!.sheet_sync_enabled = true
    const wrapper = mountComponent()
    const expected = {
      'sync':       true,  // Changed
      'import':     false,
      'create':     false,
      'edit':       false, // Changed
      'warnings':   true,
      'cache':      true,
      'replace':    false, // Changed
      'export':     true,
      'export-win': false,
      'irods':      true,
      'versions':   false, // Changed
      'tickets':    true,
      'requests':   true,
      'delete':     false, // Changed
    }
    expectDropdownItems(wrapper, expected)
  })

  test('render ops dropdown with sheetsAvailable=false', async () => {
    const appStore = useAppStore()
    // As sheetsAvailable is computed, we modify currentStudyUuid instead
    appStore.currentStudyUuid = ''
    const wrapper = mountComponent()
    const expected = {
      'sync':       false,
      'import':     true,  // Changed
      'create':     true,  // Changed
      'edit':       false, // Changed
      'warnings':   false, // Changed
      'cache':      false, // Changed
      'replace':    false, // Changed
      'export':     false, // Changed
      'export-win': false,
      'irods':      false, // Changed
      'versions':   false, // Changed
      'tickets':    false, // Changed
      'requests':   false, // Changed
      'delete':     false, // Changed
    }
    expectDropdownItems(wrapper, expected)
  })

  test(
      'render ops dropdown with sheet_sync_enabled=true and ' +
      'sheetsAvailable=false',
      async (
  ) => {
    const appStore = useAppStore()
    appStore.currentStudyUuid = ''
    appStore.sodarContext!.sheet_sync_enabled = true
    const wrapper = mountComponent()
    const expected = {
      'sync':       true,  // Changed
      'import':     false,
      'create':     false,
      'edit':       false, // Changed
      'warnings':   false, // Changed
      'cache':      false, // Changed
      'replace':    false, // Changed
      'export':     false, // Changed
      'export-win': false,
      'irods':      false, // Changed
      'versions':   false, // Changed
      'tickets':    false, // Changed
      'requests':   false, // Changed
      'delete':     false, // Changed
    }
    expectDropdownItems(wrapper, expected)
  })

  test('render ops dropdown with windowsOs=true', async () => {
    const appStore = useAppStore()
    appStore.windowsOs = true
    const wrapper = mountComponent()
    const expected = {
      'export':     false,
      'export-win': true,
    }
    expectDropdownItems(wrapper, expected)
  })

  test('open windows export modal with button click', async () => {
    const appStore = useAppStore()
    appStore.windowsOs = true
    expect(mockWinExportModal.methods.show).not.toHaveBeenCalled()

    const wrapper = mountComponent()
    await wrapper.find('#sodar-ss-op-item-export-win').trigger('click')
    expect(mockWinExportModal.methods.show).toHaveBeenCalled()
  })

  test('hide ops dropdown and show exit button with editMode',  async () => {
    const appStore = useAppStore()
    appStore.editMode = true
    const wrapper = mountComponent()
    expect(wrapper.find('#sodar-ss-op-dropdown').exists()).toBe(false)
    const btn = wrapper.find('#sodar-ss-btn-edit-finish')
    expect(btn.exists()).toBe(true)
    expect(btn.attributes().title).toBe(EDIT_MODE_EXIT_MSG)
    expect(btn.attributes().disabled).not.toBeDefined()
  })

  test('display exit button save title with editDataUpdated',  async () => {
    const appStore = useAppStore()
    appStore.editMode = true
    const editStore = useEditStore()
    editStore.versionSaved = false
    editStore.editDataUpdated = true
    const wrapper = mountComponent()
    expect(wrapper.find('#sodar-ss-op-dropdown').exists()).toBe(false)
    const btn = wrapper.find('#sodar-ss-btn-edit-finish')
    expect(btn.exists()).toBe(true)
    expect(btn.attributes().title).toBe(EDIT_MODE_EXIT_MSG + EDIT_MODE_SAVE_MSG)
    expect(btn.attributes().disabled).not.toBeDefined()
  })

  test('display exit button save title with unsavedRow',  async () => {
    const appStore = useAppStore()
    appStore.editMode = true
    const editStore = useEditStore()
    editStore.unsavedRow = { id: 'row0', tableUuid: STUDY_UUID }
    const wrapper = mountComponent()
    expect(wrapper.find('#sodar-ss-op-dropdown').exists()).toBe(false)
    const btn = wrapper.find('#sodar-ss-btn-edit-finish')
    expect(btn.exists()).toBe(true)
    expect(btn.attributes().title).toBe(EDIT_MODE_UNSAVED_MSG)
    // Button should be disabled
    expect(btn.attributes().disabled).toBeDefined()
  })

  test('enable edit mode from ops dropdown item',  async () => {
    const appStore = useAppStore()
    expect(appStore.editMode).toBe(false)
    const wrapper = mountComponent()
    await wrapper.find('#sodar-ss-op-item-edit').trigger('click')
    expect(appStore.editMode).toBe(true)
  })

  test('enable edit mode in overview view',  async () => {
    const appStore = useAppStore()
    appStore.viewActive = VIEW_OVERVIEW
    const wrapper = mountComponent()
    await wrapper.find('#sodar-ss-op-item-edit').trigger('click')
    expect(appStore.editMode).toBe(true)
    expect(appStore.viewActive).toBe(VIEW_STUDY)
  })

  test('enable edit mode in parser warning view',  async () => {
    const appStore = useAppStore()
    appStore.viewActive = VIEW_PARSER_WARNING
    const wrapper = mountComponent()
    await wrapper.find('#sodar-ss-op-item-edit').trigger('click')
    expect(appStore.editMode).toBe(true)
    expect(appStore.viewActive).toBe(VIEW_STUDY)
  })

  test('disable edit mode with finish edit button click',  async () => {
    const appStore = useAppStore()
    const editStore = useEditStore()
    appStore.editMode = true
    appStore.selectEnabled = false
    editStore.editDataUpdated = true
    editStore.enableRowSave = true

    mockFetch()
    const wrapper = mountComponent()
    expect(fetch).not.toHaveBeenCalled()
    await wrapper.find('#sodar-ss-btn-edit-finish').trigger('click')
    await flushPromises()

    expect(appStore.editMode).toBe(false)
    expect(appStore.selectEnabled).toBe(true)
    expect(editStore.editContext).toBe(null)
    expect(editStore.editDataUpdated).toBe(false)
    expect(editStore.editStudyData).toBe(false)
    expect(editStore.enableRowSave).toBe(false)
    expect(editStore.unsavedData).toBe(false)
    expect(editStore.unsavedRow).toBe(null)
    expect(editStore.updatingRow).toBe(false)
    expect(editStore.versionSaved).toBe(true)

    expect(fetch).toHaveBeenCalledWith(
      finishUrl,
      expect.objectContaining({
        body: JSON.stringify({
          updated: true, version_saved: true
        })
      }))
    expect(mockCreate).toHaveBeenCalledWith({
      body: EDIT_MSG_FINISH, modelValue: 1000, variant: 'success'
    })
  })

  test('disable edit mode with failed version save',  async () => {
    // Suppress logging as error message is expected
    vi.spyOn(console, 'error').mockImplementation(() => undefined)

    const appStore = useAppStore()
    const editStore = useEditStore()
    appStore.editMode = true
    editStore.editDataUpdated = true

    mockFetch('error', 500)
    const wrapper = mountComponent()
    await wrapper.find('#sodar-ss-btn-edit-finish').trigger('click')
    await flushPromises()

    expect(appStore.editMode).toBe(false)
    expect(fetch).toHaveBeenCalled()
    expect(mockCreate).toHaveBeenCalledWith({
      body: EDIT_MSG_SAVE_FAIL_PREFIX + 'error',
      modelValue: 2000,
      variant: 'danger',
    })
  })
})
