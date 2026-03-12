import { beforeEach, describe, expect, test, vi } from 'vitest'
import { mount, type VueWrapper } from '@vue/test-utils'

import ModalHeader from '@/components/modals/ModalHeader.vue'

const mockModal = { hide: vi.fn() }
const props = {
  modalRef: mockModal,
  title: 'Modal Title'
}

describe('ModalHeader.vue', () => {
  function mountComponent (): VueWrapper {
    return mount(ModalHeader, { props: props })
  }
  beforeEach(() => {})

  test('render component', async () => {
    const wrapper = mountComponent()
    expect(wrapper.find('.sodar-ss-modal-header').exists()).toBe(true)
    expect(wrapper.find('h5').text()).toBe(props.title)
  })

  test('open modal on button click', async () => {
    const wrapper = mountComponent()
    expect(props.modalRef.hide).not.toBeCalled()
    await wrapper.find('.modal-close').trigger('click')
    expect(props.modalRef.hide).toBeCalled()
  })
})
