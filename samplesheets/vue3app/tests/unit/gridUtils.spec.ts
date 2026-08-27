import { type TemplateRef } from 'vue'
import { beforeEach, describe, expect, test } from 'vitest'
import {
  type ColDef,
  type ColGroupDef,
  type ValueGetterParams
} from 'ag-grid-community'

import {
  compareDataCellValues,
  getAssayIrodsHeaderGroup,
  getColWidth,
  getDataCellFilterValue,
  getFieldHeader,
  getFieldVisibility,
  getFlatValue,
  getStudyShortcutHeaderGroup
} from '@/utils/gridUtils.ts'
import {
  type SheetTableCellData,
  type SheetTableFieldHeader,
  type SheetTableOntologyRef,
  type SodarContext,
  type SodarContextAssay,
  type SodarContextLinkLabel,
  type StudyDisplayConfig,
  type StudyRenderTable,
  type StudyShortcuts,
} from '@/types.ts'
import {
  EDIT_COL_TYPE_EXT_LINKS,
  EDIT_COL_TYPE_NAME,
  EDIT_COL_TYPE_NUMERIC,
  EDIT_COL_TYPE_ONTOLOGY
} from '@/constants.ts'

import { copy } from '../testUtils.ts'
import { sodarContext } from '../data/sodarContext.ts'
import studyTables from '../data/studyTables.json'
import studyShortcutsGermline from '../data/studyShortcutsGermline.json'
import { ASSAY_PATH, ASSAY_UUID, STUDY_UUID } from '../testConstants.ts'

// Tests -----------------------------------------------------------------------

describe('getAssayIrodsHeaderGroup()', () => {
  let context: SodarContext
  let assayContext: SodarContextAssay
  const mockModal = {} as TemplateRef

  beforeEach(() => {
    context = copy(sodarContext) as SodarContext
    assayContext = copy(
      context.studies[STUDY_UUID]!.assays[ASSAY_UUID] as SodarContextAssay
    ) as SodarContextAssay
  })

  test('get assay iRODS header group with default params', async () => {
    expect(context.irods_backend_enabled).toBe(true)
    expect(context.irods_webdav_url).toBe('https://davrods.local')
    expect(assayContext.irods_path).toBe(ASSAY_PATH)
    expect(context.irods_status).toBe(true)

    const res: ColGroupDef = getAssayIrodsHeaderGroup(
      context, assayContext, mockModal)
    const field = res.children[0] as ColDef
    expect(field.cellRendererParams.irodsBackendEnabled).toBe(true)
    expect(field.cellRendererParams.irodsWebdavUrl).toBe(
      'https://davrods.local')
    expect(field.cellRendererParams.assayIrodsPath).toBe(ASSAY_PATH)
    expect(field.cellRendererParams.irodsStatus).toBe(true)
  })

  test('get assay iRODS header group with modified params', async () => {
    context.irods_backend_enabled = false
    context.irods_webdav_url = 'https://sodar.example.org'
    assayContext.irods_path = ASSAY_PATH + '/xxx'
    context.irods_status = false

    const res: ColGroupDef = getAssayIrodsHeaderGroup(
      context, assayContext, mockModal)
    const field = res.children[0] as ColDef
    expect(field.cellRendererParams.irodsBackendEnabled).toBe(false)
    expect(field.cellRendererParams.irodsWebdavUrl).toBe(
      'https://sodar.example.org')
    expect(field.cellRendererParams.assayIrodsPath).toBe(ASSAY_PATH + '/xxx')
    expect(field.cellRendererParams.irodsStatus).toBe(false)
  })
})

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

describe('getFieldHeader()', () => {
  const fieldHeader = {
    value: 'Organism',
    col_type: EDIT_COL_TYPE_ONTOLOGY
  } as SheetTableFieldHeader
  const linkLabels = sodarContext.external_link_labels as {
    [key: string]: string | SodarContextLinkLabel }

  test('get field header', async () => {
    const res: ColDef = getFieldHeader({
      colAlign: 'left',
      colWidth: 250,
      editMode: false,
      externalLinkLabels: linkLabels,
      fieldEditable: true,
      fieldHeader: fieldHeader,
      fieldIdx: 2,
      fieldVisible: true,
      minColWidth: 50,
    })
    expect(res.headerName).toBe('Organism')
    expect(res.field).toBe('col2')
    expect(res.width).toBe(250)
    expect(res.minWidth).toBe(50)
    expect(res.hide).toBe(false)
    expect(res.cellRendererParams.colType).toBe(EDIT_COL_TYPE_ONTOLOGY)
    expect(res.cellRendererParams.editMode).toBe(false)
    expect(res.cellRendererParams.fieldEditable).toBe(true)
    expect(res.cellRendererParams.linkLabels).toBe(linkLabels)
    expect(res.cellClass).toContain('text-left')
    expect(res.cellClass).not.toContain('text-right')
  })

  test('get field header with fieldVisible=false', async () => {
    const res: ColDef = getFieldHeader({
      colAlign: 'left',
      colWidth: 250,
      editMode: false,
      externalLinkLabels: linkLabels,
      fieldEditable: true,
      fieldHeader: fieldHeader,
      fieldIdx: 2, // Updated
      fieldVisible: false,
      minColWidth: 50,
    })
    expect(res.hide).toBe(true)
  })

  test('get field header with right aligned content', async () => {
    const res: ColDef = getFieldHeader({
      colAlign: 'right',
      colWidth: 250,
      editMode: false, // Updated
      externalLinkLabels: linkLabels,
      fieldEditable: true,
      fieldHeader: fieldHeader,
      fieldIdx: 2,
      fieldVisible: true,
      minColWidth: 50,
    })
    expect(res.cellClass).not.toContain('text-left')
    expect(res.cellClass).toContain('text-right')
  })

  // TODO: Test editMode
})

describe('getFieldVisibility()', () => {
  let displayConfig: StudyDisplayConfig
  const studyHeader = {
    name: 'organism',
    value: 'Organism'
  } as SheetTableFieldHeader
  const assayHeader = {
    name: 'Assay Name',
    value: 'Assay Name'
  } as SheetTableFieldHeader
  beforeEach(() => {
    displayConfig = copy(studyTables.display_config) as StudyDisplayConfig
  })

  test('get study field visibility', async () => {
    // @ts-expect-error Timeboxing
    expect(displayConfig.nodes[0].fields[1].visible).toBe(true)
    const res = getFieldVisibility({
      tableUuid: STUDY_UUID,
      topIdx: 0,
      assayMode: false,
      studySection: true,
      fieldHeader: studyHeader,
      fieldEditable: true,
      colValues: 1,
      studyDisplayConfig: displayConfig,
    })
    expect(res).toBe(true)
  })

  test('get visibility with display config set false', async () => {
    // @ts-expect-error Timeboxing
    displayConfig.nodes[0].fields[1].visible = false
    const res = getFieldVisibility({
      tableUuid: STUDY_UUID,
      topIdx: 0,
      assayMode: false,
      studySection: true,
      fieldHeader: studyHeader,
      fieldEditable: true,
      colValues: 1,
      studyDisplayConfig: displayConfig,
    })
    expect(res).toBe(false)
  })

  test('get visibility with config=true and colValues=0', async () => {
    const res = getFieldVisibility({
      tableUuid: STUDY_UUID,
      topIdx: 0,
      assayMode: false,
      studySection: true,
      fieldHeader: studyHeader,
      fieldEditable: true,
      colValues: 0, // Updated
      studyDisplayConfig: displayConfig,
    })
    expect(res).toBe(true) // Should still return true
  })

  test('get visibility with no config', async () => {
    const res = getFieldVisibility({
      tableUuid: STUDY_UUID,
      topIdx: 0,
      assayMode: false,
      studySection: true,
      fieldHeader: studyHeader,
      fieldEditable: true,
      colValues: 1,
      studyDisplayConfig: null, // Updated
    })
    expect(res).toBe(true) // Should still return true
  })

  test('get visibility with no config and colValues=0', async () => {
    const res = getFieldVisibility({
      tableUuid: STUDY_UUID,
      topIdx: 0,
      assayMode: false,
      studySection: true,
      fieldHeader: studyHeader,
      fieldEditable: true,
      colValues: 0, // Updated
      studyDisplayConfig: null, // Updated
    })
    expect(res).toBe(true) // Should still be true due to fieldEditable=true
  })

  test(
      'get visibility with no config, colValues=0 and fieldEditable=false',
      async () => {
    const res = getFieldVisibility({
      tableUuid: STUDY_UUID,
      topIdx: 0,
      assayMode: false,
      studySection: true,
      fieldHeader: studyHeader,
      fieldEditable: false, // Updated
      colValues: 0, // Updated
      studyDisplayConfig: null, // Updated
    })
    expect(res).toBe(false)
  })

  test('get assay field visibility', async () => {
    // @ts-expect-error Timeboxing
    expect(displayConfig.assays[ASSAY_UUID].nodes[5].fields[1].visible).toBe(
      true)
    const res = getFieldVisibility({
      tableUuid: ASSAY_UUID,
      topIdx: 5,
      assayMode: true,
      studySection: false,
      fieldHeader: assayHeader,
      fieldEditable: true,
      colValues: 1,
      studyDisplayConfig: displayConfig,
    })
    expect(res).toBe(true)
  })

  test('get assay field with display config set false', async () => {
    // @ts-expect-error Timeboxing
    displayConfig.assays[ASSAY_UUID].nodes[5].fields[1].visible = false
    const res = getFieldVisibility({
      tableUuid: ASSAY_UUID,
      topIdx: 5,
      assayMode: true,
      studySection: false,
      fieldHeader: assayHeader,
      fieldEditable: true,
      colValues: 1,
      studyDisplayConfig: displayConfig,
    })
    expect(res).toBe(false)
  })

  test('get assay field with config=true and colValues=0', async () => {
    const res = getFieldVisibility({
      tableUuid: ASSAY_UUID,
      topIdx: 5,
      assayMode: true,
      studySection: false,
      fieldHeader: assayHeader,
      fieldEditable: true,
      colValues: 0, // Updated
      studyDisplayConfig: displayConfig,
    })
    expect(res).toBe(true) // Should still return true
  })

  test('get assay field with no config', async () => {
    const res = getFieldVisibility({
      tableUuid: ASSAY_UUID,
      topIdx: 5,
      assayMode: true,
      studySection: false,
      fieldHeader: assayHeader,
      fieldEditable: true,
      colValues: 1,
      studyDisplayConfig: null, // Updated
    })
    expect(res).toBe(true) // Should still return true
  })

  test('get assay field with no config and colValues=0', async () => {
    const res = getFieldVisibility({
      tableUuid: ASSAY_UUID,
      topIdx: 5,
      assayMode: true,
      studySection: false,
      fieldHeader: assayHeader,
      fieldEditable: true,
      colValues: 0, // Updated
      studyDisplayConfig: null, // Updated
    })
    expect(res).toBe(true) // Should still be true due to fieldEditable=true
  })

  test(
      'get assay field with no config, colValues=0 and fieldEditable=false',
      async () => {
    const res = getFieldVisibility({
      tableUuid: ASSAY_UUID,
      topIdx: 5,
      assayMode: true,
      studySection: false,
      fieldHeader: assayHeader,
      fieldEditable: false, // Updated
      colValues: 0, // Updated
      studyDisplayConfig: null, // Updated
    })
    expect(res).toBe(false)
  })

  test('get assay study section field visibility', async () => {
    // @ts-expect-error Timeboxing
    expect(displayConfig.assays[ASSAY_UUID].nodes[0].fields[1].visible).toBe(
      false)
    const res = getFieldVisibility({
      tableUuid: ASSAY_UUID,
      topIdx: 0,
      assayMode: true,
      studySection: true,
      fieldHeader: studyHeader,
      fieldEditable: true,
      colValues: 1,
      studyDisplayConfig: displayConfig,
    })
    expect(res).toBe(false)
  })

  test('get assay study section without display config', async () => {
    // @ts-expect-error Timeboxing
    expect(displayConfig.assays[ASSAY_UUID].nodes[0].fields[1].visible).toBe(
      false)
    const res = getFieldVisibility({
      tableUuid: ASSAY_UUID,
      topIdx: 0,
      assayMode: true,
      studySection: true,
      fieldHeader: studyHeader,
      fieldEditable: true,
      colValues: 1,
      studyDisplayConfig: displayConfig,
    })
    expect(res).toBe(false)
  })

  test('get assay study section field with config=true', async () => {
    // @ts-expect-error Timeboxing
    displayConfig.assays[ASSAY_UUID].nodes[0].fields[1].visible = true
    const res = getFieldVisibility({
      tableUuid: ASSAY_UUID,
      topIdx: 0,
      assayMode: true,
      studySection: true,
      fieldHeader: studyHeader,
      fieldEditable: true,
      colValues: 1,
      studyDisplayConfig: displayConfig,
    })
    expect(res).toBe(true)
  })

  test('get assay study section field with no config', async () => {
    const res = getFieldVisibility({
      tableUuid: ASSAY_UUID,
      topIdx: 0,
      assayMode: true,
      studySection: true,
      fieldHeader: studyHeader,
      fieldEditable: true,
      colValues: 1,
      studyDisplayConfig: null, // Updated
    })
    expect(res).toBe(false) // Should be false despite colValues=1
  })

  test('get assay study section name field with no config', async () => {
    const res = getFieldVisibility({
      tableUuid: ASSAY_UUID,
      topIdx: 0,
      assayMode: true,
      studySection: true,
      fieldHeader: { name: 'Name', value: 'Name'} as SheetTableFieldHeader,
      fieldEditable: true,
      colValues: 1,
      studyDisplayConfig: null, // Updated
    })
    expect(res).toBe(true) // Name field should still be visible
  })
})

describe('getStudyShortcutHeaderGroup()', () => {
  let table: StudyRenderTable
  const mockModal = {} as TemplateRef

  beforeEach(() => {
    table = copy(studyTables.tables.study) as StudyRenderTable
    table.shortcuts = copy(studyShortcutsGermline) as unknown as StudyShortcuts
  })

  test('return study shortcut header group', async () => {
    const res: ColGroupDef = getStudyShortcutHeaderGroup(table, mockModal)
    expect(res.headerName).toBe('Links')
    const field = res.children[0] as ColDef
    expect(field.cellRendererParams.schema).toBe(table.shortcuts?.schema)
    expect(field.cellRendererParams.modalRef).toBe(mockModal)
    expect(Object.keys(table.shortcuts?.schema || {}).length).toBe(2)
    expect(field.width).toBe(80) // 2 * 40
  })
})

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

// TODO: Test buildColDef()
// TODO: Test buildRowData()
// TODO: Test getRowEditHeaderGroup()
// TODO: Test getFieldEditConfig()
