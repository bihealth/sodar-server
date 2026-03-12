import { describe, expect, test } from 'vitest'
import { mount } from '@vue/test-utils'
import WaitSection from '@/components/WaitSection.vue'

describe('StudyShortcutsRenderer.vue', () => {
  test('render component', async () => {
    const wrapper = mount(WaitSection)
    expect(wrapper.find('#sodar-ss-wait').exists()).toBe(true)
  })
})
