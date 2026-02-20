// Helpers for SODAR ag-grid setup

import {
  themeQuartz,
  type GridOptions,
  type ValueGetterParams
} from 'ag-grid-community'
import { type SheetTableCellData } from '@/types.ts'

const sodarTheme = themeQuartz.withParams({
  browserColorScheme: 'light',
  cellHorizontalPadding: 10,
  columnBorder: true,
  fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, ' +
    '"Helvetica Neue", Arial, "Noto Sans", sans-serif',
  fontSize: 16,
  headerFontSize: 16,
  headerFontWeight: 'bold',
  headerColumnBorder: true,
  headerColumnBorderHeight: '100%',
  headerColumnResizeHandleColor: 'rgba(0, 0, 0, 0)',
  headerColumnResizeHandleHeight: '100%',
  rowHoverColor: 'rgba(0, 0, 0, 0)', // TODO: Better way to disable hover?
  wrapperBorder: { width: 0 },
  wrapperBorderRadius: 0
})

// Initialize ag-grid gridOptions
export function initGridOptions (
  context: object,
  editMode: boolean
): GridOptions {
  return {
    animateRows: false,
    context: context,
    // debug: true,
    defaultColDef: {
      editable: false,
      resizable: true,
      sortable: !editMode
    },
    headerHeight: 38,
    pagination: false,
    rowHeight: 38,
    singleClickEdit: false,
    suppressColumnMoveAnimation: true,
    suppressColumnVirtualisation: false,
    suppressHeaderFocus: true,
    suppressMovableColumns: true,
    theme: sodarTheme,
  }
}

// Get flat value for comparator
function getFlatValue (
  value: number | object | string
): number | object | string {
  if (Array.isArray(value) && value.length > 0) {
    if (typeof value[0] === 'object' && 'name' in value[0]) {
      return value.map(d => d.name).join(';')
    } else return value.join(';')
  }
  return value
}

// Compare data cell values
export function compareDataCellValues (
  dataA: SheetTableCellData,
  dataB: SheetTableCellData
): number {
  let valueA = dataA.value
  let valueB = dataB.value
  if (['UNIT', 'NUMERIC'].includes(dataA.colType)) {
    const vA = valueA as string
    const vB = valueB as string
    if (!isNaN(parseFloat(vA)) && !isNaN(parseFloat(vB))) {
      return parseFloat(vA) - parseFloat(vB)
    }
  }
  valueA = getFlatValue(valueA) as string
  valueB = getFlatValue(valueB) as string
  return valueA.localeCompare(valueB)
}

// Custom filter value for data cells (fix for #686)
export function getDataCellFilterValue (
  params: ValueGetterParams
): number | object | string {
  return getFlatValue(params.data[params.column.getColId() as string].value)
}
