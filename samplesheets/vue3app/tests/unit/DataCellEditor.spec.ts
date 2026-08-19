import { beforeEach, describe, expect, test, vi } from 'vitest'
import { mount, type VueWrapper } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { type GridApi } from 'ag-grid-community'

import DataCellEditor from '@/components/editors/DataCellEditor.vue'
import { useAppStore } from '@/stores/appStore.ts'
import { useEditStore } from '@/stores/editStore.ts'
import { useTableStore } from '@/stores/tableStore.ts'
import { updateNode } from '@/utils/editUtils.ts'
import {
  type GridCellEditorParams,
  type SheetTableCellData,
  type SheetTableFieldHeader,
  type StudyEditConfigNodeField,
  type StudyEditContext,
} from '@/types.ts'
import {
  CELL_NODE_NAME_NEW,
  CELL_NODE_NAME_RENAME,
  DB_OBJ_CLASS_MATERIAL,
  EDIT_FORMAT_DATE,
  EDIT_FORMAT_DOUBLE,
  EDIT_FORMAT_EXT,
  EDIT_FORMAT_INTEGER,
  EDIT_FORMAT_SELECT,
  EDIT_HEADER_TYPE_CHAR,
  EDIT_HEADER_TYPE_NAME,
  EDIT_ITEM_TYPE_DATA
} from '@/constants.ts'

import studyTablesEdit from '../data/studyTablesEdit.json'
import { copy, waitSelector } from '../testUtils.ts'
import {
  ASSAY_UUID,
  PROJECT_UUID,
  STUDY_UUID,
  TMP_UUID,
  TMP_UUID2
} from '../testConstants.ts'

// Test Data -------------------------------------------------------------------

const sampleColId = 'col7'
const sampleUuid = TMP_UUID2

// Set default params data as name field
const defaultParams = {
  assayMode: false,
  colAlign: 'left',
  colWidth: 125,
  editConfigField: {
    name: 'Name',
    type: EDIT_HEADER_TYPE_NAME
  },
  fieldHeader: copy(
    studyTablesEdit.tables.study.field_header[0] as SheetTableFieldHeader) as
    SheetTableFieldHeader,
  fieldId: 'col0',
  sampleColId: sampleColId,
  tableUuid: STUDY_UUID,
  value: {
    value: '0814',
    uuid: TMP_UUID
  },
}
let params: GridCellEditorParams

const emptyData: SheetTableCellData = {
  editable: true,
  newInit: true,
  newRow: true,
  uuid: '',
  value: ''
}

// Default edit configuration for select field
const selectEditField: StudyEditConfigNodeField = {
  default: '',
  name: 'Name',
  format: EDIT_FORMAT_SELECT,
  options: ['0814', '0815'],
  type: EDIT_HEADER_TYPE_CHAR,
}

// Default edit configuration for unit field
const unitEditField: StudyEditConfigNodeField = {
  default: '',
  name: 'Name',
  format: EDIT_FORMAT_INTEGER,
  unit: ['day', 'year'],
  unit_default: 'day',
  type: EDIT_HEADER_TYPE_CHAR,
}

const mockGridApi = {
  forEachNode: vi.fn(),
  getColumn: () => { return null }, // TODO: Mock for real
  refreshCells: vi.fn()
}

const cellUpdateUrl: string = '/samplesheets/ajax/edit/cell/' + PROJECT_UUID
const exLinksInput: string = 'x-generic-remote:123;x-sodar-example-link:456'
// NOTE: Purposefully defined as a string, will be converted to RegExp
const letterOnlyRegex: string = '^[a-z]+$'

// Selectors
const cellRootSel = '.sodar-ss-editor-cell'
const inputSel = '.sodar-ss-edit-input'
const selectSel = '.sodar-ss-edit-select'
const unitSel = '.sodar-ss-edit-unit'

// Global Setup ----------------------------------------------------------------

vi.mock('@/utils/editUtils.ts', async () => {
  const actual = await vi.importActual('@/utils/editUtils.ts')
  return { ...actual, updateNode: vi.fn() }
})

// Tests -----------------------------------------------------------------------

describe('DataCellEditor.vue', () => {
  async function mountComponent (): Promise<VueWrapper> {
    const wrapper = mount(DataCellEditor, { props: { params: params } })
    await waitSelector(wrapper, '.sodar-ss-editor-cell', 1)
    return wrapper
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
    appStore.selectEnabled = true
    appStore.projectUuid = PROJECT_UUID
    const editStore = useEditStore()
    editStore.editContext = copy(
      studyTablesEdit.edit_context) as StudyEditContext
    editStore.editContext.samples = {
      [sampleUuid]: { name: '0814-N1', assays: [] } }
    const tableStore = useTableStore()
    // Mock tableStore GridApi:s
    tableStore.gridApi.study = mockGridApi as unknown as GridApi
    tableStore.gridApi.assays[ASSAY_UUID] = mockGridApi as unknown as GridApi

    // Set up params
    params = copy(defaultParams) as GridCellEditorParams
  })

  test('render component with text input and default value', async () => {
    const appStore = useAppStore()
    expect(appStore.selectEnabled).toBe(true)

    const wrapper = await mountComponent()
    // Name cell for an existing node
    expect(wrapper.find(
      cellRootSel).attributes().title).toBe(CELL_NODE_NAME_RENAME)
    expect(wrapper.find(selectSel).exists()).toBe(false)
    expect(wrapper.find(unitSel).exists()).toBe(false)
    const input = wrapper.find(inputSel)
    expect(input.exists()).toBe(true) // NOTE: Can't assert value here
    expect(appStore.selectEnabled).toBe(false) // Should be disabled
  })

  test('return text value with getValue()', async () => {
    const wrapper = await mountComponent() as VueWrapper<typeof DataCellEditor>
    const res = wrapper.vm.getValue()
    expect(res.value).toBe('0814')
    expect(res.uuid).toBe(TMP_UUID)
  })

  test('update text value', async () => {
    const wrapper = await mountComponent() as VueWrapper<typeof DataCellEditor>
    await wrapper.find(inputSel).setValue('0815')
    const res = wrapper.vm.getValue()
    expect(res.value).toBe('0815')
    expect(res.uuid).toBe(TMP_UUID) // Assert UUID is still present
    expect(params.value?.value).toBe('0815')
  })

  test('trim updated text value', async () => {
    const wrapper = await mountComponent() as VueWrapper<typeof DataCellEditor>
    await wrapper.find(inputSel).setValue('  0815  ')
    const res = wrapper.vm.getValue()
    expect(res.value).toBe('0815')
  })

  test('return list value', async () => {
    params.value!.value = ['x', 'y']
    const wrapper = await mountComponent() as VueWrapper<typeof DataCellEditor>
    const res = wrapper.vm.getValue()
    expect(res.value).toEqual(['x', 'y'])
  })

  test('trim list value', async () => {
    params.value!.value = ['x  ', '  y']
    const wrapper = await mountComponent() as VueWrapper<typeof DataCellEditor>
    const res = wrapper.vm.getValue()
    expect(res.value).toEqual(['x', 'y'])
  })

  test('update list value', async () => {
    params.value!.value = ['x', 'y']
    const wrapper = await mountComponent() as VueWrapper<typeof DataCellEditor>
    await wrapper.find(inputSel).setValue('a;b;c')
    const res = wrapper.vm.getValue()
    expect(res.value).toEqual(['a', 'b', 'c'])
  })

  test('update and trim list value', async () => {
    params.value!.value = ['x', 'y']
    const wrapper = await mountComponent() as VueWrapper<typeof DataCellEditor>
    await wrapper.find(inputSel).setValue('a ;  b ; c  ')
    const res = wrapper.vm.getValue()
    expect(res.value).toEqual(['a', 'b', 'c'])
  })

  test('update list value with extra separator', async () => {
    params.value!.value = ['x', 'y']
    const wrapper = await mountComponent() as VueWrapper<typeof DataCellEditor>
    // Extra trailing separator
    await wrapper.find(inputSel).setValue('a;b;c;')
    const res = wrapper.vm.getValue()
    expect(res.value).toEqual(['a', 'b', 'c']) // No empty item
  })

  test('render empty value', async () => {
    params.value!.value = ''
    const wrapper = await mountComponent() as VueWrapper<typeof DataCellEditor>
    const res = wrapper.vm.getValue()
    expect(res.value).toBe('')
  })

  test('render non-name field', async () => {
    params.fieldHeader.type = EDIT_HEADER_TYPE_CHAR
    const wrapper = await mountComponent()
    // No title should be set
    expect(wrapper.find(cellRootSel).attributes().title).toBe('')
  })

  test('update input into empty value', async () => {
    const wrapper = await mountComponent() as VueWrapper<typeof DataCellEditor>
    await wrapper.find(inputSel).setValue('')
    const res = wrapper.vm.getValue()
    expect(res.value).toBe('')
  })

  test('render component with value select enabled', async () => {
    params.editConfigField = copy(selectEditField) as StudyEditConfigNodeField
    const wrapper = await mountComponent()
    expect(wrapper.find(inputSel).exists()).toBe(false)
    expect(wrapper.find(unitSel).exists()).toBe(false)
    const select = wrapper.find(selectSel)
    expect(select.exists()).toBe(true)
    expect(select.findAll('.sodar-ss-edit-select-option').length).toBe(3)
    expect(select.findAll('.sodar-ss-edit-select-option-empty').length).toBe(1)
  })

  test('return select value', async () => {
    params.editConfigField = copy(selectEditField) as StudyEditConfigNodeField
    const wrapper = await mountComponent() as VueWrapper<typeof DataCellEditor>
    const res = wrapper.vm.getValue()
    expect(res.value).toBe('0814')
    expect(res.uuid).toBe(TMP_UUID)
  })

  test('update select value', async () => {
    params.editConfigField = copy(selectEditField) as StudyEditConfigNodeField
    const wrapper = await mountComponent() as VueWrapper<typeof DataCellEditor>
    await wrapper.find(selectSel).setValue('0815')
    const res = wrapper.vm.getValue()
    expect(res.value).toBe('0815')
    expect(res.uuid).toBe(TMP_UUID) // Assert UUID is unaffected
  })

  test('update select value to empty value', async () => {
    params.editConfigField = copy(selectEditField) as StudyEditConfigNodeField
    const wrapper = await mountComponent() as VueWrapper<typeof DataCellEditor>
    await wrapper.find(selectSel).setValue('')
    const res = wrapper.vm.getValue()
    expect(res.value).toBe('')
    expect(res.uuid).toBe(TMP_UUID)
  })

  test('render value with unit', async () => {
    params.value!.unit = 'day'
    params.editConfigField = copy(unitEditField) as StudyEditConfigNodeField
    const wrapper = await mountComponent()
    expect(wrapper.find(selectSel).exists()).toBe(false)
    expect(wrapper.find(inputSel).exists()).toBe(true)
    expect(wrapper.find(unitSel).exists()).toBe(true)
    const options = wrapper.findAll('.sodar-ss-edit-unit-option')
    expect(options.length).toBe(3)
    expect(options[0]?.text()).toBe('-')
    expect(options[1]?.text()).toBe('day')
    expect(options[2]?.text()).toBe('year')
  })

  test('return unit with getValue()', async () => {
    params.value!.unit = 'day'
    params.editConfigField = copy(unitEditField) as StudyEditConfigNodeField
    const wrapper = await mountComponent() as VueWrapper<typeof DataCellEditor>
    const res = wrapper.vm.getValue()
    expect(res.unit).toBe('day')
  })

  test('update unit', async () => {
    params.value!.unit = 'day'
    params.editConfigField = copy(unitEditField) as StudyEditConfigNodeField
    const wrapper = await mountComponent() as VueWrapper<typeof DataCellEditor>
    await wrapper.find(unitSel).setValue('year')
    const res = wrapper.vm.getValue()
    expect(res.unit).toBe('year')
  })

  test('unmount with updated value', async () => {
    const appStore = useAppStore()
    expect(appStore.selectEnabled).toBe(true)
    expect(fetch).not.toHaveBeenCalled()
    const wrapper = await mountComponent()
    expect(appStore.selectEnabled).toBe(false)

    await wrapper.find(inputSel).setValue('0815')
    wrapper.unmount()

    const reqBody = {
      updated_cells: [{
        header_name: 'Name',
        header_type: EDIT_HEADER_TYPE_NAME,
        obj_cls: DB_OBJ_CLASS_MATERIAL,
        uuid: TMP_UUID,
        value: '0815',
        item_type: 'SOURCE'
      }],
      verify: true
    }
    expect(fetch).toHaveBeenCalledWith(
      cellUpdateUrl,
      expect.objectContaining({ body: JSON.stringify(reqBody)}))
    expect(appStore.selectEnabled).toBe(true) // Should be re-enabled
  })

  test('unmount with updated sample name', async () => {
    const editStore = useEditStore()
    params.fieldHeader = copy(
      studyTablesEdit.tables.study.field_header[7] as SheetTableFieldHeader) as
      SheetTableFieldHeader
    params.fieldId = sampleColId
    params.value!.uuid = sampleUuid
    params.value!.value = '0814-N1'
    expect(editStore.editContext!.samples[sampleUuid]!.name).toBe('0814-N1')

    const wrapper = await mountComponent()
    await wrapper.find(inputSel).setValue('0814-N1-up')
    wrapper.unmount()

    const reqBody = {
      updated_cells: [{
        header_name: 'Name',
        header_type: EDIT_HEADER_TYPE_NAME,
        obj_cls: DB_OBJ_CLASS_MATERIAL,
        uuid: sampleUuid,
        value: '0814-N1-up',
        item_type: 'SAMPLE'
      }],
      verify: true
    }
    expect(fetch).toHaveBeenCalledWith(
      cellUpdateUrl,
      expect.objectContaining({ body: JSON.stringify(reqBody)}))
    // Sample name should also be updated in editContext
    expect(editStore.editContext!.samples[sampleUuid]!.name).toBe('0814-N1-up')
  })

  test('unmount with unchanged value', async () => {
    const appStore = useAppStore()
    expect(appStore.selectEnabled).toBe(true)
    expect(fetch).not.toHaveBeenCalled()

    const wrapper = await mountComponent()
    expect(appStore.selectEnabled).toBe(false)
    wrapper.unmount()
    expect(fetch).not.toHaveBeenCalled()
    expect(appStore.selectEnabled).toBe(true) // Should be re-enabled
  })

  test('unmount with updated unit', async () => {
    params.value!.unit = 'day'
    params.editConfigField = copy(unitEditField) as StudyEditConfigNodeField
    expect(fetch).not.toHaveBeenCalled()

    const wrapper = await mountComponent()
    await wrapper.find(unitSel).setValue('year')
    wrapper.unmount()

    const reqBody = {
      updated_cells: [{
        header_name: 'Name',
        header_type: EDIT_HEADER_TYPE_NAME,
        obj_cls: DB_OBJ_CLASS_MATERIAL,
        uuid: TMP_UUID,
        value: '0814',
        item_type: 'SOURCE',
        unit: 'year', // This should be changed
      }],
      verify: true
    }
    expect(fetch).toHaveBeenCalledWith(
      cellUpdateUrl,
      expect.objectContaining({ body: JSON.stringify(reqBody)}))
  })

  test('unmount with unchanged unit', async () => {
    params.value!.unit = 'day'
    params.editConfigField = copy(unitEditField) as StudyEditConfigNodeField
    expect(fetch).not.toHaveBeenCalled()
    const wrapper = await mountComponent()
    wrapper.unmount()
    expect(fetch).not.toHaveBeenCalled()
  })

  test('render invalid value', async () => {
    const wrapper = await mountComponent()
    const input = wrapper.find(inputSel)
    expect(input.classes()).not.toContain('text-danger')
    await wrapper.find(inputSel).setValue('0815+') // Invalid char
    expect(input.classes()).toContain('text-danger')
  })

  test('validate invalid name', async () => {
    const wrapper = await mountComponent()
    await wrapper.find(inputSel).setValue('0815+')
    wrapper.unmount()
    expect(fetch).not.toHaveBeenCalled() // No Ajax call to update value
    expect(params.value?.value).toBe('0814') // No change to value
  })

  test('validate empty name', async () => {
    const wrapper = await mountComponent()
    await wrapper.find(inputSel).setValue('')
    wrapper.unmount()
    expect(fetch).not.toHaveBeenCalled()
    expect(params.value?.value).toBe('0814')
  })

  test('validate data name', async () => {
    params.fieldHeader.item_type = EDIT_ITEM_TYPE_DATA
    const wrapper = await mountComponent()
    // Dot is approved here
    await wrapper.find(inputSel).setValue('0815.txt')
    wrapper.unmount()
    expect(fetch).toHaveBeenCalled()
    expect(params.value?.value).toBe('0815.txt')
  })

  test('validate invalid data name', async () => {
    params.fieldHeader.item_type = EDIT_ITEM_TYPE_DATA
    const wrapper = await mountComponent()
    await wrapper.find(inputSel).setValue('0815+')
    wrapper.unmount()
    expect(fetch).not.toHaveBeenCalled()
    expect(params.value?.value).toBe('0814')
  })

  test('validate empty data name value', async () => {
    params.fieldHeader.item_type = EDIT_ITEM_TYPE_DATA
    const wrapper = await mountComponent()
    // Empty value is approved for DATA
    await wrapper.find(inputSel).setValue('')
    wrapper.unmount()
    expect(fetch).toHaveBeenCalled()
    expect(params.value?.value).toBe('')
  })

  test('validate custom regex with valid value', async () => {
    params.editConfigField.regex = letterOnlyRegex
    const wrapper = await mountComponent()
    await wrapper.find(inputSel).setValue('abc')
    wrapper.unmount()
    expect(fetch).toHaveBeenCalled()
    expect(params.value?.value).toBe('abc')
  })

  test('validate custom regex with invalid value', async () => {
    params.editConfigField.regex = letterOnlyRegex // Does not accept numbers
    const wrapper = await mountComponent()
    await wrapper.find(inputSel).setValue('abc123')
    wrapper.unmount()
    expect(fetch).not.toHaveBeenCalled()
    // Revert to old value, it's ok even if it doesn't match current regex :)
    expect(params.value?.value).toBe('0814')
  })

  test('validate integer', async () => {
    params.editConfigField.format = EDIT_FORMAT_INTEGER
    params.fieldHeader.type = EDIT_HEADER_TYPE_CHAR
    const wrapper = await mountComponent()
    await wrapper.find(inputSel).setValue('815')
    wrapper.unmount()
    expect(fetch).toHaveBeenCalled()
    expect(params.value?.value).toBe('815')
  })

  test('validate invalid integer', async () => {
    params.editConfigField.format = EDIT_FORMAT_INTEGER
    params.fieldHeader.type = EDIT_HEADER_TYPE_CHAR
    const wrapper = await mountComponent()
    await wrapper.find(inputSel).setValue('815abc')
    wrapper.unmount()
    expect(fetch).not.toHaveBeenCalled()
    expect(params.value?.value).toBe('0814')
  })

  test('validate empty integer', async () => {
    params.editConfigField.format = EDIT_FORMAT_INTEGER
    params.fieldHeader.type = EDIT_HEADER_TYPE_CHAR
    const wrapper = await mountComponent()
    await wrapper.find(inputSel).setValue('')
    wrapper.unmount()
    expect(fetch).toHaveBeenCalled() // Empty value is accepted here
    expect(params.value?.value).toBe('')
  })

  test('validate integer with invalid double value', async () => {
    params.editConfigField.format = EDIT_FORMAT_INTEGER
    params.fieldHeader.type = EDIT_HEADER_TYPE_CHAR
    const wrapper = await mountComponent()
    await wrapper.find(inputSel).setValue('8.15')
    wrapper.unmount()
    expect(fetch).not.toHaveBeenCalled()
    expect(params.value?.value).toBe('0814')
  })

  test('validate double', async () => {
    params.editConfigField.format = EDIT_FORMAT_DOUBLE
    params.fieldHeader.type = EDIT_HEADER_TYPE_CHAR
    const wrapper = await mountComponent()
    await wrapper.find(inputSel).setValue('8.15')
    wrapper.unmount()
    expect(fetch).toHaveBeenCalled()
    expect(params.value?.value).toBe('8.15')
  })

  test('validate double with invalid string value', async () => {
    params.editConfigField.format = EDIT_FORMAT_DOUBLE
    params.fieldHeader.type = EDIT_HEADER_TYPE_CHAR
    const wrapper = await mountComponent()
    await wrapper.find(inputSel).setValue('abc')
    wrapper.unmount()
    expect(fetch).not.toHaveBeenCalled()
    expect(params.value?.value).toBe('0814')
  })

  test('validate double with invalid integer value', async () => {
    params.editConfigField.format = EDIT_FORMAT_DOUBLE
    params.fieldHeader.type = EDIT_HEADER_TYPE_CHAR
    const wrapper = await mountComponent()
    await wrapper.find(inputSel).setValue('815')
    wrapper.unmount()
    expect(fetch).not.toHaveBeenCalled()
    expect(params.value?.value).toBe('0814')
  })

  test('validate double with valid negative value', async () => {
    params.editConfigField.format = EDIT_FORMAT_DOUBLE
    params.fieldHeader.type = EDIT_HEADER_TYPE_CHAR
    const wrapper = await mountComponent()
    await wrapper.find(inputSel).setValue('-8.15')
    wrapper.unmount()
    expect(fetch).toHaveBeenCalled()
    expect(params.value?.value).toBe('-8.15')
  })

  test('validate empty double', async () => {
    params.editConfigField.format = EDIT_FORMAT_DOUBLE
    params.fieldHeader.type = EDIT_HEADER_TYPE_CHAR
    const wrapper = await mountComponent()
    await wrapper.find(inputSel).setValue('')
    wrapper.unmount()
    expect(fetch).toHaveBeenCalled() // Empty value is accepted here
    expect(params.value?.value).toBe('')
  })

  test('validate range with integer', async () => {
    params.editConfigField.format = EDIT_FORMAT_INTEGER
    params.editConfigField.range = ['1', '2']
    params.fieldHeader.type = EDIT_HEADER_TYPE_CHAR
    const wrapper = await mountComponent()
    await wrapper.find(inputSel).setValue('2')
    wrapper.unmount()
    expect(fetch).toHaveBeenCalled()
    expect(params.value?.value).toBe('2')
  })

  test('validate range with invalid integer over limit', async () => {
    params.editConfigField.format = EDIT_FORMAT_INTEGER
    params.editConfigField.range = ['1', '2']
    params.fieldHeader.type = EDIT_HEADER_TYPE_CHAR
    const wrapper = await mountComponent()
    await wrapper.find(inputSel).setValue('3')
    wrapper.unmount()
    expect(fetch).not.toHaveBeenCalled()
    expect(params.value?.value).toBe('0814')
  })

  test('validate range with invalid integer under limit', async () => {
    params.editConfigField.format = EDIT_FORMAT_INTEGER
    params.editConfigField.range = ['1', '2']
    params.fieldHeader.type = EDIT_HEADER_TYPE_CHAR
    const wrapper = await mountComponent()
    await wrapper.find(inputSel).setValue('0')
    wrapper.unmount()
    expect(fetch).not.toHaveBeenCalled()
    expect(params.value?.value).toBe('0814')
  })

  test('validate range with empty integer', async () => {
    params.editConfigField.format = EDIT_FORMAT_INTEGER
    params.editConfigField.range = ['1', '2']
    params.fieldHeader.type = EDIT_HEADER_TYPE_CHAR
    const wrapper = await mountComponent()
    await wrapper.find(inputSel).setValue('')
    wrapper.unmount()
    expect(fetch).toHaveBeenCalled() // Empty is allowed with range
    expect(params.value?.value).toBe('')
  })

 test('validate range with double', async () => {
    params.editConfigField.format = EDIT_FORMAT_DOUBLE
    params.editConfigField.range = ['1', '2']
    params.fieldHeader.type = EDIT_HEADER_TYPE_CHAR
    const wrapper = await mountComponent()
    await wrapper.find(inputSel).setValue('1.5')
    wrapper.unmount()
    expect(fetch).toHaveBeenCalled()
    expect(params.value?.value).toBe('1.5')
  })

  test('validate range with invalid double over limit', async () => {
    params.editConfigField.format = EDIT_FORMAT_DOUBLE
    params.editConfigField.range = ['1', '2']
    params.fieldHeader.type = EDIT_HEADER_TYPE_CHAR
    const wrapper = await mountComponent()
    await wrapper.find(inputSel).setValue('2.1')
    wrapper.unmount()
    expect(fetch).not.toHaveBeenCalled()
    expect(params.value?.value).toBe('0814')
  })

  test('validate range with invalid double under limit', async () => {
    params.editConfigField.format = EDIT_FORMAT_DOUBLE
    params.editConfigField.range = ['1', '2']
    params.fieldHeader.type = EDIT_HEADER_TYPE_CHAR
    const wrapper = await mountComponent()
    await wrapper.find(inputSel).setValue('0.9')
    wrapper.unmount()
    expect(fetch).not.toHaveBeenCalled()
    expect(params.value?.value).toBe('0814')
  })

  test('validate range with empty double', async () => {
    params.editConfigField.format = EDIT_FORMAT_DOUBLE
    params.editConfigField.range = ['1', '2']
    params.fieldHeader.type = EDIT_HEADER_TYPE_CHAR
    const wrapper = await mountComponent()
    await wrapper.find(inputSel).setValue('')
    wrapper.unmount()
    expect(fetch).toHaveBeenCalled()
    expect(params.value?.value).toBe('')
  })

  test('validate date', async () => {
    params.editConfigField.format = EDIT_FORMAT_DATE
    params.fieldHeader.type = EDIT_HEADER_TYPE_CHAR
    const wrapper = await mountComponent()
    await wrapper.find(inputSel).setValue('2026-04-13')
    wrapper.unmount()
    expect(fetch).toHaveBeenCalled()
    expect(params.value?.value).toBe('2026-04-13')
  })

  test('validate date with non-date value', async () => {
    params.editConfigField.format = EDIT_FORMAT_DATE
    params.fieldHeader.type = EDIT_HEADER_TYPE_CHAR
    const wrapper = await mountComponent()
    await wrapper.find(inputSel).setValue('abc')
    wrapper.unmount()
    expect(fetch).not.toHaveBeenCalled()
    expect(params.value?.value).toBe('0814')
  })

  test('validate date with invalid month', async () => {
    params.editConfigField.format = EDIT_FORMAT_DATE
    params.fieldHeader.type = EDIT_HEADER_TYPE_CHAR
    const wrapper = await mountComponent()
    await wrapper.find(inputSel).setValue('2026-13-13')
    wrapper.unmount()
    expect(fetch).not.toHaveBeenCalled()
    expect(params.value?.value).toBe('0814')
  })

  test('validate date with zero month', async () => {
    params.editConfigField.format = EDIT_FORMAT_DATE
    params.fieldHeader.type = EDIT_HEADER_TYPE_CHAR
    const wrapper = await mountComponent()
    await wrapper.find(inputSel).setValue('2026-00-13')
    wrapper.unmount()
    expect(fetch).not.toHaveBeenCalled()
    expect(params.value?.value).toBe('0814')
  })

  test('validate date with invalid day', async () => {
    params.editConfigField.format = EDIT_FORMAT_DATE
    params.fieldHeader.type = EDIT_HEADER_TYPE_CHAR
    const wrapper = await mountComponent()
    await wrapper.find(inputSel).setValue('2026-04-31')
    wrapper.unmount()
    expect(fetch).not.toHaveBeenCalled()
    expect(params.value?.value).toBe('0814')
  })

  test('validate date with zero day', async () => {
    params.editConfigField.format = EDIT_FORMAT_DATE
    params.fieldHeader.type = EDIT_HEADER_TYPE_CHAR
    const wrapper = await mountComponent()
    await wrapper.find(inputSel).setValue('2026-04-00')
    wrapper.unmount()
    expect(fetch).not.toHaveBeenCalled()
    expect(params.value?.value).toBe('0814')
  })

  test('validate date with empty date', async () => {
    params.editConfigField.format = EDIT_FORMAT_DATE
    params.fieldHeader.type = EDIT_HEADER_TYPE_CHAR
    const wrapper = await mountComponent()
    await wrapper.find(inputSel).setValue('')
    wrapper.unmount()
    expect(fetch).toHaveBeenCalled()
    expect(params.value?.value).toBe('')
  })

  test('validate external links', async () => {
    params.editConfigField.format = EDIT_FORMAT_EXT
    params.fieldHeader.type = EDIT_HEADER_TYPE_CHAR
    const wrapper = await mountComponent()
    await wrapper.find(inputSel).setValue(exLinksInput)
    wrapper.unmount()
    expect(fetch).toHaveBeenCalled()
    expect(params.value?.value).toEqual(exLinksInput.split(';'))
  })

  test('validate external links with invalid string', async () => {
    params.editConfigField.format = EDIT_FORMAT_EXT
    params.fieldHeader.type = EDIT_HEADER_TYPE_CHAR
    const wrapper = await mountComponent()
    await wrapper.find(inputSel).setValue(exLinksInput + ';;')
    wrapper.unmount()
    expect(fetch).not.toHaveBeenCalled()
    expect(params.value?.value).toBe('0814')
  })

  test('validate external links with empty value', async () => {
    params.editConfigField.format = EDIT_FORMAT_EXT
    params.fieldHeader.type = EDIT_HEADER_TYPE_CHAR
    const wrapper = await mountComponent()
    await wrapper.find(inputSel).setValue('')
    wrapper.unmount()
    expect(fetch).toHaveBeenCalled()
    expect(params.value?.value).toBe('')
  })

  test('render component with name field and new row', async () => {
    params.value = copy(emptyData)
    const wrapper = await mountComponent()
    expect(wrapper.find(
      cellRootSel).attributes().title).toBe(CELL_NODE_NAME_NEW)
  })

  test('unmount to initialize source node for new row', async () => {
    params.api = mockGridApi as unknown as GridApi
    params.value = copy(emptyData)
    const wrapper = await mountComponent()
    expect(updateNode).not.toHaveBeenCalled()

    await wrapper.find(inputSel).setValue('0815')
    wrapper.unmount()

    expect(fetch).not.toHaveBeenCalled() // No fetch as we aren't saving yet
    expect(updateNode).toHaveBeenCalledWith({
      api: mockGridApi,
      assayMode: false,
      column: undefined,
      createNew: true,
      nameCellData: {
        editable: true,
        newInit: false,
        newRow: true,
        unit: '',
        uuid: '',
        value: '0815'
      },
      rowNode: undefined,
      tableUuid: STUDY_UUID
    })
  })

  // TODO: Test node renaming
  // TODO: Test validation with sample pooling
})
