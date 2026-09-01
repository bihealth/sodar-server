import { type TemplateRef } from 'vue'
import { beforeEach, describe, expect, test } from 'vitest'
import { type ColDef, type ColGroupDef } from 'ag-grid-community'

import { getStudyShortcutHeaderGroup } from '@/utils/gridUtils.ts'
import { type StudyRenderTable, type StudyShortcuts } from '@/types.ts'

import { copy } from '../testUtils.ts'
import studyTables from '../data/studyTables.json'
import studyShortcutsGermline from '../data/studyShortcutsGermline.json'

// Tests -----------------------------------------------------------------------

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
