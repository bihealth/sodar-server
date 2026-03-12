import { type TemplateRef } from 'vue'
import { beforeEach, describe, expect, test, vi } from 'vitest'
import { config, mount, type VueWrapper } from '@vue/test-utils'
import { createBootstrap } from 'bootstrap-vue-next/plugins/createBootstrap'

import StudyShortcutsRenderer from '@/components/renderers/StudyShortcutsRenderer.vue'
import {
  type StudyShortcutCell,
  type StudyShortcutQuery,
  type StudyShortcutSchema,
  type StudyShortcutsRendererParams
} from '@/types.ts'
import { copy } from '../testUtils.ts'

const igvOpenUrlPrefix: string =
  'http://127.0.0.1:60151/load?genome=b37&merge=false&file='
const sessionRenderPath: string =
  '/samplesheets/study/germline/render/igv/33333333-3333-3333-3333-333333333333'
const igvUrl: string = igvOpenUrlPrefix + encodeURIComponent(
  sessionRenderPath + '.xml')
const schema: StudyShortcutSchema = {
  igv: {
    type: 'link',
    icon: 'mdi:open-in-new',
    title: 'Open IGV session file for pedigree in IGV',
  },
  files: {
    type: 'modal',
    icon: 'mdi:folder-open-outline',
    title: 'View links to pedigree BAM/CRAM, VCF and IGV session files',
  },
}
const value: StudyShortcutCell = {
  igv: {
    url: igvUrl,
    enabled: true
  },
  files: {
    query: { source: '0814' } as unknown as StudyShortcutQuery,
    enabled: true
  }
}

const defaultParams: StudyShortcutsRendererParams = {
  modalRef: {} as TemplateRef,
  schema: schema,
  value: value
}
let params: StudyShortcutsRendererParams

config.global.plugins = [createBootstrap()]

describe('StudyShortcutsRenderer.vue', () => {
  function mountComponent (): VueWrapper {
    return mount(StudyShortcutsRenderer, { props: { params: params } })
  }
  beforeEach(() => {
    params = copy(defaultParams) as StudyShortcutsRendererParams
  })

  test('render component with default params', async () => {
    const wrapper = mountComponent()
    expect(wrapper.find('.sodar-ss-study-shortcuts').exists()).toBe(true)
    expect(wrapper.findAll('.sodar-ss-irods-btn').length).toBe(2)
    expect(wrapper.find('.sodar-ss-study-link-btn').exists()).toBe(true)
    expect(wrapper.find('.sodar-ss-study-modal-btn').exists()).toBe(true)
  })

  test('render link button with default params', async () => {
    const wrapper = mountComponent()
    const btn = wrapper.find('.sodar-ss-study-link-btn')
    expect(btn.classes()).not.toContain('disabled')
    expect(btn.attributes().href).toBe(value.igv.url)
    expect(btn.attributes().title).toBe(schema.igv?.title)
    expect(btn.find('i').attributes()['data-icon']).toBe(schema.igv?.icon)
  })

  test('render link button as disabled', async () => {
    params.value.igv.enabled = false
    const wrapper = mountComponent()
    const btn = wrapper.find('.sodar-ss-study-link-btn')
    expect(btn.classes()).toContain('disabled')
  })

  test('render modal button with default params', async () => {
    const wrapper = mountComponent()
    const btn = wrapper.find('.sodar-ss-study-modal-btn')
    expect(btn.attributes().disabled).not.toBeDefined()
    expect(btn.attributes().title).toBe(schema.files?.title)
    expect(btn.find('i').attributes()['data-icon']).toBe(schema.files?.icon)
  })

  test('render modal button as disabled', async () => {
    params.value.files.enabled = false
    const wrapper = mountComponent()
    const btn = wrapper.find('.sodar-ss-study-modal-btn')
    expect(btn.attributes().disabled).toBeDefined()
  })

  test('open modal with modal button click', async () => {
    const mockModal = { show: vi.fn() }
    expect(mockModal.show).not.toBeCalled()
    params.modalRef = mockModal as unknown as TemplateRef
    const wrapper = mountComponent()
    const btn = wrapper.find('.sodar-ss-study-modal-btn')
    await btn.trigger('click')
    expect(mockModal.show).toBeCalled()
  })
})
