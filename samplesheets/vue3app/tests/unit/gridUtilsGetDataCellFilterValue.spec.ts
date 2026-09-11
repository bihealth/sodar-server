import { describe, expect, test } from 'vitest'
import { type ValueGetterParams } from 'ag-grid-community'
import { getDataCellFilterValue } from '@/utils/gridUtils.ts'

// Tests -----------------------------------------------------------------------

describe('getDataCellFilterValue()', () => {
  function getParams (
      value: string | Array<object> | Array<string>
  ): ValueGetterParams {
    return {
      column: { getColId: () => { return 'col0' } },
      data: { 'col0': { value: value } }
    } as ValueGetterParams
  }

  test('get value with string', async () => {
    const res = getDataCellFilterValue(getParams('xxxyyy'))
    expect(res).toBe('xxxyyy')
  })

  test('get value with array of strings', async () => {
    const res = getDataCellFilterValue(getParams(['x', 'y']))
    expect(res).toBe('x;y')
  })

  test('get value with array of objects', async () => {
    const res = getDataCellFilterValue(getParams([{ name: 'x'}, { name: 'y' }]))
    expect(res).toBe('x;y')
  })
})
