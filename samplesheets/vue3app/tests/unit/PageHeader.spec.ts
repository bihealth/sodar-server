import { beforeEach, describe, expect, test } from 'vitest'
import { mount, type VueWrapper } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { createRouter, createWebHashHistory, type Router } from 'vue-router'
import { createBootstrap } from 'bootstrap-vue-next/plugins/createBootstrap'

import PageHeader from '@/components/PageHeader.vue'
import { useAppStore, type SodarContext } from '@/stores/appStore.ts'
import { useEditStore } from '@/stores/editStore.ts'
import { useTableStore } from '@/stores/tableStore.ts'
import { routes } from '@/router/index.ts'
import {
  EDIT_BADGE_DEFAULT_LABEL,
  EDIT_BADGE_SAVED_LABEL,
  EDIT_BADGE_UNSAVED_LABEL,
  EDIT_MODE_EXIT_MSG,
  EDIT_MODE_SAVE_MSG,
  EDIT_MODE_UNSAVED_MSG,
  STUDY_NAV_DROPDOWN_LEN,
  STUDY_NAV_TAB_LEN
} from '@/constants.ts'

import { sodarContext } from '../data/sodarContext.ts'
import { copy } from '../testUtils.ts'
import { ASSAY_UUID, PROJECT_UUID, STUDY_UUID } from '../testConstants.ts'

let router: Router

describe('PageHeader.vue', () => {
  function expectDropdownItems (
      wrapper: VueWrapper,
      items: { [key: string]: boolean }
  ) {
    for (const [k, v] of Object.entries(items)) {
      expect(
        wrapper.find('#sodar-ss-op-item-' + k).exists(),
        'Key = ' + k).toBe(v)
    }
  }

  function mountComponent (): VueWrapper {
    return mount(PageHeader, {
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
    appStore.editMode = false
    appStore.gridsBusy = false
    appStore.gridsLoaded = true
    appStore.overviewActive = false
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

  test('render nav tabs with overviewActive=true', async () => {
    const appStore = useAppStore()
    appStore.overviewActive = true
    const wrapper = mountComponent()
    const studyBtn = wrapper.find('.sodar-ss-nav-tab-study')
    expect(studyBtn.classes()).not.toContain('active')
    expect(studyBtn.attributes().disabled).not.toBeDefined()
    const overBtn = wrapper.find('#sodar-ss-nav-tab-overview')
    expect(overBtn.classes()).toContain('active')
    expect(overBtn.attributes().disabled).not.toBeDefined()
  })

  test('navigate to overview with nav tabs', async () => {
    const appStore = useAppStore()
    expect(appStore.overviewActive).toBe(false)
    const wrapper = mountComponent()
    const studyBtn = wrapper.find('.sodar-ss-nav-tab-study')
    const overBtn = wrapper.find('#sodar-ss-nav-tab-overview')
    await overBtn.trigger('click')
    expect(appStore.overviewActive).toBe(true)
    // TODO: The following does not seem to work, fix?
    // await router.isReady()
    // expect(router.currentRoute.value.name).toBe('overview')
    expect(studyBtn.classes()).not.toContain('active')
    expect(overBtn.classes()).toContain('active')
  })

  test('navigate to study view with nav tabs', async () => {
    const appStore = useAppStore()
    appStore.overviewActive = true
    const wrapper = mountComponent()
    const studyBtn = wrapper.find('.sodar-ss-nav-tab-study')
    const overBtn = wrapper.find('#sodar-ss-nav-tab-overview')
    await studyBtn.trigger('click')
    expect(appStore.overviewActive).toBe(false)
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
    expect(wrapper.findAll('.sodar-ss-nav-item').length).toBe(3)
    expect(wrapper.find('#sodar-ss-nav-study-' + STUDY_UUID).attributes(
    ).disabled).not.toBeDefined()
    expect(wrapper.find('#sodar-ss-nav-assay-' + ASSAY_UUID).attributes(
    ).disabled).not.toBeDefined()
    // Overview link should be disabled
    expect(wrapper.find(
      '#sodar-ss-nav-overview').attributes().disabled).toBeDefined()
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
    expect(appStore.overviewActive).toBe(false)
    const wrapper = mountComponent()
    const overLink = wrapper.find('#sodar-ss-nav-overview')
    await overLink.trigger('click')
    expect(appStore.overviewActive).toBe(true)
  })

  test('navigate to study view with nav dropdown', async () => {
    const appStore = useAppStore()
    appStore.overviewActive = true
    const wrapper = mountComponent()
    const studyLink = wrapper.find('#sodar-ss-nav-study-' + STUDY_UUID)
    await studyLink.trigger('click')
    expect(appStore.overviewActive).toBe(false)
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
    expect(editStore.versionSaved).toBe(false)
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
    expect(appStore.overviewActive).toBe(false)
    const wrapper = mountComponent()
    await wrapper.find('#sodar-ss-op-item-edit').trigger('click')
    expect(appStore.editMode).toBe(true)
  })

  test('enable edit mode in overview view',  async () => {
    const appStore = useAppStore()
    appStore.overviewActive = true
    const wrapper = mountComponent()
    await wrapper.find('#sodar-ss-op-item-edit').trigger('click')
    expect(appStore.editMode).toBe(true)
    expect(appStore.overviewActive).toBe(false)
  })

  test('disable edit mode from finish edit button',  async () => {
    const appStore = useAppStore()
    appStore.editMode = true
    const wrapper = mountComponent()
    await wrapper.find('#sodar-ss-btn-edit-finish').trigger('click')
    expect(appStore.editMode).toBe(false)
  })

  // TODO: Assert finish editing actions once implemented
})
