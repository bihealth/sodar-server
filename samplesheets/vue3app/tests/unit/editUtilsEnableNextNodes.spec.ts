import { beforeEach, describe, expect, test, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import {
  type ColDef,
  type Column,
  type GridApi,
  type IRowNode
} from 'ag-grid-community'

import { enableNextNodes } from '@/utils/editUtils.ts'
import { useAppStore } from '@/stores/appStore.ts'
import { useEditStore } from '@/stores/editStore.ts'
import {
  type NodeEnableParams,
  type SheetTableCellData,
  type StudyEditContextProtocol
} from '@/types.ts'
import {
  DB_OBJ_CLASS_MATERIAL,
  DB_OBJ_CLASS_PROCESS,
  EDIT_COL_TYPE_NAME,
  EDIT_FORMAT_PROTOCOL,
  EDIT_HEADER_TYPE_CHAR,
  EDIT_HEADER_TYPE_NAME,
  EDIT_HEADER_TYPE_PROCESS,
  EDIT_HEADER_TYPE_PROTOCOL,
  EDIT_ITEM_TYPE_SAMPLE,
  EDIT_ITEM_TYPE_DATA,
} from '@/constants.ts'

import { copy } from '../testUtils.ts'
import { STUDY_UUID, TMP_UUID, TMP_UUID2 } from '../testConstants.ts'

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
const fieldHeaderProcess = {
  type: EDIT_HEADER_TYPE_PROCESS,
  obj_cls: DB_OBJ_CLASS_PROCESS
}
const fieldHeaderProtocol = {
  type: EDIT_HEADER_TYPE_PROTOCOL,
  obj_cls: DB_OBJ_CLASS_PROCESS
}
let mockRowNode: IRowNode
const protocols: Array<StudyEditContextProtocol> = [
  { name: 'sample collection', uuid: TMP_UUID },
  { name: 'library preparation', uuid: TMP_UUID2 }
]
const sourceUuid = TMP_UUID

// Tests for enableNextNodes() -------------------------------------------------

describe('enableNextNodes()', () => {
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
        return { getGroupId: () => { return groupId } } }
    } as Column
  }

  function getMockGridApi (cols: Array<Column>): GridApi {
    // Add dummy 1st and last column and pre-filled source name to columns
    cols = [getMockCol('col0', '0'), getMockCol('col1', '1')].concat(cols)
    cols.push(getMockCol('col999', '999'))
    // Get column lookup object for getColumn()
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

  function getParams (cols: Array<Column>): NodeEnableParams {
    return {
      api: getMockGridApi(cols),
      rowNode: mockRowNode,
      startIdx: 2,
      tableUuid: STUDY_UUID
    }
  }

  beforeEach(() => {
    vi.clearAllMocks()
    setActivePinia(createPinia())
    const appStore = useAppStore()
    appStore.currentStudyUuid = STUDY_UUID
    const editStore = useEditStore()
    editStore.editContext = {
      protocols: copy(protocols) as Array<StudyEditContextProtocol>,
      samples: {},
      sodar_ontologies: {}
    }
    mockRowNode = getMockRowNode() as IRowNode
    // NOTE: gridApi and params set up in test after mocking columns
  })

  test('enable sample name column', async () => {
    const cd = getMockColDef()
    cd.cellEditorParams.fieldHeader.item_type = EDIT_ITEM_TYPE_SAMPLE
    const cols = [getMockCol('col2', '2', cd)]
    expect(mockRowNode.setDataValue).not.toHaveBeenCalled()

    enableNextNodes(getParams(cols))
    expect(mockRowNode.setDataValue).toHaveBeenCalledTimes(1)
    expect(mockRowNode.setDataValue).toHaveBeenCalledWith(
      'col2', emptyValueParams)
  })

  test('enable sample name with default value', async () => {
    const cd = getMockColDef()
    cd.cellEditorParams.editConfigField = { default: '-N1' }
    cd.cellEditorParams.fieldHeader.item_type = EDIT_ITEM_TYPE_SAMPLE
    const cols = [getMockCol('col2', '2', cd)]

    enableNextNodes(getParams(cols))
    expect(mockRowNode.setDataValue).toHaveBeenCalledTimes(1)
    const valueParams = copy(emptyValueParams) as SheetTableCellData
    valueParams.newInit = false
    valueParams.value = '0814-N1'
    expect(mockRowNode.setDataValue).toHaveBeenCalledWith(
      'col2', valueParams)
    // NOTE: updateNode() called here, but we can't mock or spy on it
    //       (see https://github.com/vitest-dev/vitest/issues/6551)
  })

  test('enable data name column', async () => {
    const cd = getMockColDef()
    cd.cellEditorParams.fieldHeader.item_type = EDIT_ITEM_TYPE_DATA
    const cols = [getMockCol('col2', '2', cd)]

    enableNextNodes(getParams(cols))
    const valueParams = copy(emptyValueParams) as SheetTableCellData
    valueParams.newInit = false // Empty value is accepted for DATA
    expect(mockRowNode.setDataValue).toHaveBeenCalledTimes(1)
    expect(mockRowNode.setDataValue).toHaveBeenCalledWith('col2', valueParams)
  })

  test('enable data name with default value', async () => {
    const cd = getMockColDef()
    cd.cellEditorParams.editConfigField = { default: 'default.txt' }
    cd.cellEditorParams.fieldHeader.item_type = EDIT_ITEM_TYPE_DATA
    const cols = [getMockCol('col2', '2', cd)]

    enableNextNodes(getParams(cols))
    const valueParams = copy(emptyValueParams) as SheetTableCellData
    valueParams.newInit = false
    valueParams.value = 'default.txt' // Should have no prefix
    expect(mockRowNode.setDataValue).toHaveBeenCalledTimes(1)
    expect(mockRowNode.setDataValue).toHaveBeenCalledWith('col2', valueParams)
  })

  test('enable data name with another field in node', async () => {
    const cd = getMockColDef()
    cd.cellEditorParams.fieldHeader.item_type = EDIT_ITEM_TYPE_DATA
    const cd2 = getMockColDef()
    cd2.cellEditorParams.fieldHeader.type = EDIT_HEADER_TYPE_CHAR
    const cols = [
      getMockCol('col2', '2', cd),
      getMockCol('col3', '2', cd2) // Same groupId
    ]

    enableNextNodes(getParams(cols))
    const valueParams = copy(emptyValueParams) as SheetTableCellData
    valueParams.newInit = false
    expect(mockRowNode.setDataValue).toHaveBeenCalledTimes(2)
    expect(mockRowNode.setDataValue).toHaveBeenCalledWith('col2', valueParams)
    expect(mockRowNode.setDataValue).toHaveBeenCalledWith('col3', valueParams)
  })

  test('enable data name followed by another node', async () => {
    mockRowNode.data['col3'] = copy(emptyCellVal)
    const cd = getMockColDef()
    cd.cellEditorParams.fieldHeader.item_type = EDIT_ITEM_TYPE_DATA
    const cd2 = getMockColDef()
    const cols = [
      getMockCol('col2', '2', cd),
      getMockCol('col3', '3', cd2) // Different groupId
    ]

    enableNextNodes(getParams(cols))
    let valueParams = copy(emptyValueParams) as SheetTableCellData
    valueParams.newInit = false
    expect(mockRowNode.setDataValue).toHaveBeenCalledTimes(2)
    expect(mockRowNode.setDataValue).toHaveBeenCalledWith('col2', valueParams)
    // First cell in next node should have newInit = true
    valueParams = copy(emptyValueParams) as SheetTableCellData
    expect(mockRowNode.setDataValue).toHaveBeenCalledWith('col3', valueParams)
  })

  test('enable protocol column', async () => {
    const cd = getMockColDef()
    cd.cellEditorParams.fieldHeader = fieldHeaderProtocol
    const cols = [getMockCol('col2', '2', cd)]

    enableNextNodes(getParams(cols))
    expect(mockRowNode.setDataValue).toHaveBeenCalledTimes(1)
    expect(mockRowNode.setDataValue).toHaveBeenCalledWith(
      'col2', emptyValueParams)
  })

  test('enable protocol with default UUID', async () => {
    const cd = getMockColDef()
    cd.cellEditorParams.editConfigField = {
      default: TMP_UUID,
      format: EDIT_FORMAT_PROTOCOL
    }
    cd.cellEditorParams.fieldHeader = fieldHeaderProtocol
    const cols = [getMockCol('col2', '2', cd)]

    enableNextNodes(getParams(cols))
    expect(mockRowNode.setDataValue).toHaveBeenCalledTimes(1)
    const valueParams = copy(emptyValueParams) as SheetTableCellData
    valueParams.newInit = false
    valueParams.uuidRef = TMP_UUID
    valueParams.value = 'sample collection'
    expect(mockRowNode.setDataValue).toHaveBeenCalledWith(
      'col2', valueParams)
  })

  test('enable process name column', async () => {
    const cd = getMockColDef()
    cd.cellEditorParams.fieldHeader = fieldHeaderProcess
    const cols = [getMockCol('col2', '2', cd)]

    enableNextNodes(getParams(cols))
    expect(mockRowNode.setDataValue).toHaveBeenCalledTimes(1)
    expect(mockRowNode.setDataValue).toHaveBeenCalledWith(
      'col2', emptyValueParams)
  })

  test('enable process name with default', async () => {
    const cd = getMockColDef()
    cd.cellEditorParams.editConfigField = { default: '-P1' }
    cd.cellEditorParams.fieldHeader = fieldHeaderProcess
    const cols = [getMockCol('col2', '2', cd)]

    enableNextNodes(getParams(cols))
    expect(mockRowNode.setDataValue).toHaveBeenCalledTimes(1)
    const valueParams = copy(emptyValueParams) as SheetTableCellData
    valueParams.editable = true
    valueParams.newInit = false
    valueParams.value = '0814-P1'
    expect(mockRowNode.setDataValue).toHaveBeenCalledWith(
      'col2', valueParams)
  })
})
