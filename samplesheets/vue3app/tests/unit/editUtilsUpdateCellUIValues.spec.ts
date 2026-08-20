import { beforeEach, describe, expect, test, vi } from 'vitest'
import { type GridApi } from 'ag-grid-community'

import { updateCellUIValues } from '@/utils/editUtils.ts'
import { type CellEditData } from '@/types.ts'

import { copy } from '../testUtils.ts'
import { TMP_UUID, TMP_UUID2 } from '../testConstants.ts'

// Test Data -------------------------------------------------------------------

const defaultCell: CellEditData = {
  fieldId: 'col0',
  headerName: 'Name',
  headerType: 'name',
  itemType: 'SOURCE',
  objCls: 'GenericMaterial',
  ogValue: '0814',
  uuid: TMP_UUID,
  value: '0814-update'
}
let mockGridApi: GridApi

// Global Setup ----------------------------------------------------------------

function mockForEachNode (nodes: Array<object>) {
  mockGridApi.forEachNode = vi.fn((callback) => {
    nodes.forEach(node => callback(node))
  })
}

// Tests for updateCellUIValues() ----------------------------------------------

describe('updateCellUIValues()', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGridApi = {
      forEachNode: vi.fn(),
      refreshCells: vi.fn()
    } as unknown as GridApi
  })

  test('update UI value of single cell', async () => {
    const mockNodes = [
      {
        data: {
          'col0': { value: '0814', uuid: TMP_UUID },
          'col1': { value: 'x', uuid: TMP_UUID }
        },
        setDataValue: vi.fn()
      },
      {
        data: {
          'col0': { value: '0815', uuid: TMP_UUID2 },
          'col1': { value: 'y', uuid: TMP_UUID2 }
        },
        setDataValue: vi.fn()
      }
    ]
    mockForEachNode(mockNodes)
    const cells = [copy(defaultCell) as CellEditData]

    expect(mockGridApi.forEachNode).not.toHaveBeenCalled()
    expect(mockGridApi.refreshCells).not.toHaveBeenCalled()

    updateCellUIValues(mockGridApi, cells, true, false)
    expect(mockGridApi.forEachNode).toHaveBeenCalled()
    expect(mockNodes[0]?.data['col0'].value).toBe('0814-update')
    // Other row node values should be unchanged
    expect(mockNodes[0]?.data['col1'].value).toBe('x')
    expect(mockNodes[1]?.data['col0'].value).toBe('0815')
    expect(mockNodes[1]?.data['col1'].value).toBe('y')
    // No unit should be added
    expect(mockNodes[0]?.data['col0'].hasOwnProperty('unit')).toBe(false)
    expect(mockGridApi.refreshCells).toHaveBeenCalled()
  })

  test('revert UI value', async () => {
    const mockNodes = [{
      data: { 'col0': { value: '0814', uuid: TMP_UUID } }, setDataValue: vi.fn()
    }]
    mockForEachNode(mockNodes)
    const cells = [copy(defaultCell) as CellEditData]

    expect(mockGridApi.forEachNode).not.toHaveBeenCalled()
    expect(mockGridApi.refreshCells).not.toHaveBeenCalled()

    updateCellUIValues(mockGridApi, cells, true, true) // revert=true
    expect(mockGridApi.forEachNode).toHaveBeenCalled()
    expect(mockNodes[0]?.data['col0'].value).toBe('0814')
    expect(mockNodes[0]?.data['col0'].hasOwnProperty('unit')).toBe(false)
  })

  test('update UI unit', async () => {
    const mockNodes = [{
      data: {
        'col0': { value: '0814', unit: 'day', uuid: TMP_UUID } },
        setDataValue: vi.fn()
    }]
    mockForEachNode(mockNodes)
    const cells = [copy(defaultCell) as CellEditData]
    cells[0]!.unit = 'year'
    cells[0]!.ogUnit = 'day'
    updateCellUIValues(mockGridApi, cells, true, false)
    expect(mockNodes[0]?.data['col0'].value).toBe('0814-update')
    expect(mockNodes[0]?.data['col0'].unit).toBe('year')
  })

  test('revert UI unit', async () => {
    const mockNodes = [{
      data: {
        'col0': { value: '0814', unit: 'day', uuid: TMP_UUID } },
        setDataValue: vi.fn()
    }]
    mockForEachNode(mockNodes)
    const cells = [copy(defaultCell) as CellEditData]
    cells[0]!.unit = 'year'
    cells[0]!.ogUnit = 'day'
    updateCellUIValues(mockGridApi, cells, true, true) // revert=true
    expect(mockNodes[0]?.data['col0'].value).toBe('0814')
    expect(mockNodes[0]?.data['col0'].unit).toBe('day')
  })
})
