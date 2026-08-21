import { type TemplateRef } from 'vue'
import { beforeEach, describe, expect, test, vi } from 'vitest'
import { mount, type VueWrapper } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

import HeaderEditRenderer from '@/components/renderers/HeaderEditRenderer.vue'
import { useEditStore } from '@/stores/editStore.ts'
import { type HeaderEditRendererParamInput } from '@/types.ts'
import { DB_OBJ_CLASS_MATERIAL } from '@/constants.ts'

import { copy } from '../testUtils.ts'
import { STUDY_UUID } from '../testConstants.ts'

// Test Data -------------------------------------------------------------------

const mockModal = { show: vi.fn() }
const defaultParams: HeaderEditRendererParamInput = {
  assayMode: false,
  assayUuid: null,
  canEditConfig: true,
  colType: 'NAME',
  configFieldIdx: 0,
  configNodeIdx: 0,
  editConfigField: {
    name: 'Name',
    type: 'name'
  },
  editable: true,
  headerType: 'name',
  modalRef: {} as unknown as TemplateRef,
  objCls: DB_OBJ_CLASS_MATERIAL
}
let params: HeaderEditRendererParamInput
const unsavedRow = { id: 'row170', tableUuid: STUDY_UUID }

// Tests -----------------------------------------------------------------------

describe('HeaderEditRenderer.vue', () => {
  function mountComponent (): VueWrapper {
    return mount(HeaderEditRenderer, { props: { params: params } })
  }

  beforeEach(() => {
    vi.resetAllMocks()
    setActivePinia(createPinia())
    params = copy(defaultParams) as HeaderEditRendererParamInput
    params.modalRef = mockModal as unknown as TemplateRef
  })

  test('render component with default data', async () => {
    const editStore = useEditStore()
    expect(editStore.unsavedRow).toBe(null)

    const wrapper = mountComponent()
    expect(wrapper.find('.sodar-ss-header-edit').exists()).toBe(true)
    const btn = wrapper.find('.sodar-ss-col-config-btn')
    expect(btn.exists()).toBe(true)
    expect(btn.attributes().disabled).not.toBeDefined()
  })

  test('disable button with unsaved row and disallowed column', async () => {
    const editStore = useEditStore()
    editStore.unsavedRow = unsavedRow
    const wrapper = mountComponent()
    // Column type is NAME, button should be disabled
    expect(wrapper.find(
      '.sodar-ss-col-config-btn').attributes().disabled).toBeDefined()
  })

  test('disable button with unsaved row and allowed column', async () => {
    const editStore = useEditStore()
    editStore.unsavedRow = unsavedRow
    params.colType = null // No specific column type = regular string
    const wrapper = mountComponent()
    // Button should be enabled
    expect(wrapper.find(
      '.sodar-ss-col-config-btn').attributes().disabled).not.toBeDefined()
  })

  test('Open modal on button click', async () => {
    const wrapper = mountComponent()
    expect(mockModal.show).not.toHaveBeenCalled()
    await wrapper.find('.sodar-ss-col-config-btn').trigger('click')
    expect(mockModal.show).toHaveBeenCalled()
  })
})
