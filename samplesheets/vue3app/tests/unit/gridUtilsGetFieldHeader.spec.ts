import { describe, expect, test } from 'vitest'
import {
  type CellClassFunc,
  type CellClassParams,
  type ColDef,
  type Column,
} from 'ag-grid-community'

import { getFieldHeader } from '@/utils/gridUtils.ts'
import {
  type SheetTableFieldHeader,
  type SodarContextLinkLabel,
} from '@/types.ts'
import { EDIT_COL_TYPE_NAME, EDIT_COL_TYPE_ONTOLOGY } from '@/constants.ts'

import { sodarContext } from '../data/sodarContext.ts'

// Tests -----------------------------------------------------------------------

describe('getFieldHeader()', () => {
  const fieldHeader = {
    value: 'Organism',
    col_type: EDIT_COL_TYPE_ONTOLOGY
  } as SheetTableFieldHeader
  const linkLabels = sodarContext.external_link_labels as {
    [key: string]: string | SodarContextLinkLabel }

  test('get field header', async () => {
    // TODO: Set up test data in a variable and update
    const res: ColDef = getFieldHeader({
      colAlign: 'left',
      colWidth: 250,
      editMode: false,
      externalLinkLabels: linkLabels,
      fieldEditable: true,
      fieldHeader: fieldHeader,
      fieldIdx: 2,
      fieldVisible: true,
      minColWidth: 50,
    })
    expect(res.headerName).toBe('Organism')
    expect(res.field).toBe('col2')
    expect(res.width).toBe(250)
    expect(res.minWidth).toBe(50)
    expect(res.hide).toBe(false)
    expect(res.cellRendererParams.colType).toBe(EDIT_COL_TYPE_ONTOLOGY)
    expect(res.cellRendererParams.editMode).toBe(false)
    expect(res.cellRendererParams.fieldEditable).toBe(true)
    expect(res.cellRendererParams.linkLabels).toBe(linkLabels)
    expect(res.cellClass).toContain('text-left')
    expect(res.cellClass).not.toContain('text-right')
  })

  test('get field header with fieldVisible=false', async () => {
    const res: ColDef = getFieldHeader({
      colAlign: 'left',
      colWidth: 250,
      editMode: false,
      externalLinkLabels: linkLabels,
      fieldEditable: true,
      fieldHeader: fieldHeader,
      fieldIdx: 2, // Updated
      fieldVisible: false,
      minColWidth: 50,
    })
    expect(res.hide).toBe(true)
  })

  test('get field header with right aligned content', async () => {
    const res: ColDef = getFieldHeader({
      colAlign: 'right',  // Updated
      colWidth: 250,
      editMode: false,
      externalLinkLabels: linkLabels,
      fieldEditable: true,
      fieldHeader: fieldHeader,
      fieldIdx: 2,
      fieldVisible: true,
      minColWidth: 50,
    })
    expect(res.cellClass).not.toContain('text-left')
    expect(res.cellClass).toContain('text-right')
  })

  test('get field header with editMode=true', async () => {
    const res: ColDef = getFieldHeader({
      colAlign: 'left',
      colWidth: 250,
      editMode: true, // Updated
      externalLinkLabels: linkLabels,
      fieldEditable: true,
      fieldHeader: fieldHeader,
      fieldIdx: 2,
      fieldVisible: true,
      minColWidth: 50,
    })
    expect(res.cellRendererParams.editMode).toBe(true)
    expect(typeof res.cellClass).toBe('function')

    // Test cellClass callback
    // TODO: Test this in separate tests with different params
    const cc = (res.cellClass as CellClassFunc)({
      colDef: { cellRendererParams: { colType: EDIT_COL_TYPE_NAME } },
      column: {} as Column,
      value: { editable: true, value: 'x' }
    } as CellClassParams)
    expect(cc).toEqual(['sodar-ss-data-cell', 'text-left'])
  })
})
