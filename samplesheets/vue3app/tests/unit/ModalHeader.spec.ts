import { beforeEach, describe, expect, test, vi, type Mock } from 'vitest'
import { mount, type VueWrapper } from '@vue/test-utils'

import ModalHeader from '@/components/modals/ModalHeader.vue'
import { copy } from '../testUtils.ts'

interface ModalHeaderProps {
  modalRef: { hide: Mock },
  title: string,
  hideCloseButton?: boolean
}

const defaultProps: ModalHeaderProps = {
  modalRef: { hide: vi.fn() },
  title: 'Modal Title'
}
let props: ModalHeaderProps

describe('ModalHeader.vue', () => {
  function mountComponent (): VueWrapper {
    return mount(ModalHeader, { props: props })
  }
  beforeEach(() => {
    props = copy(defaultProps) as ModalHeaderProps
    props.modalRef = { hide: vi.fn() }
  })

  test('render component', async () => {
    const wrapper = mountComponent()
    expect(wrapper.find('.sodar-ss-modal-header').exists()).toBe(true)
    expect(wrapper.find('h5').text()).toBe(props.title)
    expect(wrapper.find('.modal-close').exists()).toBe(true)
  })

  test('render component with hideCloseButton=true', async () => {
    props.hideCloseButton = true
    const wrapper = mountComponent()
    expect(wrapper.find('.sodar-ss-modal-header').exists()).toBe(true)
    expect(wrapper.find('.modal-close').exists()).toBe(false)
  })

  test('hide modal on button click', async () => {
    const wrapper = mountComponent()
    expect(props.modalRef.hide).not.toBeCalled()
    await wrapper.find('.modal-close').trigger('click')
    expect(props.modalRef.hide).toBeCalled()
  })
})
