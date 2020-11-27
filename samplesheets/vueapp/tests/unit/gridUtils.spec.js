import {
  // copy,
  getAppStub,
  getColDefParams,
  getRowDataParams
} from '../testUtils.js'
// import sodarContext from './data/sodarContext.json'
// import studyTables from './data/studyTables.json'
// import studyTablesEdit from './data/studyTablesEdit.json'
import { initGridOptions, buildColDef, buildRowData } from '@/utils/gridUtils.js'

// TODO: Should be tested with multiple ISAtabs

describe('initGridOptions()', () => {
  beforeAll(() => {
    // Disable warnings
    jest.spyOn(console, 'warn').mockImplementation(jest.fn())
  })

  beforeEach(() => {
    jest.resetModules()
    jest.clearAllMocks()
  })

  it('returns gridOptions', () => {
    const gridOptions = initGridOptions(getAppStub(), false)
    expect(gridOptions.defaultColDef.sortable).toBe(true)
  })

  it('returns gridOptions in edit mode', () => {
    const gridOptions = initGridOptions(getAppStub(), true)
    expect(gridOptions.defaultColDef.sortable).toBe(false)
  })
})

// TODO: Test getFlatValue()
// TODO: Test dataCellCompare()

describe('buildColDef()', () => {
  beforeAll(() => {
    // Disable warnings
    jest.spyOn(console, 'warn').mockImplementation(jest.fn())
  })

  beforeEach(() => {
    jest.resetModules()
    jest.clearAllMocks()
  })

  it('returns study colDef', () => {
    const colDef = buildColDef(getColDefParams())

    expect(colDef.length).toBe(5) // NOTE: No study shortcuts for this config
    expect(colDef[0].headerName).toBe('Row')
    expect(colDef[0].children.length).toBe(1)
    expect(colDef[0].children[0].headerName).toBe('#')
    expect(colDef[0].children[0].pinned).toBe('left')
    expect(colDef[0].children[0].unselectable).toBe(true)
    expect(colDef[1].headerName).toBe('Source')
    expect(colDef[1].children.length).toBe(1)
    expect(colDef[1].children[0].headerName).toBe('Name')
    expect(colDef[2].headerName).toBe('') // Split source group
    expect(colDef[2].children.length).toBe(2)
    expect(colDef[3].headerName).toBe('Process')
    expect(colDef[3].children.length).toBe(4)
    expect(colDef[4].headerName).toBe('Sample')
    expect(colDef[4].children.length).toBe(3)

    for (let i = 0; i < colDef.length; i++) {
      for (let j = 0; j < colDef[i].children.length; j++) {
        expect([false, undefined]).toContain(colDef[i].children[j].editable)
        expect([false, undefined]).toContain(colDef[i].children[j].hide)
      }
    }
  })

  it('returns assay colDef', () => {
    const colDef = buildColDef(getColDefParams({ assayMode: true }))

    expect(colDef.length).toBe(13)
    expect(colDef[0].headerName).toBe('Row')
    expect(colDef[0].children.length).toBe(1)
    expect(colDef[0].children[0].pinned).toBe('left')
    expect(colDef[0].children[0].headerName).toBe('#')
    expect(colDef[1].headerName).toBe('Source')
    expect(colDef[1].children.length).toBe(1)
    expect(colDef[1].children[0].headerName).toBe('Name')
    expect(colDef[2].headerName).toBe('') // Split source group
    expect(colDef[2].children.length).toBe(2)
    for (let i = 0; i < colDef[2].children.length; i++) {
      expect(colDef[2].children[i].hide).toBe(true)
    }
    expect(colDef[3].headerName).toBe('Process')
    expect(colDef[3].children.length).toBe(4)
    expect(colDef[3].children[0].hide).toBe(false)
    for (let i = 1; i < colDef[3].children.length; i++) {
      expect(colDef[3].children[i].hide).toBe(true)
    }
    expect(colDef[4].headerName).toBe('Sample')
    expect(colDef[4].children.length).toBe(3)
    expect(colDef[4].children[0].hide).toBe(false)
    for (let i = 1; i < colDef[4].children.length; i++) {
      expect(colDef[4].children[i].hide).toBe(true)
    }
    expect(colDef[5].headerName).toBe('Process')
    expect(colDef[6].headerName).toBe('Library Name')
    expect(colDef[7].headerName).toBe('Process')
    expect(colDef[7].children.length).toBe(2)
    expect(colDef[8].headerName).toBe('Raw Data File')
    expect(colDef[9].headerName).toBe('Raw Data File')
    expect(colDef[10].headerName).toBe('Process')
    expect(colDef[11].headerName).toBe('Derived Data File')
    expect(colDef[12].headerName).toBe('iRODS')
    expect(colDef[12].children[0].pinned).toBe('right')
    expect(colDef[12].children[0].unselectable).toBe(true)
    expect(colDef[12].children[0].sortable).toBe(false)

    for (let i = 0; i < colDef.length; i++) {
      for (let j = 0; j < colDef[i].children.length; j++) {
        expect([false, undefined]).toContain(colDef[i].children[j].editable)
      }
    }
  })

  it('hides study columns', () => {
    const params = getColDefParams()
    let nodeLen = params.studyDisplayConfig.nodes[0].fields.length
    for (let i = 1; i < nodeLen; i++) {
      params.studyDisplayConfig.nodes[0].fields[i].visible = false
    }
    nodeLen = params.studyDisplayConfig.nodes[2].fields.length
    for (let i = 1; i < nodeLen; i++) {
      params.studyDisplayConfig.nodes[2].fields[i].visible = false
    }
    const colDef = buildColDef(params)

    for (let i = 0; i < colDef[2].children.length; i++) {
      expect(colDef[2].children[i].hide).toBe(true)
    }
    for (let i = 1; i < colDef[4].children.length; i++) {
      expect(colDef[4].children[i].hide).toBe(true)
    }
  })

  it('displays study columns in assay', () => {
    const params = getColDefParams({ assayMode: true })
    const u = params.gridUuid
    let nodeLen = params.studyDisplayConfig.assays[u].nodes[0].fields.length
    for (let i = 0; i < nodeLen; i++) {
      params.studyDisplayConfig.assays[u].nodes[0].fields[i].visible = true
    }
    nodeLen = params.studyDisplayConfig.assays[u].nodes[2].fields.length
    for (let i = 0; i < nodeLen; i++) {
      params.studyDisplayConfig.assays[u].nodes[2].fields[i].visible = true
    }
    const colDef = buildColDef(params)

    for (let i = 0; i < colDef[2].children.length; i++) {
      expect(colDef[2].children[i].hide).toBe(false)
    }
    for (let i = 1; i < colDef[4].children.length; i++) {
      expect(colDef[4].children[i].hide).toBe(false)
    }
  })

  it('returns study colDef in edit mode', () => {
    const colDef = buildColDef(getColDefParams({ editMode: true }))

    expect(colDef.length).toBe(6)
    expect(colDef[5].headerName).toBe('Edit')
    expect(colDef[5].children[0].headerName).toBe('Row')
    for (let i = 0; i < colDef.length - 1; i++) {
      for (let j = 0; j < colDef[i].children.length; j++) {
        expect(['boolean', 'function']).toContain(typeof colDef[i].children[j].editable)
      }
    }
  })

  it('returns assay colDef in edit mode', () => {
    const colDef = buildColDef(
      getColDefParams({ assayMode: true, editMode: true }))

    expect(colDef.length).toBe(13) // iRODS column replaced
    expect(colDef[12].headerName).toBe('Edit')
    expect(colDef[12].children[0].headerName).toBe('Row')
    for (let i = 0; i < colDef.length - 1; i++) {
      for (let j = 0; j < colDef[i].children.length; j++) {
        expect(['boolean', 'function']).toContain(typeof colDef[i].children[j].editable)
      }
    }
  })

  // TODO: More detailed tests where appropriate
})

describe('buildRowData()', () => {
  beforeAll(() => {
    // Disable warnings
    jest.spyOn(console, 'warn').mockImplementation(jest.fn())
  })

  beforeEach(() => {
    jest.resetModules()
    jest.clearAllMocks()
  })

  it('returns study rowData', () => {
    const rowData = buildRowData(getRowDataParams())

    expect(rowData.length).toBe(5)
    for (let i = 0; i < rowData.length; i++) {
      expect(Object.keys(rowData[i]).length).toBe(11)
      expect(rowData[i].rowNum).toBe(i + 1)
      for (let j = 0; j < 10; j++) {
        const keys = Object.keys(rowData[i]['col' + j])
        expect(keys).toContain('value')
        expect(keys).toContain('colType')
      }
      expect(Object.keys(rowData[i].col2)).toContain('unit')
    }
  })

  it('returns assay rowData', () => {
    const rowData = buildRowData(getRowDataParams({ assayMode: true }))

    expect(rowData.length).toBe(2)
    for (let i = 0; i < rowData.length; i++) {
      // NOTE: iRODS column data not here, built in renderer
      expect(Object.keys(rowData[i]).length).toBe(19)
      expect(rowData[i].rowNum).toBe(i + 1)
      for (let j = 0; j < 10; j++) {
        const keys = Object.keys(rowData[i]['col' + j])
        expect(keys).toContain('value')
        expect(keys).toContain('colType')
      }
    }
  })

  it('returns study rowData in edit mode', () => {
    const rowData = buildRowData(getRowDataParams({ editMode: true }))

    expect(rowData.length).toBe(5)
    for (let i = 0; i < rowData.length; i++) {
      expect(Object.keys(rowData[i]).length).toBe(11)
      expect(rowData[i].rowNum).toBe(i + 1)
      for (let j = 0; j < 10; j++) {
        const keys = Object.keys(rowData[i]['col' + j])
        expect(keys).toContain('value')
        expect(keys).toContain('colType')
        expect(keys).toContain('uuid')
      }
      expect(Object.keys(rowData[i].col2)).toContain('unit')
      expect(Object.keys(rowData[i].col3)).toContain('uuid_ref') // Protocol
    }
  })

  it('returns assay rowData in edit mode', () => {
    const rowData = buildRowData(
      getRowDataParams({ assayMode: true, editMode: true }))
    // console.dir(rowData) // DEBUG

    expect(rowData.length).toBe(2)
    for (let i = 0; i < rowData.length; i++) {
      expect(Object.keys(rowData[i]).length).toBe(19)
      expect(rowData[i].rowNum).toBe(i + 1)
      for (let j = 0; j < 18; j++) {
        const keys = Object.keys(rowData[i]['col' + j])
        expect(keys).toContain('value')
        expect(keys).toContain('colType')
        expect(keys).toContain('uuid')
      }
      expect(Object.keys(rowData[i].col2)).toContain('unit')
      expect(Object.keys(rowData[i].col3)).toContain('uuid_ref') // Protocol
    }
  })

  // TODO: Test colTypes
})
