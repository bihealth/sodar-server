import { createLocalVue, mount } from '@vue/test-utils'
import {
  getAppStub,
  waitNT,
  waitRAF
} from '../testUtils.js'
import BootstrapVue from 'bootstrap-vue'
import VueClipboard from 'vue-clipboard2'
import VersionSaveModal from '@/components/modals/VersionSaveModal.vue'

// Set up extended Vue constructor
const localVue = createLocalVue()
localVue.use(BootstrapVue)
localVue.use(VueClipboard)

describe('VersionSaveModal.vue', () => {
  function getApp (params = {}) {
    const app = getAppStub(params)
    app.versionSaved = false
    return app
  }

  beforeAll(() => {
    // NOTE: Workaround for bootstrap-vue "Vue warn" errors, see issue #1034
    jest.spyOn(console, 'error').mockImplementation(jest.fn())
    // Disable warnings
    jest.spyOn(console, 'warn').mockImplementation(jest.fn())
  })

  beforeEach(() => {
    jest.resetModules()
    jest.clearAllMocks()
  })

  it('renders version save modal', async () => {
    const wrapper = mount(
      VersionSaveModal, { localVue, propsData: { app: getApp() } })
    wrapper.vm.showModal()
    await waitNT(wrapper.vm)
    await waitRAF()
    expect(wrapper.find('#sodar-ss-version-modal-content').exists()).toBe(true)
  })

  it('calls version save on button click', async () => {
    const wrapper = mount(
      VersionSaveModal, { localVue, propsData: { app: getApp() } })
    const spyOnPostSave = jest.spyOn(
      wrapper.vm, 'postSave').mockImplementation(jest.fn())
    wrapper.vm.showModal()
    await waitNT(wrapper.vm)
    await waitRAF()
    expect(wrapper.find('#sodar-ss-version-modal-content').exists()).toBe(true)

    await wrapper.find('#sodar-ss-btn-save').trigger('click')
    expect(spyOnPostSave).toBeCalled()
  })
})
