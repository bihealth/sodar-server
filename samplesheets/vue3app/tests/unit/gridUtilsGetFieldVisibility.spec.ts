import { beforeEach, describe, expect, test } from 'vitest'

import { getFieldVisibility } from '@/utils/gridUtils.ts'
import { type SheetTableFieldHeader, type StudyDisplayConfig } from '@/types.ts'

import { copy } from '../testUtils.ts'
import studyTables from '../data/studyTables.json'
import { ASSAY_UUID, STUDY_UUID } from '../testConstants.ts'

// Tests -----------------------------------------------------------------------

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
