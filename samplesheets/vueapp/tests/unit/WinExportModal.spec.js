import { createLocalVue, mount } from '@vue/test-utils'
import { projectUuid, getAppStub, waitNT, waitRAF } from '../testUtils.js'
import BootstrapVue from 'bootstrap-vue'
import WinExportModal from '@/components/modals/WinExportModal.vue'

// Set up extended Vue constructor
const localVue = createLocalVue()
localVue.use(BootstrapVue)

describe('WinExportModal.vue', () => {
  beforeAll(() => {
    // Disable warnings
    jest.spyOn(console, 'warn').mockImplementation(jest.fn())
  })

  beforeEach(() => {
    jest.resetModules()
    jest.clearAllMocks()
  })

  it('renders windows export notification modal', async () => {
    const wrapper = mount(
      WinExportModal, { localVue, propsData: { app: getAppStub() } })
    wrapper.vm.showModal()
    await waitNT(wrapper.vm)
    await waitRAF()

    expect(wrapper.find('#sodar-ss-irods-modal-content').exists()).toBe(true)
  })

  it('redirects to export on button click', async () => {
    // Recreate window location to check its value
    delete global.window.location
    global.window = Object.create(window)
    global.window.location = {
      port: '123',
      protocol: 'http:',
      hostname: 'localhost'
    }

    const wrapper = mount(
      WinExportModal, { localVue, propsData: { app: getAppStub() } })
    wrapper.vm.showModal()
    await waitNT(wrapper.vm)
    await waitRAF()

    expect(wrapper.find('#sodar-ss-irods-modal-content').exists()).toBe(true)
    await wrapper.find('#sodar-ss-win-export-btn').trigger('click')
    await waitNT(wrapper.vm)
    await waitRAF()
    // expect(spyOnExport).toHaveBeenCalled()
    expect(global.window.location.href).toBe('export/isa/' + projectUuid)
  })
})
