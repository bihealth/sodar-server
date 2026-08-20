import { beforeEach, describe, expect, test, vi } from 'vitest'
import { type Column, type IRowNode } from 'ag-grid-community'

import { getNamePrefix } from '@/utils/editUtils.ts'
import {
  EDIT_HEADER_TYPE_CHAR,
  EDIT_HEADER_TYPE_NAME,
  EDIT_HEADER_TYPE_PROCESS,
  EDIT_ITEM_TYPE_DATA,
} from '@/constants.ts'

// Test Data -------------------------------------------------------------------

let mockCols: Array<Column>
let mockRowNode: IRowNode
const sampleColId = 'col7'
const sourceColId = 'col1'

// Tests for getNamePrefix() ---------------------------------------------------

describe('getNamePrefix()', () => {
  function getMockColDef (headerType: string, itemType?: string): object {
    return {
      cellEditorParams: {
        fieldHeader: { item_type: itemType || '', type: headerType } } }
  }

  function getMockCols (): object {
    return [
      { getColId: () => { return 'rowNum' } },
      {
        getColId: () => { return sourceColId },
        getColDef: () => { return getMockColDef(EDIT_HEADER_TYPE_NAME) }
      },
      { getColId: () => { return sampleColId } },
    ]
  }

  function getMockRowNode (): IRowNode {
    return {
      data: {
        rowNum: 1,
        [sourceColId]: { value: '0814' },
        [sampleColId]: { value: '' }, // No value yet
      },
      id: '0'
    } as IRowNode
  }

  beforeEach(() => {
    vi.clearAllMocks()
    mockCols = getMockCols() as Array<Column>
    mockRowNode = getMockRowNode()
  })

  test('get prefix with previous node name set', async () => {
    const res = getNamePrefix(mockRowNode, mockCols, 2)
    expect(res).toBe('0814')
  })

  test('get prefix with previous node name unset', async () => {
    mockRowNode.data[sourceColId].value = ''
    const res = getNamePrefix(mockRowNode, mockCols, 2)
    expect(res).toBe('')
  })

  test('get prefix with previous node as process', async () => {
    mockCols[1]!.getColDef = () => {
      return getMockColDef(EDIT_HEADER_TYPE_PROCESS) }
    const res = getNamePrefix(mockRowNode, mockCols, 2)
    expect(res).toBe('0814')
  })

  test('get prefix with previous node as characteristic', async () => {
    mockCols[1]!.getColDef = () => {
      return getMockColDef(EDIT_HEADER_TYPE_CHAR) }
    const res = getNamePrefix(mockRowNode, mockCols, 2)
    expect(res).toBe('')
  })

  test('get prefix with previous node as data item', async () => {
    mockCols[1]!.getColDef = () => {
      return getMockColDef(EDIT_HEADER_TYPE_NAME, EDIT_ITEM_TYPE_DATA) }
    const res = getNamePrefix(mockRowNode, mockCols, 2)
    expect(res).toBe('')
  })
})
