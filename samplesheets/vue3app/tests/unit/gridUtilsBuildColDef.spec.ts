import { type TemplateRef } from 'vue'
import { beforeEach, describe, expect, test } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { type ColDef } from 'ag-grid-community'

import { useAppStore } from '@/stores/appStore.ts'
import { useTableStore } from '@/stores/tableStore.ts'

import {
  buildColDef,
  compareDataCellValues,
  getDataCellFilterValue,
  getRowNumHeaderGroup,
} from '@/utils/gridUtils.ts'
import {
  type AssayRenderTable,
  type ColDefBuildParams,
  type RenderTableData,
  type SodarContext,
  type StudyDisplayConfig,
  type StudyRenderTable,
} from '@/types.ts'
import { EDIT_COL_TYPE_NAME } from '@/constants.ts'

import { copy } from '../testUtils.ts'
import studyTables from '../data/studyTables.json'
import { sodarContext } from '../data/sodarContext.ts'
import { ASSAY_UUID, STUDY_UUID } from '../testConstants.ts'

// Test Data -------------------------------------------------------------------

const studyNodeLen = studyTables.tables.study.top_header.length

// Tests -----------------------------------------------------------------------

describe('buildColDef()', () => {
  function getParams (assayMode: boolean): ColDefBuildParams {
    let table: AssayRenderTable | StudyRenderTable
    let tableUuid: string
    if (!assayMode) {
      table = studyTables.tables.study
      tableUuid = STUDY_UUID
    } else {
      table = (studyTables as unknown as RenderTableData).tables.assays[
        ASSAY_UUID] as AssayRenderTable
      tableUuid = ASSAY_UUID
    }
    return {
      assayMode: assayMode,
      irodsDirModal: {} as TemplateRef,
      studyNodeLen: studyNodeLen,
      studyShortcutModal: {} as TemplateRef,
      table: table,
      tableUuid: tableUuid
    }
  }

  beforeEach(() => {
    setActivePinia(createPinia())
    const appStore = useAppStore()
    const tableStore = useTableStore()

    appStore.editMode = false
    appStore.sodarContext = copy(sodarContext) as SodarContext

    tableStore.studyDisplayConfig = copy(
      studyTables.display_config) as StudyDisplayConfig
    tableStore.sampleColId = 'col7'
  })

  test('build study columns', async () => {
    const res = buildColDef(getParams(false))
    // Includes rowNum group and extra source group in addition to study groups
    expect(res.length).toBe(studyNodeLen + 2)
    // TODO: Assert other general results here if needed
  })

  test('build rowNum group', async () => {
    const res = buildColDef(getParams(false))
    const group = res[0]!
    expect(group).toEqual(getRowNumHeaderGroup())
    expect((group.children[0] as ColDef).cellClass).not.toContain('bg-light')
  })

  test('build rowNum group in edit mode', async () => {
    const appStore = useAppStore()
    appStore.editMode = true
    const res = buildColDef(getParams(false))
    const group = res[0]!
    expect((group.children[0] as ColDef).cellClass).toContain('bg-light')
  })

  test('build source name group', async () => {
    const appStore = useAppStore()
    const res = buildColDef(getParams(false))
    const group = res[1]!
    expect(group.children.length).toBe(1)
    const col = group.children[0] as ColDef
    expect(col).toEqual(expect.objectContaining({
      cellClass: ['sodar-ss-data-cell', 'text-left'],
      cellDataType: 'object',
      cellRenderer: 'DataCellRenderer',
      cellRendererParams: {
        colType: EDIT_COL_TYPE_NAME,
        editMode: false,
        enableHover: false,
        fieldEditable: false,
        linkLabels: appStore.sodarContext!.external_link_labels
      },
      comparator: compareDataCellValues,
      context: {},
      field: 'col0',
      filterValueGetter: getDataCellFilterValue,
      headerClass: ['sodar-ss-data-header'],
      headerName: 'Name',
      hide: false,
      minWidth: 100,
      pinned: 'left',
      width: 100,
    })) // NOTE: Omitting valueFormatter
  })

  // TODO: Test main source group
  // TODO: Test other study groups and differences as needed
  // TODO: Test study groups with editMode
  // TODO: Test study shortcuts column
  // TODO: Test row edit column
  // TODO: Test build assay columns
  // TODO: Test assay column differences
})
