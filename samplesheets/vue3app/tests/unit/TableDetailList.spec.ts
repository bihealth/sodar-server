import { beforeEach, describe, expect, test, vi } from 'vitest'
import { config, mount, type VueWrapper } from '@vue/test-utils'
import { createBootstrap } from 'bootstrap-vue-next/plugins/createBootstrap'

import TableDetailList from '@/components/TableDetailList.vue'
import {
  ASSAY_META_FIELDS,
  ASSAY_SODAR_FIELDS,
  COPY_MSG_SUFFIX,
  STUDY_META_FIELDS,
  STUDY_SODAR_FIELDS,
  VARIANT_INFO,
} from '@/constants.ts'

import { copy } from '../testUtils.ts'
import { sodarContextAssay, sodarContextStudy } from '../data/sodarContext.ts'
import { ASSAY_UUID, STUDY_UUID } from '../testConstants.ts'
import { type TableDetailListProps } from '../testTypes.ts'

// Test Data -------------------------------------------------------------------

const studyProps: TableDetailListProps = {
  assayMode: false,
  tableUuid: STUDY_UUID,
  tableContext: sodarContextStudy,
  tableMetaFields: STUDY_META_FIELDS,
  tableSodarFields: STUDY_SODAR_FIELDS
}
const assayProps: TableDetailListProps = {
  assayMode: true,
  tableUuid: ASSAY_UUID,
  tableContext: sodarContextAssay,
  tableMetaFields: ASSAY_META_FIELDS,
  tableSodarFields: ASSAY_SODAR_FIELDS
}
let props: TableDetailListProps

// Global Setup ----------------------------------------------------------------

config.global.plugins = [createBootstrap()]

// Mock clipboard
const mockCopy = vi.fn()
vi.mock('@vueuse/core', async () => {
  const actual = await vi.importActual('@vueuse/core')
  return { ...actual, useClipboard: () => ({ copy: mockCopy }) }
})

// Tests -----------------------------------------------------------------------

describe('TableDetailList.vue', () => {
  function mountComponent (propVals: TableDetailListProps): VueWrapper {
    props = copy(propVals) as TableDetailListProps
    props.notifyCb = vi.fn()
    return mount(TableDetailList, { props: props })
  }

  beforeEach(() => {
    vi.resetAllMocks()
  })

  test('render component for study', async () => {
    const wrapper = mountComponent(studyProps)
    expect(wrapper.find(
      '#sodar-ss-table-detail-container-' + STUDY_UUID).exists()).toBe(true)
    expect(wrapper.findAll('.sodar-ss-table-detail-row-meta').length).toBe(
      STUDY_META_FIELDS.length)
    expect(wrapper.findAll('.sodar-ss-table-detail-row-sodar').length).toBe(
      STUDY_SODAR_FIELDS.length + 1) // The last 1 is for SODAR UUID
    expect(wrapper.find('.text-info').exists()).toBe(true)
    expect(wrapper.find('.text-danger').exists()).toBe(false)
  })

  test('render component for assay', async () => {
    const wrapper = mountComponent(assayProps)
    expect(wrapper.find(
      '#sodar-ss-table-detail-container-' + ASSAY_UUID).exists()).toBe(true)
    expect(wrapper.findAll('.sodar-ss-table-detail-row-meta').length).toBe(
      ASSAY_META_FIELDS.length)
    expect(wrapper.findAll('.sodar-ss-table-detail-row-sodar').length).toBe(
      ASSAY_SODAR_FIELDS.length + 1)
    expect(wrapper.find('.text-info').exists()).toBe(false)
    expect(wrapper.find('.text-danger').exists()).toBe(true)
  })

  test('copy value into clipboard', async () => {
    expect(mockCopy).not.toHaveBeenCalled()
    expect(props.notifyCb).not.toHaveBeenCalled()

    const wrapper = mountComponent(studyProps)
    const buttons = wrapper.findAll('.sodar-ss-clip-copy-btn')
    expect(buttons.length).toBe(1)
    await buttons[0]!.trigger('click')

    expect(mockCopy).toHaveBeenCalledWith(STUDY_UUID)
    expect(props.notifyCb).toHaveBeenCalledWith(
      'SODAR UUID' + COPY_MSG_SUFFIX, VARIANT_INFO)
  })
})
