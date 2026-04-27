import { type TemplateRef } from 'vue'
import { type VueWrapper } from '@vue/test-utils'

import { buildColDef, buildRowData } from '@/utils/gridUtils.ts'
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
  const tableStore = useTableStore()
  tableStore.studyDisplayConfig = copy(
      studyTables.display_config) as StudyDisplayConfig

  const colDefParams: ColDefBuildParams = {
    studyUuid: studyUuid,
    editMode: false,
    sampleColId: 'col7',
    sodarContext: sodarContext,
    studyDisplayConfig: tableStore.studyDisplayConfig,
    irodsDirModal: {} as TemplateRef,
    studyEditConfig: null,
    studyNodeLen: studyTables.tables.study.field_header.length,
    studyShortcutModal: {} as TemplateRef,
  }
  // TODO: Add ontologyEditModal if edit mode
  const studyTable = copy(studyTables.tables.study) as StudyRenderTable
    const assayTable = copy(
      (studyTables as unknown as RenderTableData).tables.assays[assayUuid] as
        AssayRenderTable) as AssayRenderTable

  tableStore.columnDefs.study = buildColDef(
    studyTable, studyUuid, false, colDefParams
  )
  tableStore.columnDefs.assays[assayUuid] = buildColDef(
    assayTable, assayUuid, true, colDefParams
  )
  tableStore.rowData.study = buildRowData(
    studyTable, false, false, sodarContext
  )
  tableStore.rowData.assays[assayUuid] = buildRowData(
    assayTable, true, false, sodarContext
  )
}
