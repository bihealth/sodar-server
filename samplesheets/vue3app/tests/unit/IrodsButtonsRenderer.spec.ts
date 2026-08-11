import { type TemplateRef } from 'vue'
import { beforeEach, describe, expect, test, vi } from 'vitest'
import { config, mount, type VueWrapper } from '@vue/test-utils'
import { createBootstrap } from 'bootstrap-vue-next/plugins/createBootstrap'

import IrodsButtonsRenderer from '@/components/renderers/IrodsButtonsRenderer.vue'
import {
  type AssayIrodsPath,
  type IrodsButtonsRendererParams
} from '@/types.ts'
import { IRODS_PATH_COPY_MSG, VARIANT_INFO } from '@/constants.ts'

import { copy } from '../testUtils.ts'
import { ASSAY_PATH, ASSAY_PATH_PREFIX } from '../testConstants.ts'

// Test Data -------------------------------------------------------------------

const collName: string = '0814-N1-DNA1-WGS1'
const defaultParams: IrodsButtonsRendererParams = {
  assayIrodsPath: ASSAY_PATH,
  irodsBackendEnabled: true,
  irodsStatus: true,
  irodsWebdavUrl: 'https://davrods.local',
  modalRef: {} as TemplateRef,
  value: { path: ASSAY_PATH_PREFIX + collName, enabled: true }
}
let params: IrodsButtonsRendererParams

// Global Setup ----------------------------------------------------------------

config.global.plugins = [createBootstrap()]

// Mock clipboard (NOTE: has to be done in module root)
const mockCopy = vi.fn()
vi.mock('@vueuse/core', async () => {
  const actual = await vi.importActual('@vueuse/core')
  return { ...actual, useClipboard: () => ({ copy: mockCopy }) }
})

// Tests -----------------------------------------------------------------------

describe('IrodsButtonsRenderer.vue', () => {
  function mountComponent (): VueWrapper {
    return mount(IrodsButtonsRenderer, { props: { params: params } })
  }

  beforeEach(() => {
    params = copy(defaultParams) as IrodsButtonsRendererParams
    params.notifyCb = vi.fn()
  })

  test('render component with default params', async () => {
    const wrapper = mountComponent()
    expect(wrapper.find('.sodar-ss-irods-links').exists()).toBe(true)
    const buttons = wrapper.findAll('.sodar-list-btn')
    expect(buttons.length).toBe(4)
    for (let i = 0; i < 3; i++) { // All buttons should be enabled
      expect(buttons[i]?.attributes().disabled).not.toBeDefined()
    }
    // Assert variable button is present
    expect(wrapper.find('.sodar-ss-irods-list-btn').exists()).toBe(true)
    // Buttons should link to value path
    expect(wrapper.find('.sodar-irods-dav-btn').attributes().href).toBe(
      params.irodsWebdavUrl + (params.value as AssayIrodsPath).path)
  })

  test('render component with value.enabled=false', async () => {
    (params.value as AssayIrodsPath).enabled = false
    const wrapper = mountComponent()
    const buttons = wrapper.findAll('.sodar-list-btn')
    for (let i = 0; i < 3; i++) { // All buttons should be disabled
      expect(buttons[i]?.attributes().disabled).toBeDefined()
    }
  })

  test('render component with empty path in value', async () => {
    (params.value as AssayIrodsPath).path = ''
    const wrapper = mountComponent()
    const buttons = wrapper.findAll('.sodar-list-btn')
    for (let i = 0; i < 3; i++) { // All buttons should be disabled
      expect(buttons[i]?.attributes().disabled).toBeDefined()
    }
  })

  test('render component with no value', async () => {
    params.value = null
    const wrapper = mountComponent()
    const buttons = wrapper.findAll('.sodar-list-btn')
    for (let i = 0; i < 3; i++) { // All buttons should be enabled
      expect(buttons[i]?.attributes().disabled).not.toBeDefined()
    }
    // Buttons should link to assay root path
    expect(wrapper.find('.sodar-irods-dav-btn').attributes().href).toBe(
      params.irodsWebdavUrl + params.assayIrodsPath)
  })

  test('render component with irodsStatus=false', async () => {
    params.irodsStatus= false
    const wrapper = mountComponent()
    const buttons = wrapper.findAll('.sodar-list-btn')
    for (let i = 0; i < 3; i++) { // All buttons should be disabled
      expect(buttons[i]?.attributes().disabled).toBeDefined()
    }
  })

  test('copy iRODS path to clipboard on button click', async () => {
    const wrapper = mountComponent()
    await wrapper.find('.sodar-ss-irods-copy-btn').trigger('click')
    expect(mockCopy).toHaveBeenCalledWith(params.value!.path)
    expect(params.notifyCb).toHaveBeenCalledWith(
      IRODS_PATH_COPY_MSG, VARIANT_INFO)
  })

  // TODO: Test with edit mode
})
