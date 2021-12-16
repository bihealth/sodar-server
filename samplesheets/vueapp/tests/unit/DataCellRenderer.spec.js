import { createLocalVue, mount } from '@vue/test-utils'
import {
  studyUuid,
  copy,
  getAppStub,
  getSheetTablePropsData,
  waitRAF,
  waitAG
} from '../testUtils.js'
import { initGridOptions } from '@/utils/gridUtils.js'
import BootstrapVue from 'bootstrap-vue'
import VueClipboard from 'vue-clipboard2'
import SheetTable from '@/components/SheetTable.vue'
import studyTables from './data/studyTables.json'
import studyTablesEdit from './data/studyTablesEdit.json'
import studyTablesOneCol from './data/studyTablesOneCol.json'
import sheetEditConfigModified from './data/sheetEditConfigModified.json'

// Set up extended Vue constructor
const localVue = createLocalVue()
localVue.use(BootstrapVue)
localVue.use(VueClipboard)

// Init data
// let propsData
const studyEditConfig = sheetEditConfigModified.studies[studyUuid]

// NOTE: Yes this is how you're supposed to test renderers according to ag-grid

describe('DataCellRenderer.vue', () => {
  function mountSheetTable (params = {}, editStudyConfig = null) {
    const retParams = Object.assign({
      app: getAppStub(params),
      editMode: false,
      gridOptions: null,
      editStudyConfig: null
    }, params)
    retParams.gridOptions = initGridOptions(retParams.app, retParams.editMode)
    // if (params.editMode) console.dir(retParams) // DEBUG
    return mount(SheetTable, {
      localVue, propsData: getSheetTablePropsData(retParams)
    })
  }

  beforeAll(() => {
    // NOTE: Workaround for bootstrap-vue "Vue warn" errors, see issue #1034
    jest.spyOn(console, 'error').mockImplementation(jest.fn())
    // Disable warnings
    jest.spyOn(console, 'warn').mockImplementation(jest.fn())
  })

  beforeEach(() => {
    jest.resetModules()
    jest.clearAllMocks()
  })

  it('renders name cell', async () => {
    // NOTE: Default header = name
    const wrapper = mountSheetTable({ table: studyTablesOneCol.tables.study })
    await waitAG(wrapper)
    await waitRAF()

    const cell = wrapper.find('.sodar-ss-data-cell')
    const cellData = cell.find('.sodar-ss-data')
    expect(cellData.text()).toBe('0814')
    expect(cell.classes()).not.toContain('text-right')
    expect(cell.classes()).not.toContain('text-muted')
  })

  it('renders name cell with empty value', async () => {
    const table = copy(studyTablesOneCol).tables.study
    table.table_data[0][0] = studyTables.tables.study.table_data[4][9]
    const wrapper = mountSheetTable({ table: table })
    await waitAG(wrapper)
    await waitRAF()

    const cell = wrapper.find('.sodar-ss-data-cell')
    const cellData = cell.find('.sodar-ss-data')
    expect(cellData.text()).toBe('-')
    expect(cell.classes()).not.toContain('text-right')
    expect(cell.classes()).not.toContain('text-muted')
  })

  it('renders ontology cell', async () => {
    const table = copy(studyTablesOneCol).tables.study
    table.field_header[0] = studyTables.tables.study.field_header[1]
    table.table_data[0][0] = studyTables.tables.study.table_data[0][1]
    const wrapper = mountSheetTable({ table: table })
    await waitAG(wrapper)
    await waitRAF()

    const cell = wrapper.find('.sodar-ss-data-cell')
    const cellData = cell.find('.sodar-ss-data')
    expect(cellData.find('.sodar-list-btn').exists()).toBe(false) // not HPO
    expect(cellData.text()).toBe('Mus musculus; Homo sapiens')
    expect(cellData.findAll('a').length).toBe(2)
    expect(cell.classes()).not.toContain('text-right')
    expect(cell.classes()).not.toContain('text-muted')
  })

  it('renders ontology cell in edit mode with editing enabled', async () => {
    const table = copy(studyTablesOneCol).tables.study
    table.field_header[0] = studyTablesEdit.tables.study.field_header[1]
    table.table_data[0][0] = studyTablesEdit.tables.study.table_data[0][1]
    const wrapper = mountSheetTable({
      table: table,
      editMode: true,
      editContext: copy(studyTablesEdit.edit_context),
      editStudyConfig: {
        nodes: [{ fields: [studyEditConfig.nodes[0].fields[1]] }]
      }
    })
    await waitAG(wrapper)
    await waitRAF()

    const cell = wrapper.find('.sodar-ss-data-cell')
    const cellData = cell.find('.sodar-ss-data')
    expect(cellData.find('.sodar-list-btn').exists()).toBe(false) // not HPO
    expect(cellData.text()).toContain('Mus musculus;')
    expect(cellData.text()).toContain('Homo sapiens')
    expect(cellData.findAll('a').length).toBe(0)
    expect(cell.classes()).not.toContain('text-right')
    expect(cell.classes()).not.toContain('text-muted')
    expect(cell.classes()).not.toContain('bg-light')
  })

  it('renders ontology cell in edit mode with editing disabled', async () => {
    const table = copy(studyTablesOneCol).tables.study
    table.field_header[0] = studyTablesEdit.tables.study.field_header[1]
    table.table_data[0][0] = studyTablesEdit.tables.study.table_data[0][1]
    const editField = copy(studyEditConfig).nodes[0].fields[1]
    editField.editable = false
    const wrapper = mountSheetTable({
      table: table,
      editMode: true,
      editContext: copy(studyTablesEdit.edit_context),
      editStudyConfig: { nodes: [{ fields: [editField] }] }
    })
    await waitAG(wrapper)
    await waitRAF()

    const cell = wrapper.find('.sodar-ss-data-cell')
    expect(cell.classes()).toContain('text-muted')
    expect(cell.classes()).toContain('bg-light')
  })

  it('renders integer cell with unit', async () => {
    const table = copy(studyTablesOneCol).tables.study
    table.field_header[0] = studyTables.tables.study.field_header[2]
    table.table_data[0][0] = studyTables.tables.study.table_data[0][2]
    const wrapper = mountSheetTable({ table: table })
    await waitAG(wrapper)
    await waitRAF()

    const cell = wrapper.find('.sodar-ss-data-cell')
    const cellData = cell.find('.sodar-ss-data')
    expect(cellData.text()).toBe('90 day')
    expect(cell.classes()).toContain('text-right')
    expect(cell.classes()).not.toContain('text-muted')
    expect(cellData.find('span.text-muted').exists()).toBe(true)
  })

  it('renders process protocol cell', async () => {
    const table = copy(studyTablesOneCol).tables.study
    table.field_header[0] = studyTables.tables.study.field_header[3]
    table.table_data[0][0] = studyTables.tables.study.table_data[0][3]
    const wrapper = mountSheetTable({ table: table })
    await waitAG(wrapper)
    await waitRAF()

    const cell = wrapper.find('.sodar-ss-data-cell')
    const cellData = cell.find('.sodar-ss-data')
    expect(cellData.text()).toBe('sample collection')
    expect(cell.classes()).not.toContain('text-right')
    expect(cell.classes()).not.toContain('text-muted')
  })

  it('renders basic text cell', async () => {
    const table = copy(studyTablesOneCol).tables.study
    table.field_header[0] = studyTables.tables.study.field_header[4]
    table.table_data[0][0] = studyTables.tables.study.table_data[0][4]
    const wrapper = mountSheetTable({ table: table })
    await waitAG(wrapper)
    await waitRAF()

    const cell = wrapper.find('.sodar-ss-data-cell')
    const cellData = cell.find('.sodar-ss-data')
    expect(cellData.text()).toBe('scalpel')
    expect(cell.classes()).not.toContain('text-right')
    expect(cell.classes()).not.toContain('text-muted')
  })

  it('renders basic text cell with a list of values', async () => {
    const table = copy(studyTablesOneCol).tables.study
    table.field_header[0] = studyTables.tables.study.field_header[4]
    table.table_data[0][0] = studyTables.tables.study.table_data[2][4]
    const wrapper = mountSheetTable({ table: table })
    await waitAG(wrapper)
    await waitRAF()

    const cell = wrapper.find('.sodar-ss-data-cell')
    const cellData = cell.find('.sodar-ss-data')
    expect(cellData.text()).toBe('scalpel type A; scalpel type B')
    expect(cell.classes()).not.toContain('text-right')
    expect(cell.classes()).not.toContain('text-muted')
  })

  it('renders basic text cell with simple link', async () => {
    const table = copy(studyTablesOneCol).tables.study
    table.field_header[0] = studyTables.tables.study.field_header[4]
    table.table_data[0][0] = studyTables.tables.study.table_data[0][4]
    table.table_data[0][0].value = 'Link <https://bihealth.org>'
    const wrapper = mountSheetTable({ table: table })
    await waitAG(wrapper)
    await waitRAF()

    const cell = wrapper.find('.sodar-ss-data-cell')
    const cellData = cell.find('.sodar-ss-data')
    const cellLink = cellData.find('a')
    expect(cellData.text()).toBe('Link')
    expect(cellLink.attributes().href).toBe('https://bihealth.org')
    expect(cell.classes()).not.toContain('text-right')
    expect(cell.classes()).not.toContain('text-muted')
  })

  it('renders contact cell with plain text value', async () => {
    const table = copy(studyTablesOneCol).tables.study
    table.field_header[0] = studyTables.tables.study.field_header[5]
    table.table_data[0][0] = studyTables.tables.study.table_data[0][5]
    const wrapper = mountSheetTable({ table: table })
    await waitAG(wrapper)
    await waitRAF()

    const cell = wrapper.find('.sodar-ss-data-cell')
    const cellData = cell.find('.sodar-ss-data')
    expect(cellData.text()).toBe('John Doe')
    expect(cellData.find('a').exists()).toBe(false)
    expect(cell.classes()).not.toContain('text-right')
    expect(cell.classes()).not.toContain('text-muted')
  })

  it('renders contact cell with email value', async () => {
    const table = copy(studyTablesOneCol).tables.study
    table.field_header[0] = studyTables.tables.study.field_header[5]
    table.table_data[0][0] = studyTables.tables.study.table_data[0][5]
    table.table_data[0][0].value = 'John Doe <john@example.com>'
    const wrapper = mountSheetTable({ table: table })
    await waitAG(wrapper)
    await waitRAF()

    const cell = wrapper.find('.sodar-ss-data-cell')
    const cellData = cell.find('.sodar-ss-data')
    expect(cellData.text()).toBe('John Doe')
    expect(cellData.find('a').exists()).toBe(true)
    expect(cellData.find('a').attributes().href).toBe('mailto:john@example.com')
    expect(cell.classes()).not.toContain('text-right')
    expect(cell.classes()).not.toContain('text-muted')
  })

  it('renders contact cell with bracket syntax', async () => {
    const table = copy(studyTablesOneCol).tables.study
    table.field_header[0] = studyTables.tables.study.field_header[5]
    table.table_data[0][0] = studyTables.tables.study.table_data[0][5]
    table.table_data[0][0].value = 'John Doe [john@example.com]'
    const wrapper = mountSheetTable({ table: table })
    await waitAG(wrapper)
    await waitRAF()

    const cell = wrapper.find('.sodar-ss-data-cell')
    const cellData = cell.find('.sodar-ss-data')
    expect(cellData.text()).toBe('John Doe')
    expect(cellData.find('a').exists()).toBe(true)
    expect(cellData.find('a').attributes().href).toBe('mailto:john@example.com')
    expect(cell.classes()).not.toContain('text-right')
    expect(cell.classes()).not.toContain('text-muted')
  })

  it('renders date cell', async () => {
    const table = copy(studyTablesOneCol).tables.study
    table.field_header[0] = studyTables.tables.study.field_header[6]
    table.table_data[0][0] = studyTables.tables.study.table_data[0][6]
    const wrapper = mountSheetTable({ table: table })
    await waitAG(wrapper)
    await waitRAF()

    const cell = wrapper.find('.sodar-ss-data-cell')
    const cellData = cell.find('.sodar-ss-data')
    expect(cellData.text()).toBe('2018-02-02')
    expect(cell.classes()).not.toContain('text-right')
    expect(cell.classes()).not.toContain('text-muted')
  })

  it('renders integer cell with no unit', async () => {
    const table = copy(studyTablesOneCol).tables.study
    table.field_header[0] = studyTables.tables.study.field_header[8]
    table.table_data[0][0] = studyTables.tables.study.table_data[0][8]
    const wrapper = mountSheetTable({ table: table })
    await waitAG(wrapper)
    await waitRAF()

    const cell = wrapper.find('.sodar-ss-data-cell')
    const cellData = cell.find('.sodar-ss-data')
    expect(cellData.text()).toBe('0')
    expect(cell.classes()).toContain('text-right')
    expect(cell.classes()).not.toContain('text-muted')
  })

  it('renders integer cell with no unit and empty value', async () => {
    const table = copy(studyTablesOneCol).tables.study
    table.field_header[0] = studyTables.tables.study.field_header[8]
    table.table_data[0][0] = studyTables.tables.study.table_data[4][8]
    const wrapper = mountSheetTable({ table: table })
    await waitAG(wrapper)
    await waitRAF()

    const cell = wrapper.find('.sodar-ss-data-cell')
    const cellData = cell.find('.sodar-ss-data')
    expect(cellData.text()).toBe('-')
    expect(cell.classes()).toContain('text-right')
    expect(cell.classes()).not.toContain('text-muted')
  })

  it('renders external links cell', async () => {
    const table = copy(studyTablesOneCol).tables.study
    table.field_header[0] = {
      value: 'External Links',
      name: 'External links',
      obj_cls: 'GenericMaterial',
      item_type: 'SOURCE',
      num_col: false,
      config_set: false,
      col_type: 'EXTERNAL_LINKS',
      max_value_len: 2
    }
    const value = ['id-type-a:ID-123', 'id-type-b:ID-XYZ']
    table.table_data[0][0].value = value
    const wrapper = mountSheetTable({ table: table })
    await waitAG(wrapper)
    await waitRAF()

    const cell = wrapper.find('.sodar-ss-data-cell')
    const cellData = cell.find('.sodar-ss-data')
    expect(cellData.findAll('.badge-group').length).toBe(2)
    expect(cellData.text()).toBe(
      'ID' + value[0].split(':')[1] + 'ID' + value[1].split(':')[1])
    expect(cell.classes()).not.toContain('text-right')
    expect(cell.classes()).not.toContain('text-muted')
  })

  it('renders HPO terms ontology value cell', async () => {
    const table = copy(studyTablesOneCol).tables.study
    table.field_header[0] = {
      value: 'Hpo Terms',
      name: 'HPO terms',
      obj_cls: 'GenericMaterial',
      item_type: 'SOURCE',
      num_col: false,
      config_set: false,
      col_type: 'ONTOLOGY',
      max_value_len: 171
    }
    table.table_data[0][0].value = [
      {
        name: 'Ataxia',
        accession: 'https://bioportal.bioontology.org/ontologies/HP/' +
          '?p=classes&conceptid=http://purl.obolibrary.org/obo/HP_0001251',
        ontology_name: 'HP'
      },
      {
        name: 'Hypoplasia of the corpus callosum',
        accession: 'https://bioportal.bioontology.org/ontologies/HP/' +
          '?p=classes&conceptid=http://purl.obolibrary.org/obo/HP_0002079',
        ontology_name: 'HP'
      }
    ]
    const wrapper = mountSheetTable({ table: table })
    await waitAG(wrapper)
    await waitRAF()

    const cell = wrapper.find('.sodar-ss-data-cell')
    const cellData = cell.find('.sodar-ss-data')
    expect(cellData.find('.sodar-list-btn').exists()).toBe(true)
    expect(cellData.findAll('a').length).toBe(2)
    expect(cellData.text()).toBe('Ataxia; Hypoplasia of the corpus callosum')
    expect(cell.classes()).not.toContain('text-right')
    expect(cell.classes()).not.toContain('text-muted')
  })

  it('renders HPO terms ontology value cell in edit mode', async () => {
    const table = copy(studyTablesOneCol).tables.study
    table.field_header[0] = {
      value: 'Hpo Terms',
      name: 'HPO terms',
      obj_cls: 'GenericMaterial',
      item_type: 'SOURCE',
      num_col: false,
      config_set: false,
      col_type: 'ONTOLOGY',
      type: 'characteristics',
      max_value_len: 171
    }
    table.table_data[0][0].value = [
      {
        name: 'Ataxia',
        accession: 'https://bioportal.bioontology.org/ontologies/HP/' +
          '?p=classes&conceptid=http://purl.obolibrary.org/obo/HP_0001251',
        ontology_name: 'HP'
      },
      {
        name: 'Hypoplasia of the corpus callosum',
        accession: 'https://bioportal.bioontology.org/ontologies/HP/' +
          '?p=classes&conceptid=http://purl.obolibrary.org/obo/HP_0002079',
        ontology_name: 'HP'
      }
    ]
    const wrapper = mountSheetTable({
      table: table,
      editMode: true,
      editContext: copy(studyTablesEdit.edit_context)
    })
    await waitAG(wrapper)
    await waitRAF()

    const cell = wrapper.find('.sodar-ss-data-cell')
    const cellData = cell.find('.sodar-ss-data')
    expect(cellData.find('.sodar-list-btn').exists()).toBe(false) // not there in editing
    expect(cellData.text()).toContain('Ataxia;')
    expect(cellData.text()).toContain('Hypoplasia of the corpus callosum')
    expect(cellData.findAll('a').length).toBe(0)
  })

  it('renders file name cell', async () => {
    const table = copy(studyTablesOneCol).tables.study
    table.field_header[0] = {
      value: 'Name',
      name: 'Name',
      obj_cls: 'GenericMaterial',
      item_type: 'DATA',
      num_col: false,
      config_set: false,
      col_type: 'LINK_FILE',
      max_value_len: 13
    }
    table.table_data[0][0].value = '0815-somatic.vcf.gz'
    const wrapper = mountSheetTable({ table: table })
    await waitAG(wrapper)
    await waitRAF()

    const cell = wrapper.find('.sodar-ss-data-cell')
    const cellData = cell.find('.sodar-ss-data')
    expect(cellData.text()).toBe('0815-somatic.vcf.gz')
    expect(cell.classes()).not.toContain('text-right')
    expect(cell.classes()).not.toContain('text-muted') // No colls = not muted
  })

  // TODO: Test event handlers
  // TODO: Test file name cell with mocked existing file
})
