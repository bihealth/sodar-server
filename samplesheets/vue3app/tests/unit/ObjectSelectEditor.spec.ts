import { beforeEach, describe, expect, test, vi } from 'vitest'
import { mount, type VueWrapper } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { type GridApi } from 'ag-grid-community'

import ObjectSelectEditor from '@/components/editors/ObjectSelectEditor.vue'
import { useAppStore } from '@/stores/appStore.ts'
import { useEditStore } from '@/stores/editStore.ts'
import { useTableStore } from '@/stores/tableStore.ts'
import { updateNode } from '@/utils/editUtils.ts'
import {
  type GridCellEditorParams,
  type SheetTableFieldHeader,
  type StudyEditConfigNodeField,
  type StudyEditContextProtocol,
  type StudyEditContextSample,
} from '@/types.ts'
import {
  DB_OBJ_CLASS_MATERIAL,
  DB_OBJ_CLASS_PROCESS,
  EDIT_COL_TYPE_NAME,
  EDIT_COL_TYPE_PROTOCOL,
  EDIT_FORMAT_PROTOCOL,
  EDIT_FORMAT_STRING,
  EDIT_HEADER_TYPE_NAME,
  EDIT_HEADER_TYPE_PROTOCOL,
  EDIT_ITEM_TYPE_SAMPLE,
} from '@/constants.ts'

import { copy, waitSelector } from '../testUtils.ts'
import {
  ASSAY_UUID,
  PROJECT_UUID,
  STUDY_UUID,
  TMP_UUID,
  TMP_UUID2,
  TMP_UUID3
} from '../testConstants.ts'

const mockGridApi = {
  forEachNode: vi.fn(),
  refreshCells: vi.fn()
}

// Sample params
const sampleEditConfig = {
  default: '-N1',
  editable: true,
  format: EDIT_FORMAT_STRING,
  name: 'Name',
  regex: '',
  type: EDIT_HEADER_TYPE_NAME
}
const sampleFieldHeader = {
  col_type: EDIT_COL_TYPE_NAME,
  item_type: EDIT_ITEM_TYPE_SAMPLE,
  max_value_len: 16,
  name: 'Name',
  obj_cls: DB_OBJ_CLASS_MATERIAL,
  type: EDIT_HEADER_TYPE_NAME,
  value: 'Name'
}
// NOTE: Sample selection only happens for new init
const sampleValue = {
  editable: true,
  newInit: true,
  newRow: true,
  uuid: '',
  value: ''
}
// Protocol/default params
const defaultParams = {
  api: {},
  assayMode: false,
  colAlign: 'left',
  colWidth: 125,
  column: {},
  editConfigField: {
    default: TMP_UUID,
    editable: true,
    format: EDIT_FORMAT_PROTOCOL,
    name: 'Protocol',
    type: EDIT_HEADER_TYPE_PROTOCOL
  },
  fieldHeader: {
    col_type: EDIT_COL_TYPE_PROTOCOL,
    item_type: null,
    max_value_len: 16,
    name: 'Protocol',
    obj_cls: DB_OBJ_CLASS_PROCESS,
    type: EDIT_HEADER_TYPE_PROTOCOL,
    value: 'Protocol'
  },
  fieldId: 'col3',
  node: {},
  sampleColId: 'col7',
  tableUuid: STUDY_UUID,
  value: {
    uuid: TMP_UUID3,
    uuid_ref: TMP_UUID,
    value: 'sample collection'
  },
}
let params: GridCellEditorParams

const protocols: Array<StudyEditContextProtocol> = [
  { name: 'sample collection', uuid: TMP_UUID },
  { name: 'library preparation', uuid: TMP_UUID2 }
]
const samples: { [key: string]: StudyEditContextSample } = {
  [TMP_UUID]: { assays: [], name: '0814-N1' },
  [TMP_UUID2]: { assays: [], name: '0815-N1' }
}
const cellUpdateUrl: string = '/samplesheets/ajax/edit/cell/' + PROJECT_UUID

// Global config and mocks
vi.mock('@/utils/editUtils.ts', async () => {
  const actual = await vi.importActual('@/utils/editUtils.ts')
  return { ...actual, updateNode: vi.fn() }
})

describe('ObjectSelectEditor.vue', () => {
  function setSampleParams () {
    params.assayMode = true
    params.editConfigField = copy(sampleEditConfig) as StudyEditConfigNodeField
    params.fieldHeader = copy(sampleFieldHeader) as SheetTableFieldHeader
    params.tableUuid = ASSAY_UUID
    params.value = copy(sampleValue)
  }

  beforeEach(() => {
    // Set up mocks
    vi.clearAllMocks()
    global.fetch = vi.fn(() => Promise.resolve({
      json: () => Promise.resolve({ detail: 'ok' }), status: 200} as Response)
    )

    // Set up stores
    setActivePinia(createPinia())
    const appStore = useAppStore()
    // NOTE: appStore and tableStore are needed by editUtils
    appStore.projectUuid = PROJECT_UUID
    const tableStore = useTableStore()
    tableStore.gridApi.study = mockGridApi as unknown as GridApi
    tableStore.gridApi.assays[ASSAY_UUID] = mockGridApi as unknown as GridApi
    const editStore = useEditStore()
    editStore.editContext = {
      protocols: copy(protocols) as Array<StudyEditContextProtocol>,
      samples: copy(samples) as { [key: string]: StudyEditContextSample },
      sodar_ontologies: {}
    }

    // Set up params
    params = copy(defaultParams) as GridCellEditorParams
  })

  async function mountComponent (): Promise<VueWrapper> {
    const wrapper = mount(ObjectSelectEditor, { props: { params: params } })
    await waitSelector(wrapper, '.sodar-ss-data-object-select', 1)
    return wrapper
  }

  test('render component for protocol', async () => {
    const wrapper = await mountComponent()
    expect(wrapper.find('.sodar-ss-data-object-select').exists()).toBe(true)
    const options = wrapper.findAll('.sodar-ss-data-object-option')
    expect(options.length).toBe(2)
    expect(options[0]?.text()).toBe(protocols[0]?.name)
    expect(options[0]?.attributes().value).toBe(protocols[0]?.uuid)
    expect(options[1]?.text()).toBe(protocols[1]?.name)
    expect(options[1]?.attributes().value).toBe(protocols[1]?.uuid)
  })

  test('unmount component without changes', async () => {
    const wrapper = await mountComponent()
    expect(fetch).not.toHaveBeenCalled()
    wrapper.unmount()
    // Neither fetch() nor updateNode() should have been called
    expect(fetch).not.toHaveBeenCalled()
    expect(updateNode).not.toHaveBeenCalled()
  })

  test('update protocol with changes', async () => {
    const wrapper = await mountComponent()
    expect(fetch).not.toHaveBeenCalled()
    await wrapper.find('.ag-cell-edit-input').setValue(TMP_UUID2)
    wrapper.unmount()
    const reqBody = {
      updated_cells: [{
        header_name: 'Protocol',
        header_type: 'protocol',
        obj_cls: DB_OBJ_CLASS_PROCESS,
        uuid: TMP_UUID3,
        value: protocols[1]?.name,
        uuid_ref: protocols[1]?.uuid,
      }],
      verify: true
    }
    expect(fetch).toHaveBeenCalledWith(
      cellUpdateUrl,
      expect.objectContaining({ body: JSON.stringify(reqBody) }))
  })

  test('update protocol with new row and changes', async () => {
    params.value.newInit = true
    params.value.newRow = true
    const wrapper = await mountComponent()
    expect(fetch).not.toHaveBeenCalled()
    await wrapper.find('.ag-cell-edit-input').setValue(TMP_UUID2)
    wrapper.unmount()
    expect(fetch).not.toHaveBeenCalled() // No fetch, new row
    const nodeUpdateParams = {
      api: {},
      assayMode: false,
      column: {},
      createNew: true, // Protocol = should be creating
      nameCellData: null, // Protocol = no nameCellData
      rowNode: {},
      tableUuid: STUDY_UUID
    }
    expect(updateNode).toHaveBeenCalledWith(nodeUpdateParams)
  })

  test('render component for sample', async () => {
    setSampleParams()
    const wrapper = await mountComponent()
    expect(wrapper.find('.sodar-ss-data-object-select').exists()).toBe(true)
    const options = wrapper.findAll('.sodar-ss-data-object-option')
    expect(options.length).toBe(2)
    expect(options[0]?.text()).toBe(samples[TMP_UUID]?.name)
    expect(options[0]?.attributes().value).toBe(TMP_UUID)
    expect(options[1]?.text()).toBe(samples[TMP_UUID2]?.name)
    expect(options[1]?.attributes().value).toBe(TMP_UUID2)
  })

  test('unmount component for sample without changes', async () => {
    setSampleParams()
    const wrapper = await mountComponent()
    wrapper.unmount()
    expect(fetch).not.toHaveBeenCalled()
    expect(updateNode).not.toHaveBeenCalled()
  })

  test('update sample with changes', async () => {
    setSampleParams()
    const wrapper = await mountComponent()
    await wrapper.find('.ag-cell-edit-input').setValue(TMP_UUID)
    wrapper.unmount()
    expect(fetch).not.toHaveBeenCalled() // No fetch, new row
    const nodeUpdateParams = {
      api: {},
      assayMode: true,
      column: {},
      createNew: false,
      nameCellData: {
        editable: true,
        newInit: false,
        newRow: true,
        uuid: '',
        value: ''
      },
      rowNode: {},
      tableUuid: ASSAY_UUID
    }
    expect(updateNode).toHaveBeenCalledWith(nodeUpdateParams)
  })
})
