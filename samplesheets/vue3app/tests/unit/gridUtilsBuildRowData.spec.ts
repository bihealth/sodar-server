import { type TemplateRef } from 'vue'
import { beforeEach, describe, expect, test } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { type ColDef } from 'ag-grid-community'

import { useAppStore } from '@/stores/appStore.ts'
import { useTableStore } from '@/stores/tableStore.ts'

import {
  buildColDef,
  buildRowData,
  compareDataCellValues,
  getAssayIrodsHeaderGroup,
  getDataCellFilterValue,
  getRowEditHeaderGroup,
  getRowNumHeaderGroup,
  getStudyShortcutHeaderGroup,
} from '@/utils/gridUtils.ts'
import {
  type AssayRenderTable,
  type ColDefBuildParams,
  type RenderTableData,
  type SheetTableRowData,
  type SodarContext,
  type StudyDisplayConfig,
  type StudyEditConfig,
  type StudyRenderTable,
  type StudyShortcuts,
} from '@/types.ts'
import {
  DB_OBJ_CLASS_MATERIAL,
  EDIT_COL_TYPE_NAME,
  EDIT_HEADER_TYPE_NAME,
  EDIT_ITEM_TYPE_SOURCE
} from '@/constants.ts'

import { copy } from '../testUtils.ts'
import studyTables from '../data/studyTables.json'
import studyTablesEdit from '../data/studyTablesEdit.json'
import { sodarContext } from '../data/sodarContext.ts'
import studyShortcutsGermline from '../data/studyShortcutsGermline.json'
import { ASSAY_UUID, STUDY_PLUGIN_NAME, STUDY_UUID } from '../testConstants.ts'

// Test Data -------------------------------------------------------------------

/*
const assayNodeLen = (studyTables as unknown as RenderTableData).tables.assays![
  ASSAY_UUID]!.top_header.length
const studyNodeLen = studyTables.tables.study.top_header.length
*/
let tableData: RenderTableData

// Tests -----------------------------------------------------------------------

describe('buildRowData()', () => {
  function callBuildRowData (assayMode: boolean): Array<SheetTableRowData> {
    let table
    if (!assayMode) table = tableData.tables.study as StudyRenderTable
    else table = tableData.tables.assays[ASSAY_UUID] as AssayRenderTable
    return buildRowData(table, assayMode)
  }

  function setEditMode () {
    const appStore = useAppStore()
    const tableStore = useTableStore()
    tableData = copy(studyTablesEdit) as RenderTableData
    appStore.editMode = true
    tableStore.studyEditConfig = tableData.study_config as StudyEditConfig
  }

  beforeEach(() => {
    setActivePinia(createPinia())
    const appStore = useAppStore()
    const tableStore = useTableStore()

    // TODO: Copied from buildColDef() tests, verify which are needed
    appStore.currentStudyUuid = STUDY_UUID
    appStore.editMode = false
    appStore.sodarContext = copy(sodarContext) as SodarContext
    tableStore.studyDisplayConfig = copy(
      studyTables.display_config) as StudyDisplayConfig
    tableStore.sampleColId = 'col7'

    tableData = copy(studyTables) as RenderTableData
  })

  test('build study rows', async () => {
    const res = callBuildRowData(false)
    expect(res.length).toBe(5)
    // TODO: The usual assertions here
  })

  // TODO: Tests here
})
