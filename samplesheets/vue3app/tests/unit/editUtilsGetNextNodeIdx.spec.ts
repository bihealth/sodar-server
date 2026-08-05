import { describe, expect, test } from 'vitest'
import { type Column } from 'ag-grid-community'
import { getNextNodeIdx } from '@/utils/editUtils.ts'

// Tests for getNextNodeIdx() --------------------------------------------------

describe('getNextNodeIdx()', () => {
  function getCols (groupIds: Array<string>): Array<Column> {
    const ret = []
    for (const g of groupIds) {
      ret.push({
        getOriginalParent: () => { return { getGroupId: () => { return g } } }
      } as Column)
    }
    // Push final node to represent rowEdit column
    ret.push({
      getOriginalParent: () => { return { getGroupId: () => { return '999' } } }
    } as Column)
    return ret
  }

  test('get index with two nodes with single cell', async () => {
    expect(getNextNodeIdx(getCols(['1', '2']), 0)).toBe(1)
  })

  test('get index with two nodes with multiple cells', async () => {
    expect(getNextNodeIdx(getCols(['1', '1', '2', '2']), 0)).toBe(2)
  })

  test('get index with index > 0', async () => {
    expect(getNextNodeIdx(getCols(['1', '1', '2', '2']), 1)).toBe(2)
  })

  test('get index with index past beginning of last node', async () => {
    expect(getNextNodeIdx(getCols(['1', '1', '2', '2']), 2)).toBe(null)
  })

  test('get index with start index > column length', async () => {
    // NOTE: We actually have 3 columns
    expect(getNextNodeIdx(getCols(['1', '2']), 3)).toBe(null)
  })

  test('get index with start index > column length - 1', async () => {
    expect(getNextNodeIdx(getCols(['1', '2']), 2)).toBe(null)
  })

  test('get index with empty column list', async () => {
    expect(getNextNodeIdx(getCols([]), 0)).toBe(null)
  })
})
