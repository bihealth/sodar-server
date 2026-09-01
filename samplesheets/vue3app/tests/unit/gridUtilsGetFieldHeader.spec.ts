import { beforeEach, describe, expect, test } from 'vitest'
import {
  type CellClassFunc,
  type CellClassParams,
  type Column,
} from 'ag-grid-community'

import { getFieldHeader } from '@/utils/gridUtils.ts'
import {
  type FieldHeaderGetParams,
  type SheetTableFieldHeader,
  type SodarContextLinkLabel,
} from '@/types.ts'
import {
  EDIT_COL_TYPE_NAME,
  EDIT_COL_TYPE_NUMERIC,
  EDIT_COL_TYPE_ONTOLOGY,
  EDIT_COL_TYPE_UNIT
} from '@/constants.ts'

import { copy } from '../testUtils.ts'
import { sodarContext } from '../data/sodarContext.ts'

// Test Data -------------------------------------------------------------------

const fieldHeader = {
  value: 'Organism',
  col_type: EDIT_COL_TYPE_ONTOLOGY
} as SheetTableFieldHeader
const linkLabels = sodarContext.external_link_labels as {
  [key: string]: string | SodarContextLinkLabel }
const defaultParams: FieldHeaderGetParams = {
  colAlign: 'left',
  colWidth: 250,
  editMode: false,
  externalLinkLabels: linkLabels,
  fieldEditable: true,
  fieldHeader: fieldHeader,
  fieldIdx: 2,
  fieldVisible: true,
  minColWidth: 50,
}
let params: FieldHeaderGetParams

// Tests -----------------------------------------------------------------------

describe('getFieldHeader()', () => {
  function getCellClassParams (
      colType: string,
      editable?: boolean,
      newInit?: boolean,
  ): CellClassParams {
    return {
      colDef: { cellRendererParams: { colType: colType } },
      column: {} as Column,
      value: { editable: editable, newInit: newInit, value: 'x' }
    } as CellClassParams
  }

  beforeEach(() => {
    params = copy(defaultParams) as FieldHeaderGetParams
  })

  test('get field header', async () => {
    const res = getFieldHeader(params)
    expect(res.headerName).toBe('Organism')
    expect(res.field).toBe('col2')
    expect(res.width).toBe(250)
    expect(res.minWidth).toBe(50)
    expect(res.hide).toBe(false)
    expect(res.cellRendererParams.colType).toBe(EDIT_COL_TYPE_ONTOLOGY)
    expect(res.cellRendererParams.editMode).toBe(false)
    expect(res.cellRendererParams.fieldEditable).toBe(true)
    expect(res.cellRendererParams.linkLabels).toEqual(linkLabels)
    expect(res.cellClass).toContain('text-left')
    expect(res.cellClass).not.toContain('text-right')
  })

  test('get field header with fieldVisible=false', async () => {
    params.fieldVisible = false
    const res = getFieldHeader(params)
    expect(res.hide).toBe(true)
  })

  test('get field header with right aligned content', async () => {
    params.colAlign = 'right'
    const res = getFieldHeader(params)
    expect(res.cellClass).not.toContain('text-left')
    expect(res.cellClass).toContain('text-right')
  })

  test('get field header with editMode=true', async () => {
    params.editMode = true
    const res = getFieldHeader(params)
    expect(res.cellRendererParams.editMode).toBe(true)
    expect(typeof res.cellClass).toBe('function')
    expect(typeof res.valueParser).toBe('function')
  })

  test('get edit mode cell class', async () => {
    params.editMode = true
    const res = getFieldHeader(params)
    const cc = (res.cellClass as CellClassFunc)(
      getCellClassParams(EDIT_COL_TYPE_NAME, true))
    expect(cc).toEqual(['sodar-ss-data-cell', 'text-left'])
  })

  test('get edit mode cell class with numeric type', async () => {
    params.editMode = true
    const res = getFieldHeader(params)
    const cc = (res.cellClass as CellClassFunc)(
      getCellClassParams(EDIT_COL_TYPE_NUMERIC, true))
    expect(cc).toEqual(['sodar-ss-data-cell', 'text-right'])
  })

  test('get edit mode cell class with unit type', async () => {
    params.editMode = true
    const res = getFieldHeader(params)
    const cc = (res.cellClass as CellClassFunc)(
      getCellClassParams(EDIT_COL_TYPE_UNIT, true))
    expect(cc).toEqual(['sodar-ss-data-cell', 'text-right'])
  })

  test('get edit mode cell class with editable=False', async () => {
    params.editMode = true
    const res = getFieldHeader(params)
    const cc = (res.cellClass as CellClassFunc)(
      getCellClassParams(EDIT_COL_TYPE_NAME, false))
    expect(cc).toEqual([
      'sodar-ss-data-cell', 'text-left', 'bg-light', 'text-muted'])
  })

  test('get edit mode cell class with editable=False and newInit', async () => {
    params.editMode = true
    const res = getFieldHeader(params)
    const cc = (res.cellClass as CellClassFunc)(
      getCellClassParams(EDIT_COL_TYPE_NAME, false, true))
    expect(cc).toEqual([
      'sodar-ss-data-cell',
      'text-left',
      'sodar-ss-data-forbidden',
      'text-muted'])
  })
})
