import { beforeEach, describe, expect, test, vi } from 'vitest'
import { mount, type VueWrapper } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { type GridApi } from 'ag-grid-community'

import DataCellEditor from '@/components/editors/DataCellEditor.vue'
import { useAppStore } from '@/stores/appStore.ts'
import { useTableStore } from '@/stores/tableStore.ts'
import {
  type GridCellEditorParams,
  type SheetTableFieldHeader,
  type StudyEditConfigNodeField,
} from '@/types.ts'

import studyTablesEdit from '../data/studyTablesEdit.json'
import { copy, waitSelector } from '../testUtils.ts'
import {
  ASSAY_UUID,
  PROJECT_UUID,
  STUDY_UUID,
  TMP_UUID
} from '../testConstants.ts'

// Set default params data as name field
const defaultParams = {
  assayMode: false,
  colAlign: 'left',
  colWidth: 125,
  editConfigField: {
    name: 'Name',
    type: 'name'
  },
  fieldHeader: copy(
    studyTablesEdit.tables.study.field_header[0] as SheetTableFieldHeader) as
    SheetTableFieldHeader,
  fieldId: 'col0',
  sampleColId: 'col7',
  tableUuid: STUDY_UUID,
  value: {
    value: '0814',
    uuid: TMP_UUID
  },
}
let params: GridCellEditorParams

// Default edit configuration for select field
const selectEditField: StudyEditConfigNodeField = {
  default: '',
  name: 'Name',
  format: 'select',
  options: ['0814', '0815'],
  type: 'characteristics',
}

// Default edit configuration for unit field
const unitEditField: StudyEditConfigNodeField = {
  default: '',
  name: 'Name',
  format: 'unit',
  unit: ['day', 'year'],
  unit_default: 'day',
  type: 'characteristics',
}

const cellUpdateUrl: string = '/samplesheets/ajax/edit/cell/' + PROJECT_UUID
// NOTE: Purposefully defined as a string, will be converted to RegExp
const letterOnlyRegex: string = '^[a-z]+$'
const exLinksInput: string = 'x-generic-remote:123;x-sodar-example-link:456'

describe('DataCellEditor.vue', () => {
  const mockGridApi = {
    forEachNode: vi.fn(),
    refreshCells: vi.fn()
  }

  async function mountComponent (): Promise<VueWrapper> {
    const wrapper = mount(DataCellEditor, { props: { params: params } })
    await waitSelector(wrapper, '.sodar-ss-editor-cell', 1)
    return wrapper
  }

  beforeEach(() => {
    vi.clearAllMocks()
    global.fetch = vi.fn(() => Promise.resolve({
      json: () => Promise.resolve({ detail: 'ok' }), status: 200} as Response)
    )

    setActivePinia(createPinia())
    const appStore = useAppStore()
    appStore.projectUuid = PROJECT_UUID
    const tableStore = useTableStore()
    // Mock tableStore GridApi:s
    tableStore.gridApi.study = mockGridApi as unknown as GridApi
    tableStore.gridApi.assays[ASSAY_UUID] = mockGridApi as unknown as GridApi
    params = copy(defaultParams) as GridCellEditorParams
  })

  test('render component with text input and default value', async () => {
    const wrapper = await mountComponent()
    expect(wrapper.find('.sodar-ss-edit-select').exists()).toBe(false)
    expect(wrapper.find('.sodar-ss-edit-unit').exists()).toBe(false)
    const input = wrapper.find('.sodar-ss-edit-input')
    expect(input.exists()).toBe(true) // NOTE: Can't assert value here
  })

  test('return text value with getValue()', async () => {
    const wrapper = await mountComponent() as VueWrapper<typeof DataCellEditor>
    const res = wrapper.vm.getValue()
    expect(res.value).toBe('0814')
    expect(res.uuid).toBe(TMP_UUID)
  })

  test('update text value', async () => {
    const wrapper = await mountComponent() as VueWrapper<typeof DataCellEditor>
    await wrapper.find('.sodar-ss-edit-input').setValue('0815')
    const res = wrapper.vm.getValue()
    expect(res.value).toBe('0815')
    expect(res.uuid).toBe(TMP_UUID) // Assert UUID is still present
    expect(params.value?.value).toBe('0815')
  })

  test('trim updated text value', async () => {
    const wrapper = await mountComponent() as VueWrapper<typeof DataCellEditor>
    await wrapper.find('.sodar-ss-edit-input').setValue('  0815  ')
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
    await wrapper.find('.sodar-ss-edit-input').setValue('a;b;c')
    const res = wrapper.vm.getValue()
    expect(res.value).toEqual(['a', 'b', 'c'])
  })

  test('update and trim list value', async () => {
    params.value!.value = ['x', 'y']
    const wrapper = await mountComponent() as VueWrapper<typeof DataCellEditor>
    await wrapper.find('.sodar-ss-edit-input').setValue('a ;  b ; c  ')
    const res = wrapper.vm.getValue()
    expect(res.value).toEqual(['a', 'b', 'c'])
  })

  test('update list value with extra separator', async () => {
    params.value!.value = ['x', 'y']
    const wrapper = await mountComponent() as VueWrapper<typeof DataCellEditor>
    // Extra trailing separator
    await wrapper.find('.sodar-ss-edit-input').setValue('a;b;c;')
    const res = wrapper.vm.getValue()
    expect(res.value).toEqual(['a', 'b', 'c']) // No empty item
  })

  test('render empty value', async () => {
    params.value!.value = ''
    const wrapper = await mountComponent() as VueWrapper<typeof DataCellEditor>
    const res = wrapper.vm.getValue()
    expect(res.value).toBe('')
  })

  test('update input into empty value', async () => {
    const wrapper = await mountComponent() as VueWrapper<typeof DataCellEditor>
    await wrapper.find('.sodar-ss-edit-input').setValue('')
    const res = wrapper.vm.getValue()
    expect(res.value).toBe('')
  })

  test('render component with value select enabled', async () => {
    params.editConfigField = copy(selectEditField) as StudyEditConfigNodeField
    const wrapper = await mountComponent()
    expect(wrapper.find('.sodar-ss-edit-input').exists()).toBe(false)
    expect(wrapper.find('.sodar-ss-edit-unit').exists()).toBe(false)
    const select = wrapper.find('.sodar-ss-edit-select')
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
    await wrapper.find('.sodar-ss-edit-select').setValue('0815')
    const res = wrapper.vm.getValue()
    expect(res.value).toBe('0815')
    expect(res.uuid).toBe(TMP_UUID) // Assert UUID is unaffected
  })

  test('update select value to empty value', async () => {
    params.editConfigField = copy(selectEditField) as StudyEditConfigNodeField
    const wrapper = await mountComponent() as VueWrapper<typeof DataCellEditor>
    await wrapper.find('.sodar-ss-edit-select').setValue('')
    const res = wrapper.vm.getValue()
    expect(res.value).toBe('')
    expect(res.uuid).toBe(TMP_UUID)
  })

  test('render value with unit', async () => {
    params.value!.unit = 'day'
    params.editConfigField = copy(unitEditField) as StudyEditConfigNodeField
    const wrapper = await mountComponent()
    expect(wrapper.find('.sodar-ss-edit-select').exists()).toBe(false)
    expect(wrapper.find('.sodar-ss-edit-input').exists()).toBe(true)
    expect(wrapper.find('.sodar-ss-edit-unit').exists()).toBe(true)
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
    await wrapper.find('.sodar-ss-edit-unit').setValue('year')
    const res = wrapper.vm.getValue()
    expect(res.unit).toBe('year')
  })

  test('unmount with updated value', async () => {
    const reqBody = {
      updated_cells: [{
        header_name: 'Name',
        header_type: 'name',
        obj_cls: 'GenericMaterial',
        uuid: TMP_UUID,
        value: '0815',
        item_type: 'SOURCE'
      }],
      verify: true
    }
    expect(fetch).not.toHaveBeenCalled()

    const wrapper = await mountComponent()
    await wrapper.find('.sodar-ss-edit-input').setValue('0815')
    wrapper.unmount()
    expect(fetch).toHaveBeenCalledWith(
      cellUpdateUrl,
      expect.objectContaining({ body: JSON.stringify(reqBody)}))
  })

  test('unmount with unchanged value', async () => {
    expect(fetch).not.toHaveBeenCalled()
    const wrapper = await mountComponent()
    wrapper.unmount()
    expect(fetch).not.toHaveBeenCalled()
  })

  test('unmount with updated unit', async () => {
    params.value!.unit = 'day'
    params.editConfigField = copy(unitEditField) as StudyEditConfigNodeField
    const reqBody = {
      updated_cells: [{
        header_name: 'Name',
        header_type: 'name',
        obj_cls: 'GenericMaterial',
        uuid: TMP_UUID,
        value: '0814',
        item_type: 'SOURCE',
        unit: 'year', // This should be changed
      }],
      verify: true
    }
    expect(fetch).not.toHaveBeenCalled()

    const wrapper = await mountComponent()
    await wrapper.find('.sodar-ss-edit-unit').setValue('year')
    wrapper.unmount()
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
    const input = wrapper.find('.sodar-ss-edit-input')
    expect(input.classes()).not.toContain('text-danger')
    await wrapper.find('.sodar-ss-edit-input').setValue('0815+') // Invalid char
    expect(input.classes()).toContain('text-danger')
  })

  test('validate invalid name', async () => {
    const wrapper = await mountComponent()
    await wrapper.find('.sodar-ss-edit-input').setValue('0815+')
    wrapper.unmount()
    expect(fetch).not.toHaveBeenCalled() // No Ajax call to update value
    expect(params.value?.value).toBe('0814') // No change to value
  })

  test('validate empty name', async () => {
    const wrapper = await mountComponent()
    await wrapper.find('.sodar-ss-edit-input').setValue('')
    wrapper.unmount()
    expect(fetch).not.toHaveBeenCalled()
    expect(params.value?.value).toBe('0814')
  })

  test('validate data name', async () => {
    params.fieldHeader.item_type = 'DATA'
    const wrapper = await mountComponent()
    // Dot is approved here
    await wrapper.find('.sodar-ss-edit-input').setValue('0815.txt')
    wrapper.unmount()
    expect(fetch).toHaveBeenCalled()
    expect(params.value?.value).toBe('0815.txt')
  })

  test('validate invalid data name', async () => {
    params.fieldHeader.item_type = 'DATA'
    const wrapper = await mountComponent()
    await wrapper.find('.sodar-ss-edit-input').setValue('0815+')
    wrapper.unmount()
    expect(fetch).not.toHaveBeenCalled()
    expect(params.value?.value).toBe('0814')
  })

  test('validate empty data name value', async () => {
    params.fieldHeader.item_type = 'DATA'
    const wrapper = await mountComponent()
    // Empty value is approved for DATA
    await wrapper.find('.sodar-ss-edit-input').setValue('')
    wrapper.unmount()
    expect(fetch).toHaveBeenCalled()
    expect(params.value?.value).toBe('')
  })

  test('validate custom regex with valid value', async () => {
    params.editConfigField.regex = letterOnlyRegex
    const wrapper = await mountComponent()
    await wrapper.find('.sodar-ss-edit-input').setValue('abc')
    wrapper.unmount()
    expect(fetch).toHaveBeenCalled()
    expect(params.value?.value).toBe('abc')
  })

  test('validate custom regex with invalid value', async () => {
    params.editConfigField.regex = letterOnlyRegex // Does not accept numbers
    const wrapper = await mountComponent()
    await wrapper.find('.sodar-ss-edit-input').setValue('abc123')
    wrapper.unmount()
    expect(fetch).not.toHaveBeenCalled()
    // Revert to old value, it's ok even if it doesn't match current regex :)
    expect(params.value?.value).toBe('0814')
  })

  test('validate integer', async () => {
    params.editConfigField.format = 'integer'
    params.fieldHeader.type = 'characteristics'
    const wrapper = await mountComponent()
    await wrapper.find('.sodar-ss-edit-input').setValue('815')
    wrapper.unmount()
    expect(fetch).toHaveBeenCalled()
    expect(params.value?.value).toBe('815')
  })

  test('validate invalid integer', async () => {
    params.editConfigField.format = 'integer'
    params.fieldHeader.type = 'characteristics'
    const wrapper = await mountComponent()
    await wrapper.find('.sodar-ss-edit-input').setValue('815abc')
    wrapper.unmount()
    expect(fetch).not.toHaveBeenCalled()
    expect(params.value?.value).toBe('0814')
  })

  test('validate empty integer', async () => {
    params.editConfigField.format = 'integer'
    params.fieldHeader.type = 'characteristics'
    const wrapper = await mountComponent()
    await wrapper.find('.sodar-ss-edit-input').setValue('')
    wrapper.unmount()
    expect(fetch).toHaveBeenCalled() // Empty value is accepted here
    expect(params.value?.value).toBe('')
  })

  test('validate integer with invalid double value', async () => {
    params.editConfigField.format = 'integer'
    params.fieldHeader.type = 'characteristics'
    const wrapper = await mountComponent()
    await wrapper.find('.sodar-ss-edit-input').setValue('8.15')
    wrapper.unmount()
    expect(fetch).not.toHaveBeenCalled()
    expect(params.value?.value).toBe('0814')
  })

  test('validate double', async () => {
    params.editConfigField.format = 'double'
    params.fieldHeader.type = 'characteristics'
    const wrapper = await mountComponent()
    await wrapper.find('.sodar-ss-edit-input').setValue('8.15')
    wrapper.unmount()
    expect(fetch).toHaveBeenCalled()
    expect(params.value?.value).toBe('8.15')
  })

  test('validate double with invalid string value', async () => {
    params.editConfigField.format = 'double'
    params.fieldHeader.type = 'characteristics'
    const wrapper = await mountComponent()
    await wrapper.find('.sodar-ss-edit-input').setValue('abc')
    wrapper.unmount()
    expect(fetch).not.toHaveBeenCalled()
    expect(params.value?.value).toBe('0814')
  })

  test('validate double with invalid integer value', async () => {
    params.editConfigField.format = 'double'
    params.fieldHeader.type = 'characteristics'
    const wrapper = await mountComponent()
    await wrapper.find('.sodar-ss-edit-input').setValue('815')
    wrapper.unmount()
    expect(fetch).not.toHaveBeenCalled()
    expect(params.value?.value).toBe('0814')
  })

  test('validate double with valid negative value', async () => {
    params.editConfigField.format = 'double'
    params.fieldHeader.type = 'characteristics'
    const wrapper = await mountComponent()
    await wrapper.find('.sodar-ss-edit-input').setValue('-8.15')
    wrapper.unmount()
    expect(fetch).toHaveBeenCalled()
    expect(params.value?.value).toBe('-8.15')
  })

  test('validate empty double', async () => {
    params.editConfigField.format = 'double'
    params.fieldHeader.type = 'characteristics'
    const wrapper = await mountComponent()
    await wrapper.find('.sodar-ss-edit-input').setValue('')
    wrapper.unmount()
    expect(fetch).toHaveBeenCalled() // Empty value is accepted here
    expect(params.value?.value).toBe('')
  })

  test('validate range with integer', async () => {
    params.editConfigField.format = 'integer'
    params.editConfigField.range = ['1', '2']
    params.fieldHeader.type = 'characteristics'
    const wrapper = await mountComponent()
    await wrapper.find('.sodar-ss-edit-input').setValue('2')
    wrapper.unmount()
    expect(fetch).toHaveBeenCalled()
    expect(params.value?.value).toBe('2')
  })

  test('validate range with invalid integer over limit', async () => {
    params.editConfigField.format = 'integer'
    params.editConfigField.range = ['1', '2']
    params.fieldHeader.type = 'characteristics'
    const wrapper = await mountComponent()
    await wrapper.find('.sodar-ss-edit-input').setValue('3')
    wrapper.unmount()
    expect(fetch).not.toHaveBeenCalled()
    expect(params.value?.value).toBe('0814')
  })

  test('validate range with invalid integer under limit', async () => {
    params.editConfigField.format = 'integer'
    params.editConfigField.range = ['1', '2']
    params.fieldHeader.type = 'characteristics'
    const wrapper = await mountComponent()
    await wrapper.find('.sodar-ss-edit-input').setValue('0')
    wrapper.unmount()
    expect(fetch).not.toHaveBeenCalled()
    expect(params.value?.value).toBe('0814')
  })

  test('validate range with empty integer', async () => {
    params.editConfigField.format = 'integer'
    params.editConfigField.range = ['1', '2']
    params.fieldHeader.type = 'characteristics'
    const wrapper = await mountComponent()
    await wrapper.find('.sodar-ss-edit-input').setValue('')
    wrapper.unmount()
    expect(fetch).toHaveBeenCalled() // Empty is allowed with range
    expect(params.value?.value).toBe('')
  })

 test('validate range with double', async () => {
    params.editConfigField.format = 'double'
    params.editConfigField.range = ['1', '2']
    params.fieldHeader.type = 'characteristics'
    const wrapper = await mountComponent()
    await wrapper.find('.sodar-ss-edit-input').setValue('1.5')
    wrapper.unmount()
    expect(fetch).toHaveBeenCalled()
    expect(params.value?.value).toBe('1.5')
  })

  test('validate range with invalid double over limit', async () => {
    params.editConfigField.format = 'double'
    params.editConfigField.range = ['1', '2']
    params.fieldHeader.type = 'characteristics'
    const wrapper = await mountComponent()
    await wrapper.find('.sodar-ss-edit-input').setValue('2.1')
    wrapper.unmount()
    expect(fetch).not.toHaveBeenCalled()
    expect(params.value?.value).toBe('0814')
  })

  test('validate range with invalid double under limit', async () => {
    params.editConfigField.format = 'double'
    params.editConfigField.range = ['1', '2']
    params.fieldHeader.type = 'characteristics'
    const wrapper = await mountComponent()
    await wrapper.find('.sodar-ss-edit-input').setValue('0.9')
    wrapper.unmount()
    expect(fetch).not.toHaveBeenCalled()
    expect(params.value?.value).toBe('0814')
  })

  test('validate range with empty double', async () => {
    params.editConfigField.format = 'double'
    params.editConfigField.range = ['1', '2']
    params.fieldHeader.type = 'characteristics'
    const wrapper = await mountComponent()
    await wrapper.find('.sodar-ss-edit-input').setValue('')
    wrapper.unmount()
    expect(fetch).toHaveBeenCalled()
    expect(params.value?.value).toBe('')
  })

  test('validate date', async () => {
    params.editConfigField.format = 'date'
    params.fieldHeader.type = 'characteristics'
    const wrapper = await mountComponent()
    await wrapper.find('.sodar-ss-edit-input').setValue('2026-04-13')
    wrapper.unmount()
    expect(fetch).toHaveBeenCalled()
    expect(params.value?.value).toBe('2026-04-13')
  })

  test('validate date with non-date value', async () => {
    params.editConfigField.format = 'date'
    params.fieldHeader.type = 'characteristics'
    const wrapper = await mountComponent()
    await wrapper.find('.sodar-ss-edit-input').setValue('abc')
    wrapper.unmount()
    expect(fetch).not.toHaveBeenCalled()
    expect(params.value?.value).toBe('0814')
  })

  test('validate date with invalid month', async () => {
    params.editConfigField.format = 'date'
    params.fieldHeader.type = 'characteristics'
    const wrapper = await mountComponent()
    await wrapper.find('.sodar-ss-edit-input').setValue('2026-13-13')
    wrapper.unmount()
    expect(fetch).not.toHaveBeenCalled()
    expect(params.value?.value).toBe('0814')
  })

  test('validate date with zero month', async () => {
    params.editConfigField.format = 'date'
    params.fieldHeader.type = 'characteristics'
    const wrapper = await mountComponent()
    await wrapper.find('.sodar-ss-edit-input').setValue('2026-00-13')
    wrapper.unmount()
    expect(fetch).not.toHaveBeenCalled()
    expect(params.value?.value).toBe('0814')
  })

  test('validate date with invalid day', async () => {
    params.editConfigField.format = 'date'
    params.fieldHeader.type = 'characteristics'
    const wrapper = await mountComponent()
    await wrapper.find('.sodar-ss-edit-input').setValue('2026-04-31')
    wrapper.unmount()
    expect(fetch).not.toHaveBeenCalled()
    expect(params.value?.value).toBe('0814')
  })

  test('validate date with zero day', async () => {
    params.editConfigField.format = 'date'
    params.fieldHeader.type = 'characteristics'
    const wrapper = await mountComponent()
    await wrapper.find('.sodar-ss-edit-input').setValue('2026-04-00')
    wrapper.unmount()
    expect(fetch).not.toHaveBeenCalled()
    expect(params.value?.value).toBe('0814')
  })

  test('validate date with empty date', async () => {
    params.editConfigField.format = 'date'
    params.fieldHeader.type = 'characteristics'
    const wrapper = await mountComponent()
    await wrapper.find('.sodar-ss-edit-input').setValue('')
    wrapper.unmount()
    expect(fetch).toHaveBeenCalled()
    expect(params.value?.value).toBe('')
  })

  test('validate external links', async () => {
    params.editConfigField.format = 'external_links'
    params.fieldHeader.type = 'characteristics'
    const wrapper = await mountComponent()
    await wrapper.find('.sodar-ss-edit-input').setValue(exLinksInput)
    wrapper.unmount()
    expect(fetch).toHaveBeenCalled()
    expect(params.value?.value).toEqual(exLinksInput.split(';'))
  })

  test('validate external links with invalid string', async () => {
    params.editConfigField.format = 'external_links'
    params.fieldHeader.type = 'characteristics'
    const wrapper = await mountComponent()
    await wrapper.find('.sodar-ss-edit-input').setValue(exLinksInput + ';;')
    wrapper.unmount()
    expect(fetch).not.toHaveBeenCalled()
    expect(params.value?.value).toBe('0814')
  })

  test('validate external links with empty value', async () => {
    params.editConfigField.format = 'external_links'
    params.fieldHeader.type = 'characteristics'
    const wrapper = await mountComponent()
    await wrapper.find('.sodar-ss-edit-input').setValue('')
    wrapper.unmount()
    expect(fetch).toHaveBeenCalled()
    expect(params.value?.value).toBe('')
  })

  // TODO: Test validation with sample pooling (once nameValues is implemented)
})
