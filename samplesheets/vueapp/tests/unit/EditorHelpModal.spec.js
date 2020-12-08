import { createLocalVue, mount } from '@vue/test-utils'
import { waitNT, waitRAF } from '../testUtils.js'
import BootstrapVue from 'bootstrap-vue'
import EditorHelpModal from '@/components/modals/EditorHelpModal.vue'

// Set up extended Vue constructor
const localVue = createLocalVue()
localVue.use(BootstrapVue)

describe('EditorHelpModal.vue', () => {
  beforeAll(() => {
    // Disable warnings
    jest.spyOn(console, 'warn').mockImplementation(jest.fn())
  })

  beforeEach(() => {
    jest.resetModules()
    jest.clearAllMocks()
  })

  it('renders editor help modal', async () => {
    const wrapper = mount(EditorHelpModal, { localVue })
    wrapper.vm.showModal()
    await waitNT(wrapper.vm)
    await waitRAF()

    expect(wrapper.find('#sodar-ss-editor-help-modal-content').exists()).toBe(true)
  })
})
