import { beforeEach, describe, expect, test, vi } from 'vitest'
import { mount, type VueWrapper } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { type GridApi } from 'ag-grid-community'

import ObjectSelectEditor from '@/components/editors/ObjectSelectEditor.vue'
import { useAppStore } from '@/stores/appStore.ts'
import { useEditStore } from '@/stores/editStore.ts'
import { useTableStore } from '@/stores/tableStore.ts'
import {
  type GridCellEditorParams,
  type StudyEditContextProtocol,
} from '@/types.ts'

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

// Protocol params
const defaultParams = {
  assayMode: false,
  colAlign: 'left',
  colWidth: 125,
  editConfigField: {
    name: 'Protocol',
    type: 'protocol',
    format: 'protocol',
    default: TMP_UUID
  },
  fieldHeader: {
    value: 'Protocol',
    name: 'Protocol',
    obj_cls: 'Process',
    item_type: null,
    col_type: 'PROTOCOL',
    type: 'protocol',
    max_value_len: 16
  },
  fieldId: 'col3',
  sampleColId: 'col7',
  tableUuid: STUDY_UUID,
  value: {
    value: 'sample collection',
    uuid: TMP_UUID3,
    uuid_ref: TMP_UUID
  },
}
let params: GridCellEditorParams

const protocols: Array<StudyEditContextProtocol> = [
  { name: 'sample collection', uuid: TMP_UUID },
  { name: 'library preparation', uuid: TMP_UUID2 }
]
const cellUpdateUrl: string = '/samplesheets/ajax/edit/cell/' + PROJECT_UUID

describe('ObjectSelectEditor.vue', () => {
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
      protocols: protocols, samples: {}, sodar_ontologies: {}
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

  test('unmount component with no changes', async () => {
    const wrapper = await mountComponent()
    expect(fetch).not.toHaveBeenCalled()
    wrapper.unmount()
    expect(fetch).not.toHaveBeenCalled() // Should not have been called
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
        obj_cls: 'Process',
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

  // TODO: Test sample selecting once row editing is implemented
})
