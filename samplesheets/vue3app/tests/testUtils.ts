import { type TemplateRef } from 'vue'
import { type VueWrapper } from '@vue/test-utils'

import { buildColDef, buildRowData } from '@/utils/gridUtils.ts'
import { useAppStore } from '@/stores/appStore.ts'
import { useTableStore } from '@/stores/tableStore.ts'
import {
  type AssayRenderTable,
  type ColDefBuildParams,
  type RenderTableData,
  type SodarContext,
  type StudyDisplayConfig,
  type StudyRenderTable
} from '@/types.ts'

// Basic copy function for data objects
export function copy (obj: object): object {
  return JSON.parse(JSON.stringify(obj))
}

// Wait for N milliseconds
// NOTE: Don't use unless no other reasonable options exist :)
export async function waitMs (ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms))
}

// Wait for at least N elements to be present by selector
export const waitSelector = (
    wrapper: VueWrapper,
    selector: string,
    count: number
) =>
  new Promise<void>(function (resolve): void {(
    function waitForSelectorCount () {
      if (count === undefined) count = 1
      if ((count > 0 && wrapper.findAll(selector).length >= count) ||
          (count === 0 && wrapper.findAll(selector).length === count)) {
        return resolve()
      }
      setTimeout(waitForSelectorCount, 10)
    })()
  })

// Set up table store with given sodar Context and render tables
// NOTE: This expects Pinia to be set up beforehand
// NOTE: This expects exactly one study and assay. Can be updated to multiple
//       ones later if needed
// TODO: Update for edit mode
export function setUpTableStore (
    sodarContext: SodarContext,
    studyTables: RenderTableData,
    studyUuid: string,
    assayUuid: string,
) {
  const appStore = useAppStore()
  appStore.currentStudyUuid = studyUuid
  appStore.sodarContext = sodarContext
  const tableStore = useTableStore()
  tableStore.sampleColId = 'col7'
  tableStore.studyDisplayConfig = copy(
      studyTables.display_config) as StudyDisplayConfig

  const studyTable = copy(studyTables.tables.study) as StudyRenderTable
  const assayTable = copy(
    (studyTables as unknown as RenderTableData).tables.assays[assayUuid] as
      AssayRenderTable) as AssayRenderTable

  const colDefParams: ColDefBuildParams = {
    assayMode: false,
    irodsDirModal: {} as TemplateRef,
    studyNodeLen: studyTables.tables.study.top_header.length,
    studyShortcutModal: {} as TemplateRef,
    table: studyTable,
    tableUuid: studyUuid,
  }
  // TODO: Add ontologyEditModal if edit mode

  tableStore.columnDefs.study = buildColDef(colDefParams)
  tableStore.columnDefs.assays[assayUuid] = buildColDef(
    Object.assign(colDefParams, {
      assayMode: true,
      table: assayTable,
      tableUuid: assayUuid
    }))
  tableStore.rowData.study = buildRowData(studyTable, false)
  tableStore.rowData.assays[assayUuid] = buildRowData(assayTable, true)
}
