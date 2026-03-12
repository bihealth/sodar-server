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
} from '@/gridUtils.ts'
import {
  type SodarContext,
  type SodarContextAssay,
  type SodarContextLinkLabel
} from '@/stores/appStore.ts'
import {
  type SheetTableCellData,
  type SheetTableFieldHeader,
  type SheetTableOntologyRef,
  type StudyDisplayConfig,
  type StudyRenderTable,
  type StudyShortcuts,
} from '@/types.ts'

import { copy } from '../testUtils.ts'
import { sodarContext } from '../data/sodarContext.ts'
import studyTables from '../data/studyTables.json'
import studyShortcutsGermline from '../data/studyShortcutsGermline.json'
import { ASSAY_PATH, ASSAY_UUID, STUDY_UUID } from '../testConstants.ts'

const extColType: string = 'EXTERNAL_LINKS'

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
    const res: Array<number> = getColWidth(1, 'NAME', 12, 2, 50, 250)
    expect(res).toEqual([12 * 10 + 25, 50])
  })

  test('get widths with calculated width higher than maximum', async () => {
    const res: Array<number> = getColWidth(1, 'NAME', 24, 2, 50, 250)
    expect(res).toEqual([250, 50]) // Should be capped to max width
  })

  test('get widths with calculated width lower than minimum', async () => {
    const res: Array<number> = getColWidth(1, 'NAME', 1, 2, 50, 250)
    expect(res).toEqual([50, 50]) // Column and minimum width should be equal
  })

  test('get widths with last visible column', async () => {
    const res: Array<number> = getColWidth(2, 'NAME', 24, 2, 50, 250)
    expect(res).toEqual([265, 50]) // We can exceed max width
  })

  test('get widths with external links column type', async () => {
    const res: Array<number> = getColWidth(1, extColType, 2, 2, 50, 250)
    expect(res).toEqual([2 * 120, 150])
  })

  test('get widths with external links and width > max', async () => {
    const res: Array<number> = getColWidth(1, extColType, 4, 2, 50, 250)
    expect(res).toEqual([250, 150])
  })

  test('get widths with external links and width < min', async () => {
    const res: Array<number> = getColWidth(1, extColType, 0, 2, 50, 250)
    expect(res).toEqual([150, 150])
  })

  test('get widths with external links and last visible column', async () => {
    const res: Array<number> = getColWidth(2, extColType, 3, 2, 50, 250)
    expect(res).toEqual([360, 150])
  })
})

describe('getFieldHeader()', () => {
  const fieldHeader = {
    value: 'Organism',
    col_type: 'ONTOLOGY'
  } as SheetTableFieldHeader
  const linkLabels = sodarContext.external_link_labels as {
    [key: string]: string | SodarContextLinkLabel }

  test('get field header', async () => {
    const res: ColDef = getFieldHeader(
      fieldHeader,  // fieldHeader
      2,            // fieldIdx
      'left',       // colAlign
      250,          // colWidth
      50,           // minColWidth
      true,         // fieldEditable
      true,         // fieldVisible
      false,        // editMode
      linkLabels    // externalLinkLabels
    )
    expect(res.headerName).toBe('Organism')
    expect(res.field).toBe('col2')
    expect(res.width).toBe(250)
    expect(res.minWidth).toBe(50)
    expect(res.hide).toBe(false)
    expect(res.cellRendererParams.colType).toBe('ONTOLOGY')
    expect(res.cellRendererParams.editMode).toBe(false)
    expect(res.cellRendererParams.fieldEditable).toBe(true)
    expect(res.cellRendererParams.linkLabels).toBe(linkLabels)
    expect(res.cellClass).toContain('text-left')
    expect(res.cellClass).not.toContain('text-right')
  })

  test('get field header with fieldVisible=false', async () => {
    const res = getFieldHeader(
      fieldHeader,
      2,
      'left',
      250,
      50,
      true,
      false, // fieldVisible
      false,
      linkLabels
    )
    expect(res.hide).toBe(true)
  })

  test('get field header with right aligned content', async () => {
    const res = getFieldHeader(
      fieldHeader,
      2,
      'right', // colWidth
      250,
      50,
      true,
      true,
      false,
      linkLabels
    )
    expect(res.cellClass).not.toContain('text-left')
    expect(res.cellClass).toContain('text-right')
  })

  // TODO: Test editMode differences once edit mode is implemented
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
    const res: boolean = getFieldVisibility(
      STUDY_UUID, // tableUuid
      0, // topIdx
      false, // assayMode
      true, // studySection
      studyHeader, // fieldHeader
      true, // fieldEditable
      1, // colValues
      displayConfig // studyDisplayConfig
    )
    expect(res).toBe(true)
  })

  test('get visibility with display config set false', async () => {
    // @ts-expect-error Timeboxing
    displayConfig.nodes[0].fields[1].visible = false
    const res = getFieldVisibility(
      STUDY_UUID,
      0,
      false,
      true,
      studyHeader,
      true,
      1,
      displayConfig
    )
    expect(res).toBe(false)
  })

  test('get visibility with config=true and colValues=0', async () => {
    const res = getFieldVisibility(
      STUDY_UUID,
      0,
      false,
      true,
      studyHeader,
      true,
      0, // colValues
      displayConfig
    )
    expect(res).toBe(true) // Should still return true
  })

  test('get visibility with no config', async () => {
    const res: boolean = getFieldVisibility(
      STUDY_UUID,
      0,
      false,
      true,
      studyHeader,
      true,
      1,
      null // studyDisplayConfig
    )
    expect(res).toBe(true) // Should still return true
  })

  test('get visibility with no config and colValues=0', async () => {
    const res = getFieldVisibility(
      STUDY_UUID,
      0,
      false,
      true,
      studyHeader,
      true, // fieldEditable
      0, // colValues
      null // studyDisplayConfig
    )
    expect(res).toBe(true) // Should still be true due to fieldEditable=true
  })

  test(
      'get visibility with no config, colValues=0 and fieldEditable=false',
      async () => {
    const res = getFieldVisibility(
      STUDY_UUID,
      0,
      false,
      true,
      studyHeader,
      false, // fieldEditable
      0, // colValues
      null // studyDisplayConfig
    )
    expect(res).toBe(false)
  })

  test('get assay field visibility', async () => {
    // @ts-expect-error Timeboxing
    expect(displayConfig.assays[ASSAY_UUID].nodes[5].fields[1].visible).toBe(
      true)
    const res = getFieldVisibility(
      ASSAY_UUID,
      5,
      true, // assayMode
      false, // studySection
      assayHeader,
      true,
      1,
      displayConfig
    )
    expect(res).toBe(true)
  })

  test('get assay field with display config set false', async () => {
    // @ts-expect-error Timeboxing
    displayConfig.assays[ASSAY_UUID].nodes[5].fields[1].visible = false
    const res = getFieldVisibility(
      ASSAY_UUID,
      5,
      true,
      false,
      assayHeader,
      true,
      1,
      displayConfig
    )
    expect(res).toBe(false)
  })

  test('get assay field with config=true and colValues=0', async () => {
    const res = getFieldVisibility(
      ASSAY_UUID,
      5,
      true,
      false,
      assayHeader,
      true,
      0, // colValues
      displayConfig
    )
    expect(res).toBe(true) // Should still return true
  })

  test('get assay field with no config', async () => {
    const res = getFieldVisibility(
      ASSAY_UUID,
      5,
      true,
      false,
      assayHeader,
      true,
      1, // colValues
      null // studyDisplayConfig
    )
    expect(res).toBe(true) // Should still return true
  })

  test('get assay field with no config and colValues=0', async () => {
    const res = getFieldVisibility(
      ASSAY_UUID,
      5,
      true,
      false,
      assayHeader,
      true,
      0, // colValues
      null // studyDisplayConfig
    )
    expect(res).toBe(true) // Should still be true due to fieldEditable=true
  })

  test(
      'get assay field with no config, colValues=0 and fieldEditable=false',
      async () => {
    const res = getFieldVisibility(
      ASSAY_UUID,
      5,
      true,
      false,
      assayHeader,
      false, // fieldEditable
      0, // colValues
      null // studyDisplayConfig
    )
    expect(res).toBe(false)
  })

  test('get assay study section field visibility', async () => {
    // @ts-expect-error Timeboxing
    expect(displayConfig.assays[ASSAY_UUID].nodes[0].fields[1].visible).toBe(
      false)
    const res = getFieldVisibility(
      ASSAY_UUID,
      0,
      true,
      true, // studySection
      studyHeader,
      true,
      1,
      displayConfig
    )
    expect(res).toBe(false)
  })

  test('get assay study section field visibility', async () => {
    // @ts-expect-error Timeboxing
    expect(displayConfig.assays[ASSAY_UUID].nodes[0].fields[1].visible).toBe(
      false)
    const res = getFieldVisibility(
      ASSAY_UUID,
      0,
      true,
      true, // studySection
      studyHeader,
      true,
      1,
      displayConfig
    )
    expect(res).toBe(false)
  })

  test('get assay study section field with config=true', async () => {
    // @ts-expect-error Timeboxing
    displayConfig.assays[ASSAY_UUID].nodes[0].fields[1].visible = true
    const res = getFieldVisibility(
      ASSAY_UUID,
      0,
      true,
      true,
      studyHeader,
      true,
      1,
      displayConfig
    )
    expect(res).toBe(true)
  })

  test('get assay study section field with no config', async () => {
    const res = getFieldVisibility(
      ASSAY_UUID,
      0,
      true,
      true, // studySection
      studyHeader,
      true,
      1, // colValues
      null // studyDisplayConfig
    )
    expect(res).toBe(false) // Should be false despite colValues=1
  })

    test('get assay study section name field with no config', async () => {
    const res = getFieldVisibility(
      ASSAY_UUID,
      0,
      true,
      true,
      { name: 'Name', value: 'Name'} as SheetTableFieldHeader,
      true,
      1, // colValues
      null // studyDisplayConfig
    )
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
    const dataA = { colType: 'NAME', value: 'a' } as SheetTableCellData
    const dataB = { colType: 'NAME', value: 'b' } as SheetTableCellData
    const res = compareDataCellValues(dataA, dataB)
    expect(res).toBe(-1)
  })

  test('compare data cells in inverse order', async () => {
    const dataA = { colType: 'NAME', value: 'a' } as SheetTableCellData
    const dataB = { colType: 'NAME', value: 'b' } as SheetTableCellData
    const res = compareDataCellValues(dataB, dataA)
    expect(res).toBe(1)
  })

  test('compare data cells with numeric values', async () => {
    const dataA = { colType: 'NUMERIC', value: '1' } as SheetTableCellData
    const dataB = { colType: 'NUMERIC', value: '2' } as SheetTableCellData
    const res = compareDataCellValues(dataA, dataB)
    expect(res).toBe(-1)
  })

  test('compare data cells with numeric values in inverse order', async () => {
    const dataA = { colType: 'NUMERIC', value: '1' } as SheetTableCellData
    const dataB = { colType: 'NUMERIC', value: '2' } as SheetTableCellData
    const res = compareDataCellValues(dataB, dataA)
    expect(res).toBe(1)
  })

  test('compare data cells with object values', async () => {
    const dataA = {
      colType: 'ONTOLOGY', value: [{ name: 'a' } as SheetTableOntologyRef]
    } as SheetTableCellData
    const dataB = {
      colType: 'ONTOLOGY', value: [{ name: 'b' } as SheetTableOntologyRef]
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

// TODO: Test buildColDef() once edit mode is supported
// TODO: Test buildRowData() once edit mode is supported
// TODO: Test getRowEditHeaderGroup() once edit mode is supported
// TODO: Test getFieldEditConfig() once edit mode is supported
