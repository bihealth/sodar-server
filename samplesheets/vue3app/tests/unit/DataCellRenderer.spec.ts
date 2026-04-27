import { beforeEach, describe, expect, test } from 'vitest'
import { mount, type VueWrapper } from '@vue/test-utils'

import DataCellRenderer from '@/components/renderers/DataCellRenderer.vue'
import {
  type DataCellRendererParams,
  type SheetTableCellData,
  type SheetTableOntologyRef
} from '@/types.ts'

import { copy } from '../testUtils.ts'
import { sodarContext } from '../data/sodarContext.ts'
import studyTables from '../data/studyTables.json'

const defaultCellData: SheetTableCellData = {
  editable: false,
  value: '0814'
}

// NOTE: headerName does not matter except with ontology and HPO terms
const defaultParams = {
  colDef: { headerName: 'Header', field: 'col0' },
  colType: 'NAME',
  editMode: false,
  enableHover: true,
  linkLabels: sodarContext.external_link_labels,
  node: { id: '1' },
  value: defaultCellData
}
let params: DataCellRendererParams

describe('DataCellRenderer.vue', () => {
  function mountComponent (): VueWrapper {
    return mount(DataCellRenderer, { props: { params: params } })
  }
  beforeEach(() => {
    params = copy(defaultParams) as DataCellRendererParams
  })

  test('render component', async () => {
    // Use defaultParams for name field
    const wrapper = mountComponent()
    const elem = wrapper.find('.sodar-ss-data')
    expect(elem.exists()).toBe(true)
    expect(elem.attributes()['data-col-num']).toBe('0')
    expect(elem.attributes()['data-row-id']).toBe('1')
  })

  test('render name field', async () => {
    // Use defaultParams for name field
    const wrapper = mountComponent()
    expect(wrapper.find('.sodar-ss-data').exists()).toBe(true)
    const data = wrapper.find('.sodar-ss-data-val-plain')
    expect(data.exists()).toBe(true)
    expect(data.text()).toBe(params.value?.value)
    // Assert other value types and unit are not present
    expect(wrapper.find('.sodar-ss-data-val-ontology').exists()).toBe(false)
    expect(wrapper.find('.sodar-ss-data-val-contact').exists()).toBe(false)
    expect(wrapper.find('.sodar-ss-data-val-ext').exists()).toBe(false)
    expect(wrapper.find('.sodar-ss-data-val-file').exists()).toBe(false)
    expect(wrapper.find('.sodar-ss-data-val-link').exists()).toBe(false)
    expect(wrapper.find('.sodar-ss-data-val-special').exists()).toBe(false)
    expect(wrapper.find('.sodar-ss-data-unit').exists()).toBe(false)
  })

  test('render ontology field', async () => {
    params.colType = 'ONTOLOGY'
    // Example ontology value is two NCBITAXON terms
    params.value!.value = studyTables.tables.study.table_data[0]![1]!.value as
      Array<SheetTableOntologyRef>
    const wrapper = mountComponent()

    const val = wrapper.find('.sodar-ss-data-val-ontology')
    expect(val.exists()).toBe(true)
    expect(val.find('.sodar-ss-hpo-copy-btn').exists()).toBe(false)
    expect(val.text()).toBe(
      params.value?.value[0]!.name + '; ' + params.value?.value[1]!.name
    )
    const links = val.findAll('a')
    expect(links.length).toBe(2)
    for (let i = 0; i < 2; i++) {
      expect(links[i]!.attributes().href).toBe(params.value?.value[i]!.accession)
      expect(links[i]!.attributes().title).toBe(
        params.value?.value[i]!.ontology_name)
      expect(links[i]!.text()).toBe(params.value?.value[i]!.name)
    }
  })

  test('render ontology field in edit mode', async () => {
    params.editMode = true
    params.colType = 'ONTOLOGY'
    params.value!.value = studyTables.tables.study.table_data[0]![1]!.value as
      Array<SheetTableOntologyRef>
    const wrapper = mountComponent()

    const val = wrapper.find('.sodar-ss-data-val-ontology')
    expect(val.text()).toBe(
      params.value?.value[0]!.name + '; ' + params.value?.value[1]!.name
    )
    expect(val.find('a').exists()).toBe(false) // No links in edit mode
  })

  test('render ontology field with HPO term', async () => {
    params.colDef!.headerName = 'HPO terms'
    params.colType = 'ONTOLOGY'
    params.value!.value = [{
        name: 'Renal tubular atrophy',
        accession: 'https://purl.obolibrary.org/obo/HP_0000092',
        ontology_name: 'HP'
    }]
    const wrapper = mountComponent()

    const val = wrapper.find('.sodar-ss-data-val-ontology')
    expect(val.find('.sodar-ss-hpo-copy-btn').exists()).toBe(true)
    expect(val.text()).toBe(params.value!.value[0]!.name)
  })

  // TODO: Test HPO term clipboard copying

  test('render contact field', async () => {
    params.colType = 'CONTACT'
    params.value!.value = [
      'Alice Example <alice@example.com>',
      'Bob Example <bob@example.com>'
    ]
    const wrapper = mountComponent()

    const val = wrapper.find('.sodar-ss-data-val-contact')
    expect(val.text()).toBe('Alice Example; Bob Example')
    const link = val.findAll('a')[0]
    expect(link!.attributes().href).toBe('mailto:alice@example.com')
    expect(link!.text()).toBe('Alice Example')
  })

  test('render contact field with single contact', async () => {
    params.colType = 'CONTACT'
    params.value!.value = ['Alice Example <alice@example.com>']
    const wrapper = mountComponent()

    const val = wrapper.find('.sodar-ss-data-val-contact')
    expect(val.text()).toBe('Alice Example')
    const link = val.find('a')
    expect(link!.attributes().href).toBe('mailto:alice@example.com')
    expect(link!.text()).toBe('Alice Example')
  })

  // TODO: Test contact field without email (see #2412)

  test('render eternal links field', async () => {
    params.colType = 'EXTERNAL_LINKS'
    // Second badge should be rendered as a link
    params.value!.value = ['x-generic-remote:123', 'x-sodar-example-link:456']
    const wrapper = mountComponent()

    const val = wrapper.find('.sodar-ss-data-val-ext')
    expect(val.exists()).toBe(true)
    const badges = val.findAll('.badge-group')
    expect(badges.length).toBe(2)
    expect(badges[0]?.findAll('.badge')[0]?.text()).toBe('ID')
    expect(badges[0]?.findAll('.badge')[1]?.text()).toBe('123')
    expect(badges[0]?.find('a').exists()).toBe(false)
    expect(badges[1]?.findAll('.badge')[0]?.text()).toBe('ID')
    expect(badges[1]?.findAll('.badge')[1]?.text()).toBe('456')
    expect(badges[1]?.find('a').exists()).toBe(true)
    expect(badges[1]?.find('a').attributes().href).toBe(
      'https://example.com/456')
  })

  test('render eternal links field with unknown ID types', async () => {
    params.colType = 'EXTERNAL_LINKS'
    params.value!.value = ['abc:123', 'def:456']
    const wrapper = mountComponent()

    const val = wrapper.find('.sodar-ss-data-val-ext')
    const badges = val.findAll('.badge-group')
    expect(badges.length).toBe(2)
    expect(badges[0]?.findAll('.badge')[0]?.text()).toBe('ID')
    expect(badges[0]?.findAll('.badge')[1]?.text()).toBe('123')
    expect(badges[0]?.find('a').exists()).toBe(false)
    expect(badges[1]?.findAll('.badge')[0]?.text()).toBe('ID')
    expect(badges[1]?.findAll('.badge')[1]?.text()).toBe('456')
    expect(badges[1]?.find('a').exists()).toBe(false)
  })

  test('render file link field', async () => {
    params.colType = 'LINK_FILE'
    params.value!.link = 'https://example.com'
    params.value!.value = 'Example Link'
    const wrapper = mountComponent()

    const val = wrapper.find('.sodar-ss-data-val-file')
    expect(val.exists()).toBe(true)
    expect(val.text()).toBe('Example Link')
    const link = val.find('a')
    expect(link.exists()).toBe(true)
    expect(link.attributes().href).toBe('https://example.com')
    expect(link.attributes().title).toBe('')
  })

  // TODO: Remove tooltip support? (see #2413)
  test('render file link field with tooltip', async () => {
    params.colType = 'LINK_FILE'
    params.value!.link = 'https://example.com'
    params.value!.tooltip = 'Tooltip'
    params.value!.value = 'Example Link'
    const wrapper = mountComponent()
    const val = wrapper.find('.sodar-ss-data-val-file')
    expect(val.find('a').attributes().title).toBe(params.value?.tooltip)
  })

  test('render file link field without link', async () => {
    params.colType = 'LINK_FILE'
    // No link added to value
    params.value!.value = 'Example Link'
    const wrapper = mountComponent()

    const val = wrapper.find('.sodar-ss-data-val-file')
    expect(val.exists()).toBe(true)
    expect(val.text()).toBe('Example Link')
    expect(val.find('a').exists()).toBe(false)
  })

  test('render field with value as simple link', async () => {
    // NOTE: Yes, this also works with name field
    params.value!.value = 'Link <https://example.com>'
    const wrapper = mountComponent()
    expect(wrapper.find('.sodar-ss-data').exists()).toBe(true)
    const data = wrapper.find('.sodar-ss-data-val-link')
    expect(data.exists()).toBe(true)
    const link = data.find('a')
    expect(link.exists()).toBe(true)
    expect(link.text()).toBe('Link')
    expect(link.attributes().href).toBe('https://example.com')
  })

  test('render field with value as list of strings', async () => {
    params.value!.value = ['val1', 'val2']
    const wrapper = mountComponent()
    expect(wrapper.find('.sodar-ss-data').exists()).toBe(true)
    const data = wrapper.find('.sodar-ss-data-val-special')
    expect(data.exists()).toBe(true)
    expect(data.text()).toBe('val1; val2')
  })

  test('render unit field', async () => {
    params.colType = 'UNIT'
    params.value!.value = '90'
    params.value!.unit = 'day'
    const wrapper = mountComponent()

    // const val = wrapper.find('.sodar-ss-data-val-')
    expect(wrapper.find('.sodar-ss-data-val-plain').exists()).toBe(true)
    expect(wrapper.find('.sodar-ss-data-unit').exists()).toBe(true)
    // NOTE: No actual whitespace character here
    expect(wrapper.find('.sodar-ss-data').text()).toBe('90day')
    expect(wrapper.find('.sodar-ss-data-unit').text()).toBe('day')
  })
})
