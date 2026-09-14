import { describe, expect, test } from 'vitest'

import { compareDataCellValues } from '@/utils/gridUtils.ts'
import { type SheetTableCellData, type SheetTableOntologyRef } from '@/types.ts'
import {
  EDIT_COL_TYPE_NAME,
  EDIT_COL_TYPE_NUMERIC,
  EDIT_COL_TYPE_ONTOLOGY
} from '@/constants.ts'

// Tests -----------------------------------------------------------------------

describe('compareDataCellValues()', () => {
  test('compare data cells with string values', async () => {
    const dataA = {
      colType: EDIT_COL_TYPE_NAME, value: 'a' } as SheetTableCellData
    const dataB = {
      colType: EDIT_COL_TYPE_NAME, value: 'b' } as SheetTableCellData
    const res = compareDataCellValues(dataA, dataB)
    expect(res).toBe(-1)
  })

  test('compare data cells in inverse order', async () => {
    const dataA = {
      colType: EDIT_COL_TYPE_NAME, value: 'a' } as SheetTableCellData
    const dataB = {
      colType: EDIT_COL_TYPE_NAME, value: 'b' } as SheetTableCellData
    const res = compareDataCellValues(dataB, dataA)
    expect(res).toBe(1)
  })

  test('compare data cells with numeric values', async () => {
    const dataA = {
      colType: EDIT_COL_TYPE_NUMERIC, value: '1' } as SheetTableCellData
    const dataB = {
      colType: EDIT_COL_TYPE_NUMERIC, value: '2' } as SheetTableCellData
    const res = compareDataCellValues(dataA, dataB)
    expect(res).toBe(-1)
  })

  test('compare data cells with numeric values in inverse order', async () => {
    const dataA = {
      colType: EDIT_COL_TYPE_NUMERIC, value: '1' } as SheetTableCellData
    const dataB = {
      colType: EDIT_COL_TYPE_NUMERIC, value: '2' } as SheetTableCellData
    const res = compareDataCellValues(dataB, dataA)
    expect(res).toBe(1)
  })

  test('compare data cells with object values', async () => {
    const dataA = {
      colType: EDIT_COL_TYPE_ONTOLOGY,
      value: [{ name: 'a' } as SheetTableOntologyRef]
    } as SheetTableCellData
    const dataB = {
      colType: EDIT_COL_TYPE_ONTOLOGY,
      value: [{ name: 'b' } as SheetTableOntologyRef]
    } as SheetTableCellData
    const res = compareDataCellValues(dataB, dataA) // Inverse order
    expect(res).toBe(1)
  })
})
