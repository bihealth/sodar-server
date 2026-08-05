import { beforeEach, describe, expect, test, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import {
  type ColDef,
  type Column,
  type GridApi,
  type IRowNode
} from 'ag-grid-community'

import { updateNode } from '@/utils/editUtils.ts'
import { useTableStore } from '@/stores/tableStore.ts'
import {
  type NodeUpdateParams,
  type SheetTableCellData,
} from '@/types.ts'
import {
  DB_OBJ_CLASS_MATERIAL,
  EDIT_COL_TYPE_NAME,
  EDIT_HEADER_TYPE_CHAR,
  EDIT_HEADER_TYPE_NAME,
  EDIT_HEADER_TYPE_PROCESS,
  EDIT_HEADER_TYPE_PROTOCOL,
  HEADER_NAME_SAMPLE,
} from '@/constants.ts'

import { copy } from '../testUtils.ts'
import { STUDY_UUID, TMP_UUID } from '../testConstants.ts'

// Test data -------------------------------------------------------------------

const emptyCellVal = {
  newInit: true,
  newRow: true,
  uuid: '',
  value: ''
}
const emptyValueParams = {
  editable: true,
  newInit: true,
  newRow: true,
  uuid: '',
  value: ''
}
let mockGridApi: GridApi
let mockRowNode: IRowNode
// const sampleUuid = TMP_UUID2
const sourceUuid = TMP_UUID

// Tests for updateNode() ------------------------------------------------------

describe('updateNode()', () => {
  function getMockColDef (): ColDef {
    return {
      cellEditorParams: {
        fieldHeader: {
          type: EDIT_HEADER_TYPE_NAME,
          obj_cls: DB_OBJ_CLASS_MATERIAL
        }
      },
      cellRendererParams: {
        col_type: EDIT_COL_TYPE_NAME,
        fieldEditable: true
      }
    } as ColDef
  }

  function getMockForEachNode (nodes: Array<object>) {
    return vi.fn((callback) => {
      nodes.forEach(node => callback(node))
    })
  }

  function getMockRowNode (): object {
    return {
      data: {
        rowNum: 1,
        'col0': { value: 'col0' },
        'col1': {
          newInit: false,
          newRow: true,
          value: '0814',
          uuid: sourceUuid
        }, // Already filled
        'col2': copy(emptyCellVal),
        'col999': { value: 'xxx' }
      },
      id: '0',
      setDataValue: vi.fn()
    }
  }

  function getMockCol (
      columnId: string,
      groupId: string,
      colDef?: ColDef
  ): Column {
    if (!colDef) colDef = getMockColDef()
    return {
      getColId: () => { return columnId },
      getColDef: () => { return colDef },
      getOriginalParent: () => {
        return {
          getGroupId: () => {
            return groupId
          },
          getColGroupDef: () => {
            return { headerName: groupId === '2' ? HEADER_NAME_SAMPLE : 'xyz' }
          }
        }
      }
    } as Column
  }

  function getMockGridApi (cols: Array<Column>): GridApi {
    cols = [
      getMockCol('col0', '0'),
      getMockCol('col1', '1'),
    ].concat(cols)
    cols.push(getMockCol('col999', '999'))
    const colLookup = cols.map(
      x => ({ [x.getColId() as string]: x })).reduce(
        (a, b) => ({ ...a, ...b }), {}) as { [key: string]: Column }
    return {
      applyTransaction: vi.fn(),
      forEachNode: vi.fn(),
      getColumn: (colId: string) => { return colLookup[colId] },
      getColumns: () => { return cols },
      refreshCells: vi.fn(),
    } as unknown as GridApi
  }

  function getParams (
      cols: Array<Column>,
      colIdx: number
  ): NodeUpdateParams {
    mockGridApi = getMockGridApi(cols)
    return {
      api: mockGridApi,
      assayMode: false,
      column: cols[colIdx]!,
      createNew: true,
      nameCellData: null,
      rowNode: mockRowNode,
      tableUuid: STUDY_UUID
    }
  }

  beforeEach(() => {
    vi.clearAllMocks()
    setActivePinia(createPinia())
    const tableStore = useTableStore()
    // NOTE: Set up tableStore.gridApi.study in tests when testing assay
    tableStore.sampleColId = 'col2'
    tableStore.sampleIdx = 2
    tableStore.sourceColSpan = 1
    mockRowNode = getMockRowNode() as IRowNode
  })

  test('update new node', async () => {
    const cd = getMockColDef()
    const cd2 = getMockColDef()
    cd2.cellEditorParams.fieldHeader.type = EDIT_HEADER_TYPE_CHAR
    const cols = [
      getMockCol('col2', '2', cd),
      getMockCol('col3', '2', cd2) // Same group
    ]
    const params = getParams(cols, 0)

    updateNode(params)
    expect(mockRowNode.setDataValue).toHaveBeenCalledTimes(1)
    const valueParams = copy(emptyValueParams) as SheetTableCellData
    valueParams.editable = undefined // Not defined for new init
    valueParams.newInit = false
    expect(mockRowNode.setDataValue).toHaveBeenCalledWith('col3', valueParams)
    expect(mockGridApi.refreshCells).toHaveBeenCalledTimes(1)
    expect(mockGridApi.refreshCells).toHaveBeenCalledWith(
      { columns: ['rowEdit'], rowNodes: [params.rowNode], force: true })
  })

  test('update existing node', async () => {
    const cd = getMockColDef()
    const cd2 = getMockColDef()
    cd2.cellEditorParams.fieldHeader.type = EDIT_HEADER_TYPE_CHAR
    const cols = [
      getMockCol('col2', '2', cd),
      getMockCol('col3', '2', cd2) // Same group
    ]

    const params = getParams(cols, 0)
    params.createNew = false
    params.nameCellData = { value: '0814-N1' }
    mockGridApi.forEachNode = getMockForEachNode([{
      data: {
        'col2': { value: '0814-N1' },
        'col3': { value: 'test' }
      }
    }])

    updateNode(params)
    expect(mockRowNode.setDataValue).toHaveBeenCalledTimes(1)
    const valueParams = { editable: true, newInit: false, value: 'test' }
    expect(mockRowNode.setDataValue).toHaveBeenCalledWith('col3', valueParams)
  })

  test('update assay node from sample name column', async () => {
    const tableStore = useTableStore()
    const cd = getMockColDef()
    const cd2 = getMockColDef()
    cd2.cellEditorParams.fieldHeader.type = EDIT_HEADER_TYPE_CHAR
    const cols = [getMockCol('col2', '2', cd), getMockCol('col3', '2', cd2)]

    const params = getParams(cols, 0)
    params.assayMode = true
    params.createNew = false
    params.nameCellData = { value: '0814-N1' }
    mockGridApi.forEachNode = getMockForEachNode([{
      data: {
        'col1': { value: '0814' },
        'col2': { value: '0814-N1' },
        'col3': { value: 'test' }
      }
    }])
    tableStore.gridApi.study = mockGridApi

    updateNode(params)
    expect(mockRowNode.setDataValue).toHaveBeenCalledTimes(2)
    // Both source node and current sample node should get filled
    const valueParams = {
      editable: true, newInit: false, newRow: true, value: '0814' }
    expect(mockRowNode.setDataValue).toHaveBeenCalledWith('col1', valueParams)
    const valueParams2 = { editable: true, newInit: false, value: 'test' }
    expect(mockRowNode.setDataValue).toHaveBeenCalledWith('col3', valueParams2)
  })

  test('update protocol UUID for named process node', async () => {
    const cd = getMockColDef()
    cd.cellEditorParams.fieldHeader.type = EDIT_HEADER_TYPE_PROTOCOL
    const cd2 = getMockColDef()
    cd2.cellEditorParams.fieldHeader.type = EDIT_HEADER_TYPE_PROCESS
    const cols = [getMockCol('col2', '2', cd), getMockCol('col3', '2', cd2)]

    const params = getParams(cols, 1)
    mockRowNode.data['col3'] = { value: '', uuid: TMP_UUID }
    expect(mockRowNode.data['col2'].uuid).toBe('') // No UUID yet

    updateNode(params)
    expect(mockRowNode.setDataValue).toHaveBeenCalledTimes(0)
    // UUID of previous protocol should be updated
    expect(mockRowNode.data['col2'].uuid).toBe(TMP_UUID)
  })

  test('skip UUID update for non-protocol cell for named process', async () => {
    const cd = getMockColDef()
    expect(
      cd.cellEditorParams.fieldHeader.type).not.toBe(EDIT_HEADER_TYPE_PROTOCOL)
    const cd2 = getMockColDef()
    cd2.cellEditorParams.fieldHeader.type = EDIT_HEADER_TYPE_PROCESS
    const cols = [getMockCol('col2', '2', cd), getMockCol('col3', '2', cd2)]

    const params = getParams(cols, 1)
    mockRowNode.data['col3'] = { value: '', uuid: TMP_UUID }
    expect(mockRowNode.data['col2'].uuid).toBe('') // No UUID yet

    updateNode(params)
    expect(mockRowNode.setDataValue).toHaveBeenCalledTimes(0)
    expect(mockRowNode.data['col2'].uuid).toBe('') // UUID should be unchanged
  })
})
