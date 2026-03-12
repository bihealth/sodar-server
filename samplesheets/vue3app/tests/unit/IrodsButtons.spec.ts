import { beforeEach, describe, expect, test, vi } from 'vitest'
import { config, mount, type VueWrapper } from '@vue/test-utils'
import { createBootstrap } from 'bootstrap-vue-next/plugins/createBootstrap'

import IrodsButtons from '@/components/IrodsButtons.vue'
import { copy } from '../testUtils.ts'
import { ASSAY_PATH } from '../testConstants.ts'
import { type IrodsButtonsProps } from '../testTypes.ts'

// Set up bootstrap-vue-next plugin to enable composable use
config.global.plugins = [createBootstrap()]

const defaultProps: IrodsButtonsProps = {
  editMode: false,
  enabled: true,
  extraLinks: [],
  irodsBackendEnabled: true,
  irodsDirModalRef: null,
  irodsWebdavUrl: 'https://davrods.local',
  irodsPath: ASSAY_PATH,
  irodsStatus: true,
  showFileList: true
}
let props: IrodsButtonsProps

describe('IrodsButtons.vue', () => {
  function mountComponent (): VueWrapper {
    return mount(IrodsButtons, { props: props })
  }
  beforeEach(() => {
    props = copy(defaultProps) as IrodsButtonsProps
  })

  test('render component with default properties', async () => {
    const wrapper = mountComponent()
    expect(wrapper.find('.sodar-ss-irods-links').exists()).toBe(true)
    const buttons = wrapper.findAll('.sodar-list-btn')
    expect(buttons.length).toBe(4)
    for (let i = 0; i < 3; i++) { // All buttons should be enabled
      expect(buttons[i]?.attributes().disabled).not.toBeDefined()
    }
    // Ensure variable button is present
    expect(wrapper.find('.sodar-ss-irods-list-btn').exists()).toBe(true)
  })

  test('hide list button with showFileList=false', async () => {
    props.showFileList = false
    const wrapper = mountComponent()
    expect(wrapper.findAll('.sodar-list-btn').length).toBe(3)
    expect(wrapper.find('.sodar-ss-irods-list-btn').exists()).toBe(false)
  })

  test('hide list button with irodsBackendEnabled=false', async () => {
    props.irodsBackendEnabled = false
    const wrapper = mountComponent()
    expect(wrapper.findAll('.sodar-list-btn').length).toBe(3)
    expect(wrapper.find('.sodar-ss-irods-list-btn').exists()).toBe(false)
  })

  test('hide list button with empty irodsWebdavUrl', async () => {
    props.irodsWebdavUrl = ''
    const wrapper = mountComponent()
    expect(wrapper.findAll('.sodar-list-btn').length).toBe(3)
    expect(wrapper.find('.sodar-ss-irods-list-btn').exists()).toBe(false)
  })

  test('disable buttons with editMode=true', async () => {
    props.editMode = true
    const wrapper = mountComponent()
    const buttons = wrapper.findAll('.sodar-list-btn')
    for (let i = 0; i < 3; i++) {
      expect(buttons[i]?.attributes().disabled).toBeDefined()
    }
  })

  test('disable buttons with irodsStatus=false', async () => {
    props.irodsStatus = false
    const wrapper = mountComponent()
    const buttons = wrapper.findAll('.sodar-list-btn')
    for (let i = 0; i < 3; i++) {
      expect(buttons[i]?.attributes().disabled).toBeDefined()
    }
  })

  test('disable buttons with enabled=false', async () => {
    props.enabled = false
    const wrapper = mountComponent()
    const buttons = wrapper.findAll('.sodar-list-btn')
    for (let i = 0; i < 3; i++) {
      expect(buttons[i]?.attributes().disabled).toBeDefined()
    }
  })

  test('open file dir modal on button click', async () => {
    const mockModal = { show: vi.fn() }
    expect(mockModal.show).not.toBeCalled()
    props.irodsDirModalRef = mockModal
    const wrapper = mountComponent()
    await wrapper.find('.sodar-ss-irods-list-btn').trigger('click')
    expect(mockModal.show).toBeCalled()
  })

  // TODO: Test clipboard copying
  // TODO: Test extra links display once supported (see #2403)
})
