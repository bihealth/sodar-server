import { describe, expect, test } from 'vitest'
import { getFlatValue } from '@/utils/gridUtils.ts'

// Tests -----------------------------------------------------------------------

describe('getFlatValue()', () => {
  test('get flat value with array of strings', async () => {
    const res = getFlatValue(['x', 'y']) as string
    expect(res).toBe('x;y')
  })

  test('get flat value with array of objects with name member', async () => {
    const val = [
      { name: 'x' },
      { name: 'y' },
    ]
    const res = getFlatValue(val)
    expect(res).toBe('x;y')
  })

  test('get flat value with string', async () => {
    const res = getFlatValue('xxxyyy') as string
    expect(res).toBe('xxxyyy')
  })
})
