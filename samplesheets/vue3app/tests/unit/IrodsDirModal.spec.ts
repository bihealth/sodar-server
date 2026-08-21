import { nextTick } from 'vue'
import { beforeEach, describe, expect, test, vi } from 'vitest'
import {
  config,
  mount,
  type DOMWrapper,
  type VueWrapper
} from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { createBootstrap } from 'bootstrap-vue-next/plugins/createBootstrap'
import prettyBytes from 'pretty-bytes'

import IrodsDirModal from '@/components/modals/IrodsDirModal.vue'
import { useAppStore } from '@/stores/appStore.ts'
import { type IrodsDirResponseBody, type SodarContext } from '@/types.ts'

import { copy, waitSelector } from '../testUtils.ts'
import { irodsDirFiles } from '../data/irodsDirFiles.ts'
import { sodarContext } from '../data/sodarContext.ts'
import {
  ASSAY_PATH_PREFIX,
  MISC_FILES_DIR,
  PROJECT_UUID,
  USER_UUID
} from '../testConstants.ts'

// Test Data -------------------------------------------------------------------

const errorMsg = 'Error'
const irodsPath = ASSAY_PATH_PREFIX + MISC_FILES_DIR
let dirBody: IrodsDirResponseBody

// Global Setup ----------------------------------------------------------------

config.global.plugins = [createBootstrap()]

// Tests -----------------------------------------------------------------------

describe('IrodsDirModal.vue', () => {
  function mockListFetch (
      status: number,
      body: IrodsDirResponseBody) {
    global.fetch = vi.fn(() =>
      Promise.resolve({
        json: () => Promise.resolve(body), status: status
      } as Response)
    )
  }

  function mockDataRequestFetch () {
    global.fetch = vi.fn(() =>
      Promise.resolve({
        json: () => Promise.resolve({ 'detail': 'ok' }), status: 200
      } as Response)
    )
  }

  function getCols (
      element: DOMWrapper<Element> | undefined
  ): Array<DOMWrapper<HTMLTableCellElement>> {
    if (!element) return []
    return element.findAll('td') as Array<DOMWrapper<HTMLTableCellElement>>
  }

  async function showModal (
      queryStatus: number,
      queryBody: IrodsDirResponseBody
  ): Promise<VueWrapper> {
    mockListFetch(queryStatus, queryBody)
    const wrapper = mount(IrodsDirModal)
    wrapper.vm.show(irodsPath)
    await nextTick() // Must wait for all reactive vals to update
    return wrapper
  }

  beforeEach(() => {
    setActivePinia(createPinia())
    const appStore = useAppStore()
    appStore.projectUuid = PROJECT_UUID
    appStore.sodarContext = copy(sodarContext) as SodarContext
    dirBody = { irods_data: copy(irodsDirFiles) } as IrodsDirResponseBody
  })

  test('render component with default data', async () => {
    const wrapper = await showModal(200, dirBody)
    expect(wrapper.find('#sodar-ss-irods-dir-modal').exists()).toBe(true)
    await waitSelector(wrapper, '#sodar-ss-irods-dir-modal-content', 1)
    expect(wrapper.findAll('.sodar-ss-irods-obj').length).toBe(3)
    expect(wrapper.find('#sodar-ss-irods-filter-empty').exists()).toBe(false)
    expect(wrapper.find(
      '#sodar-ss-irods-dir-modal-message').exists()).toBe(false)
  })

  test('render file item', async () => {
    const appStore = useAppStore()
    expect(appStore.getPerm('edit_sheet')).toBe(true)
    expect(appStore.getPerm('is_superuser')).toBe(false)
    expect(irodsDirFiles[0]?.irods_request_status).toBe(null)

    const wrapper = await showModal(200, dirBody)
    await waitSelector(wrapper, '#sodar-ss-irods-dir-modal-content', 1)
    const cols = getCols(wrapper.findAll('.sodar-ss-irods-obj')[0])

    expect(cols[0]?.find('a').attributes().href).toBe(
      sodarContext.irods_webdav_url + irodsDirFiles[0]?.path)
    expect(cols[0]?.find('a').text()).toBe('/' + irodsDirFiles[0]?.name)
    expect(cols[0]?.find('a').find('.text-muted').text()).toBe('/')
    expect(cols[1]?.text()).toBe(prettyBytes(irodsDirFiles[0]?.size as number))
    expect(cols[2]?.text()).toBe(irodsDirFiles[0]?.modify_time)
    for (let i = 0; i <= 2; i++) {
      expect(cols[i]?.classes()).not.toContain('text-strikethrough')
    }
    expect(cols[3]?.find('.sodar-ss-request-cancel-btn').exists()).toBe(false)
    expect(cols[3]?.find('.sodar-ss-request-delete-btn').exists()).toBe(true)
    expect(cols[3]?.find(
      '.sodar-ss-request-delete-btn').attributes().disabled).not.toBeDefined()
  })

  test('render item with active delete request', async () => {
    expect(irodsDirFiles[1]?.irods_request_status).toBe('ACTIVE')
    expect(irodsDirFiles[1]?.irods_request_user).toBe(USER_UUID)

    const wrapper = await showModal(200, dirBody)
    await waitSelector(wrapper, '#sodar-ss-irods-dir-modal-content', 1)
    const cols = getCols(wrapper.findAll('.sodar-ss-irods-obj')[1])

    for (let i = 0; i <= 2; i++) {
      expect(cols[i]?.classes()).toContain('text-strikethrough')
    }
    expect(cols[3]?.find('.sodar-ss-request-cancel-btn').exists()).toBe(true)
    expect(cols[3]?.find(
      '.sodar-ss-request-cancel-btn').attributes().disabled).not.toBeDefined()
    expect(cols[3]?.find('.sodar-ss-request-delete-btn').exists()).toBe(false)
  })

  test('render item with delete request from another user', async () => {
    expect(irodsDirFiles[2]?.irods_request_status).toBe('ACTIVE')
    expect(irodsDirFiles[2]?.irods_request_user).not.toBe(USER_UUID)

    const wrapper = await showModal(200, dirBody)
    await waitSelector(wrapper, '#sodar-ss-irods-dir-modal-content', 1)
    const cols = getCols(wrapper.findAll('.sodar-ss-irods-obj')[2])

    for (let i = 0; i <= 2; i++) {
      expect(cols[i]?.classes()).toContain('text-strikethrough')
    }
    expect(cols[3]?.find('.sodar-ss-request-cancel-btn').exists()).toBe(true)
    // Cancel button should be disabled
    expect(cols[3]?.find(
      '.sodar-ss-request-cancel-btn').attributes().disabled).toBeDefined()
    expect(cols[3]?.find('.sodar-ss-request-delete-btn').exists()).toBe(false)
  })

  test('render item with path in subcollection', async () => {
    const wrapper = await showModal(200, dirBody)
    await waitSelector(wrapper, '#sodar-ss-irods-dir-modal-content', 1)
    const cols = getCols(wrapper.findAll('.sodar-ss-irods-obj')[1])

    expect(cols[0]?.find('a').text()).toBe('subcoll/' + irodsDirFiles[1]?.name)
    expect(cols[0]?.find('a').find('.text-muted').text()).toBe('subcoll/')
  })

  test('render item with path in nested subcollections', async () => {
    const wrapper = await showModal(200, dirBody)
    await waitSelector(wrapper, '#sodar-ss-irods-dir-modal-content', 1)
    const cols = getCols(wrapper.findAll('.sodar-ss-irods-obj')[2])

    expect(cols[0]?.find('a').text()).toBe(
      'subcoll/subcoll2/' + irodsDirFiles[2]?.name)
    expect(cols[0]?.find('a').find(
      '.text-muted').text()).toBe('subcoll/subcoll2/')
  })

  test('render item with edit_sheet=false', async () => {
    const appStore = useAppStore()
    appStore.sodarContext!.perms.edit_sheet = false
    expect(appStore.getPerm('edit_sheet')).toBe(false)

    const wrapper = await showModal(200, dirBody)
    await waitSelector(wrapper, '#sodar-ss-irods-dir-modal-content', 1)
    const cols = getCols(wrapper.findAll('.sodar-ss-irods-obj')[0])

    // Delete button should be disabled
    expect(cols[3]?.find(
      '.sodar-ss-request-delete-btn').attributes().disabled).toBeDefined()
  })

  test(
      'render item with with delete request from another user as superuser',
      async (
  ) => {
    const appStore = useAppStore()
    appStore.sodarContext!.perms.is_superuser = true
    expect(appStore.getPerm('is_superuser')).toBe(true)

    const wrapper = await showModal(200, dirBody)
    await waitSelector(wrapper, '#sodar-ss-irods-dir-modal-content', 1)
    const cols = getCols(wrapper.findAll('.sodar-ss-irods-obj')[2])

    // Cancel button should not be disabled
    expect(cols[3]?.find(
      '.sodar-ss-request-cancel-btn').attributes().disabled).not.toBeDefined()
  })

  test('render component with empty collection', async () => {
    const wrapper = await showModal(200, { irods_data: [] })
    await waitSelector(wrapper, '#sodar-ss-irods-dir-modal-empty', 1)
    expect(wrapper.find(
      '#sodar-ss-irods-dir-modal-content').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-irods-dir-modal-empty').exists()).toBe(true)
    expect(wrapper.find(
      '#sodar-ss-irods-dir-modal-message').exists()).toBe(false)
  })

  test('render component with detail in return data', async () => {
    const wrapper = await showModal(200, { detail: errorMsg })
    await waitSelector(wrapper, '#sodar-ss-irods-dir-modal-message', 1)
    expect(wrapper.find(
      '#sodar-ss-irods-dir-modal-content').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-irods-dir-modal-empty').exists()).toBe(false)
    expect(wrapper.find(
      '#sodar-ss-irods-dir-modal-message').exists()).toBe(true)
  })

  test('submit delete request', async () => {
    const wrapper = await showModal(200, dirBody)
    await waitSelector(wrapper, '#sodar-ss-irods-dir-modal-content', 1)
    const cols = getCols(wrapper.findAll('.sodar-ss-irods-obj')[0])

    global.confirm = vi.fn(() => true)
    mockDataRequestFetch()
    expect(global.confirm).not.toHaveBeenCalled()
    expect(global.fetch).not.toHaveBeenCalled()

    const btn = cols[3]?.find('.sodar-ss-request-delete-btn')
    await btn?.trigger('click')
    expect(global.confirm).toHaveBeenCalled()
    expect(global.fetch).toHaveBeenCalled()
  })

  test('cancel delete request', async () => {
    const wrapper = await showModal(200, dirBody)
    await waitSelector(wrapper, '#sodar-ss-irods-dir-modal-content', 1)
    const cols = getCols(wrapper.findAll('.sodar-ss-irods-obj')[1])

    global.confirm = vi.fn(() => true)
    mockDataRequestFetch()
    expect(global.confirm).not.toHaveBeenCalled()
    expect(global.fetch).not.toHaveBeenCalled()

    const btn = cols[3]?.find('.sodar-ss-request-cancel-btn')
    await btn?.trigger('click')
    // Confirmation is not needed for cancelling
    expect(global.confirm).not.toHaveBeenCalled()
    expect(global.fetch).toHaveBeenCalled()
  })

  // TODO: Test filtering
})
