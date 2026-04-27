import { beforeEach, describe, expect, test } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

import ServerAlerts from '@/components/ServerAlerts.vue'
import { useAppStore } from '@/stores/appStore.ts'
import { type SodarContext } from '@/types.ts'

import { copy } from '../testUtils.ts'
import { sodarContext } from '../data/sodarContext.ts'
import { serverAlerts } from '../data/serverAlerts.ts'

describe('ServerAlerts.vue', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    const appStore = useAppStore()
    appStore.sodarContext = copy(sodarContext) as SodarContext
  })

  test('render component with default parameters', async () => {
    const wrapper = mount(ServerAlerts)
    expect(wrapper.find('#sodar-ss-version-alert').exists()).toBe(true)
    // No alerts should be present
    expect(wrapper.find('#sodar-ss-alert-container').exists()).toBe(false)
    expect(wrapper.findAll('.sodar-ss-server-alert').length).toBe(0)
  })

  test('render alerts', async () => {
    const appStore = useAppStore()
    appStore.sodarContext!.alerts = serverAlerts
    const wrapper = mount(ServerAlerts)
    expect(wrapper.find('#sodar-ss-version-alert').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-alert-container').exists()).toBe(true)
    const alerts = wrapper.findAll('.sodar-ss-server-alert')
    expect(alerts.length).toBe(2)
    expect(alerts[0]?.classes()).toContain('alert-info')
    expect(alerts[0]?.classes()).not.toContain('alert-danger')
    expect(alerts[0]?.html()).toContain('<p>First alert</p>')
    expect(alerts[1]?.classes()).not.toContain('alert-info')
    expect(alerts[1]?.classes()).toContain('alert-danger')
    expect(alerts[1]?.html()).toContain('<p><b>Second alert</b></p>')
  })

  test('render component with edit_sheet=false', async () => {
    const appStore = useAppStore()
    appStore.sodarContext!.alerts = serverAlerts
    appStore.sodarContext!.perms.edit_sheet = false
    const wrapper = mount(ServerAlerts)
    // Only version alert should be displayed
    expect(wrapper.find('#sodar-ss-version-alert').exists()).toBe(true)
    expect(wrapper.findAll('.sodar-ss-server-alert').length).toBe(0)
  })
})
