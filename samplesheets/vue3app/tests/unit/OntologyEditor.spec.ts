import { nextTick, type TemplateRef } from 'vue'
import { beforeEach, describe, expect, test, vi } from 'vitest'
import { mount, type VueWrapper } from '@vue/test-utils'

import OntologyEditor from '@/components/editors/OntologyEditor.vue'
import {
  type GridCellEditorParams,
  type SheetTableFieldHeader
} from '@/types.ts'

import studyTablesEdit from '../data/studyTablesEdit.json'
import { copy } from '../testUtils.ts'
import { STUDY_UUID } from '../testConstants.ts'

// Test Data -------------------------------------------------------------------

const defaultParams = {
  assayMode: false,
  colAlign: 'left',
  colWidth: 125,
  editConfigField: {
    name: 'organism',
    type: 'characteristics',
    format: 'ontology',
    allow_list: false,
    ontologies: []
  },
  fieldHeader: copy(
    studyTablesEdit.tables.study.field_header[1] as SheetTableFieldHeader) as
    SheetTableFieldHeader,
  fieldId: 'col1',
  sampleColId: 'col7',
  tableUuid: STUDY_UUID,
}
let params: GridCellEditorParams
const mockModal = { show: vi.fn() }

// Tests -----------------------------------------------------------------------

describe('OntologyEditor.vue', () => {
  async function mountComponent (): Promise<VueWrapper> {
    const wrapper = mount(OntologyEditor, { props: { params: params } })
    await nextTick()
    return wrapper
  }

  beforeEach(() => {
    vi.resetAllMocks()
    // setActivePinia(createPinia())
    params = copy(defaultParams) as GridCellEditorParams
    params.ontologyEditModal = mockModal as unknown as TemplateRef
  })

  test('render component and open modal', async () => {
    expect(mockModal.show).not.toBeCalled()
    await mountComponent()
    expect(mockModal.show).toBeCalled()
  })
})
