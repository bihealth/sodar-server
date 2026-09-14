import { type TemplateRef } from 'vue'
import { beforeEach, describe, expect, test } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { type ColDef } from 'ag-grid-community'

import { useAppStore } from '@/stores/appStore.ts'
import { useTableStore } from '@/stores/tableStore.ts'

import {
  buildColDef,
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

const assayNodeLen = (studyTables as unknown as RenderTableData).tables.assays![
  ASSAY_UUID]!.top_header.length
const studyNodeLen = studyTables.tables.study.top_header.length
let tableData: RenderTableData

// Tests -----------------------------------------------------------------------

describe('buildColDef()', () => {
  function getParams (assayMode: boolean): ColDefBuildParams {
    let table: AssayRenderTable | StudyRenderTable
    let tableUuid: string
    if (!assayMode) {
      table = tableData.tables.study
      tableUuid = STUDY_UUID
    } else {
      table = tableData.tables.assays[ASSAY_UUID] as AssayRenderTable
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

    appStore.currentStudyUuid = STUDY_UUID
    appStore.editMode = false
    appStore.sodarContext = copy(sodarContext) as SodarContext
    tableStore.studyDisplayConfig = copy(
      studyTables.display_config) as StudyDisplayConfig
    tableStore.sampleColId = 'col7'

    tableData = copy(studyTables) as RenderTableData
  })

  test('build study columns', async () => {
    const res = buildColDef(getParams(false))
    // Includes rowNum group and extra source group in addition to study groups
    expect(res.length).toBe(studyNodeLen + 2)
  })

  test('build rowNum group', async () => {
    const res = buildColDef(getParams(false))
    const group = res[0]!
    expect(group).toEqual(getRowNumHeaderGroup())
    expect((group.children[0] as ColDef).cellClass).not.toContain('bg-light')
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

  test('build main source group', async () => {
    const res = buildColDef(getParams(false))
    const group = res[2]!
    expect(group.children.length).toBe(2)
    expect((group.children[0] as ColDef).field).toBe('col1')
    expect((group.children[0] as ColDef).headerName).toBe('Organism')
    expect((group.children[1] as ColDef).headerName).toBe('Age')
  })

  test('build study shortcuts group', async () => {
    const appStore = useAppStore()
    appStore.sodarContext!.studies[STUDY_UUID]!.plugin_name = STUDY_PLUGIN_NAME
    tableData.tables.study.shortcuts = studyShortcutsGermline as
      unknown as StudyShortcuts

    const params = getParams(false)
    const res = buildColDef(params)
    expect(res.length).toBe(studyNodeLen + 3) // Extra group for shortcuts
    const group = res[studyNodeLen + 2]!
    const exp = getStudyShortcutHeaderGroup(
        tableData.tables.study, params.studyShortcutModal)
    expect(JSON.stringify(group)).toEqual(JSON.stringify(exp))
  })

  test('build study columns in edit mode', async () => {
    setEditMode()
    const res = buildColDef(getParams(false))
    // Extra group for row edit column
    expect(res.length).toBe(studyNodeLen + 3)
  })

  test('build rowNum group in edit mode', async () => {
    setEditMode()
    const res = buildColDef(getParams(false))
    const group = res[0]!
    expect((group.children[0] as ColDef).cellClass).toContain('bg-light')
  })

  test('build source name group in edit mode', async () => {
    setEditMode()
    const res = buildColDef(getParams(false))
    const group = res[1]!
    expect(group.children.length).toBe(1)
    const col = group.children[0] as ColDef
    const editConfigField = { name: 'Name', type: EDIT_HEADER_TYPE_NAME }
    expect(col.cellEditorParams).toEqual({
      assayMode: false,
      colAlign: 'left',
      colWidth: 100, // TODO: Why does this differ from col.width?,
      editConfigField: editConfigField,
      fieldHeader: tableData.tables.study.field_header[0],
      fieldId: 'col0',
      notifyCb: undefined,
      ontologyEditModal: undefined,
      sampleColId: 'col7',
      tableUuid: STUDY_UUID,
    })
    expect(col.headerComponent).toBe('HeaderEditRenderer')
    expect(col.headerComponentParams).toEqual({
      assayMode: false,
      assayUuid: null,
      canEditConfig: true,
      colType: EDIT_COL_TYPE_NAME,
      configFieldIdx: 0,
      configNodeIdx: 0,
      editConfigField: editConfigField,
      editable: false,
      headerType: EDIT_HEADER_TYPE_NAME,
      itemType: EDIT_ITEM_TYPE_SOURCE,
      modalRef: undefined,
      objCls: DB_OBJ_CLASS_MATERIAL
    })
    expect(col.minWidth).toBe(120)
    expect(typeof col.valueFormatter).toBe('function')
    expect(typeof col.valueParser).toBe('function')
    expect(col.width).toBe(120)

  })

  test('build source name group in edit mode with editable=true', async () => {
    const tableStore = useTableStore()
    setEditMode()
    tableStore.studyEditConfig!.nodes![0]!.fields![0]!.editable = true

    const res = buildColDef(getParams(false))
    const group = res[1]!
    expect(group.children.length).toBe(1)
    const col = group.children[0] as ColDef
    expect(col.headerComponentParams.editConfigField).toEqual({
      editable: true, // Editable set here
      name: 'Name',
      type: EDIT_HEADER_TYPE_NAME,
    })
    expect(col.headerComponentParams.editable).toBe(true)
  })

  test('build study row edit column', async () => {
    setEditMode()
    const res = buildColDef(getParams(false))
    const group = res[studyNodeLen + 2]!
    expect(group.children.length).toBe(1)
    const exp = getRowEditHeaderGroup({
      assayMode: false,
      tableUuid: STUDY_UUID
    })
    expect(JSON.stringify(group)).toEqual(JSON.stringify(exp))
  })

  test('build assay columns', async () => {
    const res = buildColDef(getParams(true))
    // Includes rowNum and extra source group in addition to study/assay groups
    expect(res.length).toBe(assayNodeLen + 2)
  })

  test('build assay columns with assay shortcuts', async () => {
    const appStore = useAppStore()
    appStore.sodarContext!.irods_status = true
    appStore.sodarContext!.studies[
      STUDY_UUID]!.assays[ASSAY_UUID]!.display_row_links = true

    const params = getParams(true)
    const res = buildColDef(params)
    // Assay shortcut column added
    expect(res.length).toBe(assayNodeLen + 3)

    const group = res[assayNodeLen + 2]!
    expect(group).toEqual(getAssayIrodsHeaderGroup(
      appStore.sodarContext!,
      appStore.sodarContext!.studies[STUDY_UUID]!.assays[ASSAY_UUID]!,
      params.irodsDirModal,
      appStore.notifyCb,
    ))
  })

  test('build assay row edit column', async () => {
    setEditMode()
    const res = buildColDef(getParams(true))
    const group = res[assayNodeLen + 2]!
    expect(group.children.length).toBe(1)
    const exp = getRowEditHeaderGroup({
      assayMode: true,
      tableUuid: ASSAY_UUID
    })
    expect(JSON.stringify(group)).toEqual(JSON.stringify(exp))
  })

  test('build assay columns with edit mode and assay shortcuts', async () => {
    setEditMode()
    const appStore = useAppStore()
    appStore.sodarContext!.irods_status = true
    appStore.sodarContext!.studies[
      STUDY_UUID]!.assays[ASSAY_UUID]!.display_row_links = true

    const params = getParams(true)
    const res = buildColDef(params)
    // No extra columns added
    expect(res.length).toBe(assayNodeLen + 3)

    // Last group should be row edit column, no shortcuts visible
    const group = res[assayNodeLen + 2]!
    const exp = getRowEditHeaderGroup({
      assayMode: true,
      tableUuid: ASSAY_UUID
    })
    expect(JSON.stringify(group)).toEqual(JSON.stringify(exp))
  })
})
