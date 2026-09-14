import { describe, expect, test } from 'vitest'
import { getColWidth } from '@/utils/gridUtils.ts'
import { EDIT_COL_TYPE_EXT_LINKS, EDIT_COL_TYPE_NAME } from '@/constants.ts'

// Tests -----------------------------------------------------------------------

describe('getColWidth()', () => {
  test('get column widths', async () => {
    const res: Array<number> = getColWidth({
      colIdx: 1,
      colType: EDIT_COL_TYPE_NAME,
      lastVis: 2,
      maxColWidth: 250,
      maxValueLen: 12,
      minColWidth: 50,
    })
    expect(res).toEqual([12 * 10 + 25, 50])
  })

  test('get widths with calculated width higher than maximum', async () => {
    const res: Array<number> = getColWidth({
      colIdx: 1,
      colType: EDIT_COL_TYPE_NAME,
      lastVis: 2,
      maxColWidth: 250,
      maxValueLen: 24,
      minColWidth: 50,
    })
    expect(res).toEqual([250, 50]) // Should be capped to max width
  })

  test('get widths with calculated width lower than minimum', async () => {
    const res: Array<number> = getColWidth({
      colIdx: 1,
      colType: EDIT_COL_TYPE_NAME,
      lastVis: 2,
      maxColWidth: 250,
      maxValueLen: 1,
      minColWidth: 50,
    })
    expect(res).toEqual([50, 50]) // Column and minimum width should be equal
  })

  test('get widths with last visible column', async () => {
    const res: Array<number> = getColWidth({
      colIdx: 2,
      colType: EDIT_COL_TYPE_NAME,
      lastVis: 2,
      maxColWidth: 250,
      maxValueLen: 24,
      minColWidth: 50,
    })
    expect(res).toEqual([265, 50]) // We can exceed max width
  })

  test('get widths with external links column type', async () => {
    const res: Array<number> = getColWidth({
      colIdx: 1,
      colType: EDIT_COL_TYPE_EXT_LINKS,
      lastVis: 2,
      maxColWidth: 250,
      maxValueLen: 2,
      minColWidth: 50,
    })
    expect(res).toEqual([2 * 120, 150])
  })

  test('get widths with external links and width > max', async () => {
    const res: Array<number> = getColWidth({
      colIdx: 1,
      colType: EDIT_COL_TYPE_EXT_LINKS,
      lastVis: 2,
      maxColWidth: 250,
      maxValueLen: 4,
      minColWidth: 50,
    })
    expect(res).toEqual([250, 150])
  })

  test('get widths with external links and width < min', async () => {
    const res: Array<number> = getColWidth({
      colIdx: 1,
      colType: EDIT_COL_TYPE_EXT_LINKS,
      lastVis: 2,
      maxColWidth: 250,
      maxValueLen: 0,
      minColWidth: 50,
    })
    expect(res).toEqual([150, 150])
  })

  test('get widths with external links and last visible column', async () => {
    const res: Array<number> = getColWidth({
      colIdx: 2,
      colType: EDIT_COL_TYPE_EXT_LINKS,
      lastVis: 2,
      maxColWidth: 250,
      maxValueLen: 3,
      minColWidth: 50,
    })
    expect(res).toEqual([360, 150])
  })
})
