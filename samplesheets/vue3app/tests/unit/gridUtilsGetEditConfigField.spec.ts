import { beforeEach, describe, expect, test } from 'vitest'

import { getEditConfigField } from '@/utils/gridUtils.ts'
import {
  type EditConfigFieldGetParams,
  type RenderTableData,
  type SheetTableFieldHeader,
  type StudyEditConfig,
} from '@/types.ts'

import { copy } from '../testUtils.ts'
import studyTablesEdit from '../data/studyTablesEdit.json'
import { ASSAY_UUID, STUDY_UUID } from '../testConstants.ts'

// Test Data -------------------------------------------------------------------

const nameFieldHeader = studyTablesEdit.tables.study.field_header[0]

const defaultParams: EditConfigFieldGetParams = {
  assayMode: false,
  fieldHeader: nameFieldHeader as SheetTableFieldHeader,
  studyEditConfig: studyTablesEdit.study_config as unknown as StudyEditConfig,
  tableUuid: STUDY_UUID,
  topIdx: 0
}
let params: EditConfigFieldGetParams

// Tests -----------------------------------------------------------------------

describe('getEditConfigField()', () => {
  beforeEach(() => {
    params = copy(defaultParams) as EditConfigFieldGetParams
  })

  test('get study source name config', async () => {
    const res = getEditConfigField(params)
    expect(res).toEqual(studyTablesEdit.study_config.nodes[0]!.fields[0])
  })

  test('get study source organism config', async () => {
    params.fieldHeader = studyTablesEdit.tables.study.field_header[1] as
      SheetTableFieldHeader
    const res = getEditConfigField(params)
    expect(res).toEqual(studyTablesEdit.study_config.nodes[0]!.fields[1])
  })

  test('get study protocol config', async () => {
    params.fieldHeader = studyTablesEdit.tables.study.field_header[3] as
      SheetTableFieldHeader
    params.topIdx = 1
    const res = getEditConfigField(params)
    expect(res).toEqual(studyTablesEdit.study_config.nodes[1]!.fields[0])
  })

  test('get study sample name config', async () => {
    params.fieldHeader = studyTablesEdit.tables.study.field_header[7] as
      SheetTableFieldHeader
    params.topIdx = 2
    const res = getEditConfigField(params)
    expect(res).toEqual(studyTablesEdit.study_config.nodes[2]!.fields[0])
  })

  test('get assay sample name config', async () => {
    params.assayMode = true
    params.fieldHeader = (studyTablesEdit as unknown as
      RenderTableData).tables.assays[ASSAY_UUID]!.field_header[7] as
        SheetTableFieldHeader
    params.tableUuid = ASSAY_UUID
    params.topIdx = 2
    const res = getEditConfigField(params)
    expect(res).toEqual(studyTablesEdit.study_config.nodes[2]!.fields[0])
  })

  test('get assay sample protocol config', async () => {
    params.assayMode = true
    params.fieldHeader = (studyTablesEdit as unknown as
      RenderTableData).tables.assays[ASSAY_UUID]!.field_header[10] as
        SheetTableFieldHeader
    params.tableUuid = ASSAY_UUID
    params.topIdx = 3
    const res = getEditConfigField(params)
    expect(res).toEqual((studyTablesEdit as unknown as
      RenderTableData).study_config!.assays[ASSAY_UUID]!.nodes[0]!.fields[0])
  })
})
