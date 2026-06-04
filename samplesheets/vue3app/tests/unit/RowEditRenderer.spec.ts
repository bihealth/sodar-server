import { beforeEach, describe, expect, test, vi } from 'vitest'
import { config, flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { createBootstrap } from 'bootstrap-vue-next/plugins/createBootstrap'
import { type GridApi } from 'ag-grid-community'

import RowEditRenderer from '@/components/renderers/RowEditRenderer.vue'
import { useEditStore } from '@/stores/editStore.ts'
import { useTableStore } from '@/stores/tableStore.ts'
import { deleteRow } from '@/utils/editUtils.ts'
import { type RowEditRendererParams, type StudyEditContext } from '@/types.ts'
import {
  AJAX_RES_OK,
  ROW_DEL_MSG_ALL,
  ROW_DEL_MSG_ASSAY,
  ROW_DEL_MSG_CANCEL,
  ROW_DEL_MSG_OK,
  ROW_DEL_MSG_UNSAVED,
} from '@/constants.ts'

import studyTablesEdit from '../data/studyTablesEdit.json'
import { copy } from '../testUtils.ts'
import {
  ASSAY_UUID,
  STUDY_UUID,
  TMP_UUID,
  TMP_UUID2,
  TMP_UUID3
} from '../testConstants.ts'

// Data
const nodeId = '0'
const otherNodeId = '170'
const sourceColId = 'col1'
const sourceUuid = TMP_UUID
const sampleColId = 'col7'
const sampleUuid = TMP_UUID2

const defaultParams = {
  assayMode: false,
  node: {
    data: {
      [sourceColId]: { value: '0814', uuid: sourceUuid },
      [sampleColId]: { value: '0814-N1', uuid: sampleUuid }
    },
    id: nodeId
  },
  tableUuid: STUDY_UUID
}
let params: RowEditRendererParams
let rowCount: number

// Selectors
const deleteBtnSel = '.sodar-ss-row-delete-btn'
const saveBtnSel = '.sodar-ss-row-save-btn'

// Global config
config.global.plugins = [createBootstrap()]

vi.mock('@/utils/editUtils.ts', async () => {
  const actual = await vi.importActual('@/utils/editUtils.ts')
  return { ...actual, deleteRow: vi.fn() }
})

describe('RowEditRenderer.vue', () => {
  function getMockGridApi (nodes?: Array<object>): GridApi {
    let forEachNode
    if (nodes === undefined) nodes = [params.node]
    if (nodes) {
      forEachNode = vi.fn((callback) => {
        nodes.forEach(node => callback(node))
      })
    } else forEachNode = vi.fn()
    return {
      forEachNode: forEachNode,
      getColumns: () => {
        return [
          { getColId: () => { return sourceColId } },
          { getColId: () => { return sampleColId } },
        ]
      },
      getDisplayedRowCount: () => { return rowCount }
    } as unknown as GridApi
  }

  function setAssayMode () {
    params.assayMode = true
    params.tableUuid = ASSAY_UUID
  }

  function setUnsavedRow (id: string, tableUuid: string) {
    const editStore = useEditStore()
    editStore.unsavedRow = { id: id, tableUuid: tableUuid }
  }

  function mountComponent (): VueWrapper {
    return mount(RowEditRenderer, { props: { params: params } })
  }

  beforeEach(() => {
    vi.resetAllMocks()
    setActivePinia(createPinia())

    const editStore = useEditStore()
    editStore.unsavedRow = null
    editStore.updatingRow = false
    editStore.editContext = copy(
      studyTablesEdit.edit_context) as StudyEditContext
    editStore.editContext.samples = {
      [sampleUuid]: { name: '0814-N1', assays: [] } }

    const tableStore = useTableStore()
    tableStore.sampleColId = sampleColId

    params = copy(defaultParams) as RowEditRendererParams
    params.api = getMockGridApi()
    rowCount = 2

    const fetchData = { detail: AJAX_RES_OK }
    global.fetch = vi.fn(() => Promise.resolve({
      json: () => Promise.resolve(fetchData), status: 200} as Response)
    )
  })

  test('render component for study with existing row', async () => {
    const wrapper = mountComponent()
    expect(wrapper.find(deleteBtnSel).exists()).toBe(true)
    // Sample not used in assay, button should be enabled
    const delBtn = wrapper.find(deleteBtnSel)
    expect(delBtn.attributes().disabled).not.toBeDefined()
    expect(delBtn.attributes().title).toBe(ROW_DEL_MSG_OK)
    // Existing row = save button should be hidden
    expect(wrapper.find(saveBtnSel).exists()).toBe(false)
  })

  test('render delete button with sample used in assay', async () => {
    const editStore = useEditStore()
    editStore.editContext!.samples[sampleUuid]!.assays = [ASSAY_UUID]
    const wrapper = mountComponent()
    const delBtn = wrapper.find(deleteBtnSel)
    expect(delBtn.attributes().disabled).toBeDefined() // Should be disabled
    expect(delBtn.attributes().title).toBe(ROW_DEL_MSG_ASSAY)
  })

  test('render delete button with another sample used in assay', async () => {
    const editStore = useEditStore()
    editStore.editContext!.samples = {
      [sampleUuid]: { name: '0814-N1', assays: [] },
      [TMP_UUID3]: { name: '0815-N1', assays: [ASSAY_UUID] } }
    const wrapper = mountComponent()
    const delBtn = wrapper.find(deleteBtnSel)
    expect(delBtn.attributes().disabled).not.toBeDefined() // Should be enabled
    expect(delBtn.attributes().title).toBe(ROW_DEL_MSG_OK)
  })

  test('render delete button with row count under 2', async () => {
    // NOTE: This is because we don't currently support empty tables
    rowCount = 1
    const wrapper = mountComponent()
    const delBtn = wrapper.find(deleteBtnSel)
    expect(delBtn.attributes().disabled).toBeDefined()
    expect(delBtn.attributes().title).toBe(ROW_DEL_MSG_ALL)
  })

  test('render delete button with another unsaved row', async () => {
    setUnsavedRow(otherNodeId, STUDY_UUID)
    const wrapper = mountComponent()
    const delBtn = wrapper.find(deleteBtnSel)
    expect(delBtn.attributes().disabled).toBeDefined()
    expect(delBtn.attributes().title).toBe(ROW_DEL_MSG_UNSAVED)
  })

  test('render delete button with row update', async () => {
    const editStore = useEditStore()
    editStore.updatingRow = true
    const wrapper = mountComponent()
    const delBtn = wrapper.find(deleteBtnSel)
    expect(delBtn.attributes().disabled).toBeDefined()
    expect(delBtn.attributes().title).toBe(ROW_DEL_MSG_UNSAVED)
  })

  test('render component for study with new row', async () => {
    setUnsavedRow(nodeId, STUDY_UUID)
    const wrapper = mountComponent()
    // Both buttons should be available and enabled
    const delBtn = wrapper.find(deleteBtnSel)
    expect(delBtn.attributes().disabled).not.toBeDefined()
    expect(delBtn.attributes().title).toBe(ROW_DEL_MSG_CANCEL)
    expect(wrapper.find(saveBtnSel).attributes().disabled).not.toBeDefined()
  })

  test('render save button for new row with newInit set', async () => {
    setUnsavedRow(nodeId, STUDY_UUID)
    params.node.data[sampleColId].newInit = true
    const wrapper = mountComponent()
    // Save button should be disabled
    expect(wrapper.find(saveBtnSel).attributes().disabled).toBeDefined()
  })

  test('render component for assay with existing row', async () => {
    setAssayMode()
    const wrapper = mountComponent()
    const delBtn = wrapper.find(deleteBtnSel)
    expect(delBtn.attributes().disabled).not.toBeDefined()
    expect(delBtn.attributes().title).toBe(ROW_DEL_MSG_OK)
    expect(wrapper.find(saveBtnSel).exists()).toBe(false)
  })

  test('render delete button for assay with sample used', async () => {
    const editStore = useEditStore()
    editStore.editContext!.samples[sampleUuid]!.assays = [ASSAY_UUID]
    setAssayMode()
    const wrapper = mountComponent()
    const delBtn = wrapper.find(deleteBtnSel)
    expect(delBtn.attributes().disabled).not.toBeDefined() // Should be enabled
    expect(delBtn.attributes().title).toBe(ROW_DEL_MSG_OK)
  })

  test('delete study row', async () => {
    vi.stubGlobal('confirm', () => { return true })
    const wrapper = mountComponent()
    expect(deleteRow).not.toHaveBeenCalled()

    await wrapper.find(deleteBtnSel).trigger('click')
    await flushPromises()

    const p = {
      assayMode: false,
      rowNode: params.node,
      tableUuid: STUDY_UUID,
    }
    expect(deleteRow).toHaveBeenCalledWith(expect.objectContaining(p))
  })

  test('delete assay row', async () => {
    vi.stubGlobal('confirm', () => { return true })
    setAssayMode()
    const wrapper = mountComponent()

    await wrapper.find(deleteBtnSel).trigger('click')
    await flushPromises()

    const p = {
      assayMode: true,
      rowNode: params.node,
      tableUuid: ASSAY_UUID,
    }
    expect(deleteRow).toHaveBeenCalledWith(expect.objectContaining(p))
  })

  test('cancel row delete', async () => {
    vi.stubGlobal('confirm', () => { return false }) // Not confirmed
    const wrapper = mountComponent()
    await wrapper.find(deleteBtnSel).trigger('click')
    await flushPromises()
    expect(deleteRow).not.toHaveBeenCalled()
  })

  // TODO: Test insertion
})
