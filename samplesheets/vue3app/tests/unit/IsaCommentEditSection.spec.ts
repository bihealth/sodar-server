import { beforeEach, describe, expect, test } from 'vitest'
import { config, mount, type VueWrapper } from '@vue/test-utils'
import { createBootstrap } from 'bootstrap-vue-next/plugins/createBootstrap'


import IsaCommentEditSection from '@/components/modals/include/IsaCommentEditSection.vue'
import { copy } from '../testUtils.ts'
import { type IsaCommentEditSectionProps } from '../testTypes.ts'


// Test Data -------------------------------------------------------------------

const cKey = 'Comment 1'
const cKey2 = 'Comment 2'
const cKey3 = 'Comment 3'
const cVal = 'value'
const defaultProps: IsaCommentEditSectionProps = {
  comments: {
    [cKey]: 'abc',
    [cKey2]: '',
  },
  mandatory: [],
}
let props: IsaCommentEditSectionProps

const rowSel = '.sodar-ss-isa-comment-edit-row'
const manIconSel = '.sodar-ss-isa-comment-mandatory-icon'
const inputSel = '.sodar-ss-isa-comment-input'
const delBtnSel = '.sodar-ss-isa-comment-delete-btn'
const insKeySel = '.sodar-ss-isa-comment-insert-key'
const insValSel = '.sodar-ss-isa-comment-insert-value'
const insBtnSel = '.sodar-ss-isa-comment-insert-btn'

// Global Setup ----------------------------------------------------------------

config.global.plugins = [createBootstrap()]

// Tests -----------------------------------------------------------------------

describe('IsaCommentEditSection.vue', () => {
  function mountComponent (): VueWrapper {
    return mount(IsaCommentEditSection, { props: props })
  }

  beforeEach(() => {
    props = copy(defaultProps) as IsaCommentEditSectionProps
  })

  test('render component with default properties', async () => {
    const wrapper = mountComponent()
    expect(wrapper.find('.sodar-ss-isa-comment-edit-body').exists()).toBe(true)
    expect(wrapper.find(manIconSel).exists()).toBe(false)

    const rows = wrapper.findAll(rowSel)
    expect(rows.length).toBe(2)
    expect(rows[0]!.findAll('td')[0]!.text()).toBe(cKey)
    expect(rows[0]!.find(
      inputSel)!.attributes().value).toBe(props.comments[cKey])
    expect(rows[0]!.find(delBtnSel).attributes().disabled).not.toBeDefined()
    expect(rows[1]!.findAll('td')[0]!.text()).toBe(cKey2)
    expect(rows[1]!.find(
      inputSel)!.attributes().value).toBe(props.comments[cKey2])
    expect(rows[1]!.find(delBtnSel).attributes().disabled).not.toBeDefined()

    expect(wrapper.find(insKeySel).attributes().value).toBe('')
    expect(wrapper.find(insValSel).attributes().value).toBe('')
    expect(wrapper.find(insBtnSel).attributes().disabled).toBeDefined()
  })

  test('render component with mandatory comment', async () => {
    props.mandatory = [cKey]
    const wrapper = mountComponent()

    const rows = wrapper.findAll(rowSel)
    // First row should have mandatory icon
    expect(rows[0]!.find(manIconSel).exists()).toBe(true)
    expect(rows[1]!.find(manIconSel).exists()).toBe(false)
    // Delete button for first row should be defined
    expect(rows[0]!.find(delBtnSel).attributes().disabled).toBeDefined()
    expect(rows[1]!.find(delBtnSel).attributes().disabled).not.toBeDefined()
  })

  test('delete comment', async () => {
    const wrapper = mountComponent()
    let rows = wrapper.findAll(rowSel)
    expect(rows.length).toBe(2)
    await rows[0]!.find(delBtnSel).trigger('click')
    rows = wrapper.findAll(rowSel)
    expect(rows.length).toBe(1)
    expect(rows[0]!.findAll('td')[0]!.text()).toBe(cKey2)
  })

  test('insert comment', async () => {
    const wrapper = mountComponent()
    await wrapper.find(insKeySel).setValue(cKey3)
    await wrapper.find(insValSel).setValue(cVal)
    expect(wrapper.find(insKeySel).classes()).not.toContain('text-danger')
    await wrapper.find(insBtnSel).trigger('click')

    const rows = wrapper.findAll(rowSel)
    expect(rows.length).toBe(3)
    expect(rows[2]!.findAll('td')[0]!.text()).toBe(cKey3)
    expect(rows[2]!.find(inputSel)!.attributes().value).toBe(cVal)
  })

  test('insert comment', async () => {
    const wrapper = mountComponent()
    await wrapper.find(insKeySel).setValue(cKey3)
    await wrapper.find(insValSel).setValue(cVal)
    expect(wrapper.find(insKeySel).classes()).not.toContain('text-danger')
    await wrapper.find(insBtnSel).trigger('click')

    const rows = wrapper.findAll(rowSel)
    expect(rows.length).toBe(3)
    expect(rows[2]!.findAll('td')[0]!.text()).toBe(cKey3)
    expect(rows[2]!.find(inputSel)!.attributes().value).toBe(cVal)

    expect(wrapper.find(insKeySel).attributes().value).toBe('')
    expect(wrapper.find(insValSel).attributes().value).toBe('')
  })

  test('enter insert comment key without value', async () => {
    const wrapper = mountComponent()
    await wrapper.find(insKeySel).setValue(cKey3)
    expect(wrapper.find(insKeySel).classes()).not.toContain('text-danger')
    expect(wrapper.find(insBtnSel).attributes().disabled).toBeDefined()
  })

  test('enter insert comment value without key', async () => {
    const wrapper = mountComponent()
    await wrapper.find(insValSel).setValue(cVal)
    expect(wrapper.find(insKeySel).classes()).not.toContain('text-danger')
    expect(wrapper.find(insBtnSel).attributes().disabled).toBeDefined()
  })

  test('enter duplicate key', async () => {
    const wrapper = mountComponent()
    await wrapper.find(insKeySel).setValue(cKey.toLowerCase())
    await wrapper.find(insValSel).setValue(cVal)
    expect(wrapper.find(insKeySel).classes()).toContain('text-danger')
    expect(wrapper.find(insBtnSel).attributes().disabled).toBeDefined()
  })
})
