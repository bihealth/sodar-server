import { beforeEach, describe, expect, test } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

import { useAppStore } from '@/stores/appStore.ts'
import { useTableStore } from '@/stores/tableStore.ts'

import { buildRowData } from '@/utils/gridUtils.ts'
import {
  type AssayRenderTable,
  type RenderTableData,
  type SheetTableCellData,
  type SheetTableOntologyRef,
  type SheetTableRowData,
  type SodarContext,
  type StudyDisplayConfig,
  type StudyEditConfig,
  type StudyRenderTable,
  type StudyShortcuts,
} from '@/types.ts'

import { copy } from '../testUtils.ts'
import studyTables from '../data/studyTables.json'
import studyTablesEdit from '../data/studyTablesEdit.json'
import { sodarContext } from '../data/sodarContext.ts'
import studyShortcutsGermline from '../data/studyShortcutsGermline.json'
import {
  ASSAY_UUID,
  ONTOLOGY_URL_TPL,
  STUDY_PLUGIN_NAME,
  STUDY_UUID
} from '../testConstants.ts'

// Test Data -------------------------------------------------------------------

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

    appStore.currentStudyUuid = STUDY_UUID
    appStore.editMode = false
    appStore.sodarContext = copy(sodarContext) as SodarContext
    appStore.sodarContext!.ontology_url_template = ONTOLOGY_URL_TPL
    tableStore.studyDisplayConfig = copy(
      studyTables.display_config) as StudyDisplayConfig
    tableStore.sampleColId = 'col7'

    tableData = copy(studyTables) as RenderTableData
  })

  test('build study rows', async () => {
    const res = callBuildRowData(false)
    expect(res.length).toBe(5)

    const row = res![0]!
    expect(Object.keys(row).length).toBe(11)
    expect(row.rowNum).toBe(1)
    for (let i = 0; i < 10; i++) {
      const d = tableData.tables.study.table_data[0]![i]!
      let unit
      if (d.unit) unit = d.unit
      expect(row['col' + i]).toEqual({ value: d.value, unit: unit, uuid: null })
    }
  })

  test('build study rows with study shortcuts', async () => {
    const appStore = useAppStore()
    appStore.sodarContext!.studies[STUDY_UUID]!.plugin_name = STUDY_PLUGIN_NAME
    tableData.tables.study.shortcuts = studyShortcutsGermline as
      unknown as StudyShortcuts

    const res = callBuildRowData(false)
    expect(res.length).toBe(5)
    const row = res![0]!
    expect(Object.keys(row).length).toBe(12)
    expect(row.shortcutLinks).toEqual(studyShortcutsGermline.data[0])
  })

  test('update ontology term accession with url template', async () => {
    const appStore = useAppStore()
    appStore.sodarContext!.ontology_url_skip = []

    const exp = tableData.tables.study.table_data[0]![1]!
    for (let i = 0; i < 2; i++) {
      const v = exp.value[i]! as SheetTableOntologyRef
      (exp.value[i]! as SheetTableOntologyRef).accession =
        ONTOLOGY_URL_TPL.replace(
          '{ontology_name}', v.ontology_name as string).replace(
          '{accession}', encodeURIComponent(v.accession))
      exp.uuid = null
    }

    const res = callBuildRowData(false)
    const row = res![0]!
    expect(row['col1']).toEqual(exp)
  })

  test('update ontology term accession with no skip matches', async () => {
    const appStore = useAppStore()
    appStore.sodarContext!.ontology_url_skip = [
      'archive.org', 'codeberg.org']

    const exp = tableData.tables.study.table_data[0]![1]!
    for (let i = 0; i < 2; i++) {
      const v = exp.value[i]! as SheetTableOntologyRef
      (exp.value[i]! as SheetTableOntologyRef).accession =
        ONTOLOGY_URL_TPL.replace(
          '{ontology_name}', v.ontology_name as string).replace(
          '{accession}', encodeURIComponent(v.accession))
      exp.uuid = null
    }

    const res = callBuildRowData(false)
    const row = res![0]!
    expect(row['col1']).toEqual(exp)
  })

  test('keep original ontology term accession with skip set', async () => {
    const appStore = useAppStore()
    appStore.sodarContext!.ontology_url_skip = ['bioontology.org']

    const res = callBuildRowData(false)
    const row = res![0]!
    // No change to original data expected
    expect(row['col1']).toEqual(tableData.tables.study.table_data[0]![1]!)
  })

  test('keep original accession with one skip match of multiple', async () => {
    const appStore = useAppStore()
    appStore.sodarContext!.ontology_url_skip = [
      'bioontology.org', 'archive.org']

    const res = callBuildRowData(false)
    const row = res![0]!
    expect(row['col1']).toEqual(tableData.tables.study.table_data[0]![1]!)
  })

  test('keep original ontology term accession with no template', async () => {
    const appStore = useAppStore()
    appStore.sodarContext!.ontology_url_skip = []
    appStore.sodarContext!.ontology_url_template = ''

    const res = callBuildRowData(false)
    const row = res![0]!
    expect(row['col1']).toEqual(tableData.tables.study.table_data[0]![1]!)
  })

  test('update HP ontology term from HPO notation', async () => {
    const appStore = useAppStore()
    appStore.sodarContext!.ontology_url_skip = []
    let v = tableData.tables.study.table_data[
      0]![1]!.value[0]! as SheetTableOntologyRef
    v.ontology_name = 'HPO'
    v.accession = 'http://purl.bioontology.org/ontology/HPO/2048'

    const res = callBuildRowData(false)
    const row = res![0]!
    const col = row['col1']! as SheetTableCellData
    v = col.value![0] as SheetTableOntologyRef
    expect(v.accession).toContain('/HP/')
    expect(v.accession).not.toContain('/HPO/')
  })

  test('build study rows in edit mode', async () => {
    setEditMode()
    const res = callBuildRowData(false)
    expect(res.length).toBe(5)

    const row = res![0]!
    expect(Object.keys(row).length).toBe(11)
    expect(row.rowNum).toBe(1)
    for (let i = 0; i < 10; i++) {
      const d = tableData.tables.study.table_data[0]![i]!
      const exp = { value: d.value, uuid: d.uuid } as SheetTableCellData
      if (d.unit) exp.unit = d.unit
      if (d.uuidRef) exp.uuidRef = d.uuidRef
      expect(row['col' + i]).toEqual(exp)
    }
  })

  test('build study rows in edit mode with study shortcuts', async () => {
    const appStore = useAppStore()
    appStore.sodarContext!.studies[STUDY_UUID]!.plugin_name = STUDY_PLUGIN_NAME
    setEditMode()
    tableData.tables.study.shortcuts = studyShortcutsGermline as
      unknown as StudyShortcuts

    const res = callBuildRowData(false)
    const row = res![0]!
     // Shortcuts should not be returned
    expect(Object.keys(row).length).toBe(11)
  })

  test('keep ontology term accession in edit mode', async () => {
    const appStore = useAppStore()
    appStore.sodarContext!.ontology_url_skip = []
    setEditMode()

    const res = callBuildRowData(false)
    const row = res![0]!
    expect(row['col1']).toEqual(tableData.tables.study.table_data[0]![1]!)
  })

  test('build assay rows', async () => {
    const res = callBuildRowData(true)
    expect(res.length).toBe(2)

    const row = res![0]!
    expect(Object.keys(row).length).toBe(19)
    expect(row.rowNum).toBe(1)
    for (let i = 0; i < 10; i++) {
      const d = (tableData as unknown as RenderTableData).tables.assays[
        ASSAY_UUID]!.table_data[0]![i]!
      let unit
      if (d.unit) unit = d.unit
      expect(row['col' + i]).toEqual({ value: d.value, unit: unit, uuid: null })
    }
  })

  test('build assay rows with assay shortcuts', async () => {
    const appStore = useAppStore()
    appStore.sodarContext!.irods_status = true
    appStore.sodarContext!.studies[
      STUDY_UUID]!.assays[ASSAY_UUID]!.display_row_links = true

    const td = tableData as unknown as RenderTableData
    const irodsPaths = [{
      enabled: true,
      path: '/sodarZone/x/y/z'
    }]
    td.tables.assays[ASSAY_UUID]!.irods_paths = irodsPaths

    const res = callBuildRowData(true)
    expect(res.length).toBe(2)

    const row = res![0]!
    expect(Object.keys(row).length).toBe(20) // Extra assay shortcut column
    expect(row.irodsLinks).toEqual(irodsPaths[0])
  })

  test('build assay rows in edit mode', async () => {
    setEditMode()
    const res = callBuildRowData(true)
    expect(res.length).toBe(2)

    const row = res![0]!
    expect(Object.keys(row).length).toBe(19)
    expect(row.rowNum).toBe(1)
    for (let i = 0; i < 10; i++) {
      const d = (tableData as unknown as RenderTableData).tables.assays[
        ASSAY_UUID]!.table_data[0]![i]!
      const exp = { value: d.value, uuid: d.uuid } as SheetTableCellData
      if (d.unit) exp.unit = d.unit
      if (d.uuidRef) exp.uuidRef = d.uuidRef
      expect(row['col' + i]).toEqual(exp)
    }
  })

  test('build assay rows in edit mode with assay shortcuts', async () => {
    const appStore = useAppStore()
    appStore.sodarContext!.irods_status = true
    appStore.sodarContext!.studies[
      STUDY_UUID]!.assays[ASSAY_UUID]!.display_row_links = true
    setEditMode()

    const td = tableData as unknown as RenderTableData
    td.tables.assays[ASSAY_UUID]!.irods_paths = [{
      enabled: true,
      path: '/sodarZone/x/y/z'
    }]

    const res = callBuildRowData(true)
    expect(res.length).toBe(2)
    const row = res![0]!
    expect(Object.keys(row).length).toBe(19) // No extra column returned
  })
})
