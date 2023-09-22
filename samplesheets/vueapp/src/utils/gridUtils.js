// Helpers for SODAR ag-grid setup

// Initialize ag-grid gridOptions
export function initGridOptions (app, editMode) {
  return {
    // debug: true,
    pagination: false,
    animateRows: false,
    rowSelection: 'single',
    suppressMovableColumns: true,
    suppressColumnMoveAnimation: true,
    suppressRowClickSelection: true,
    singleClickEdit: false,
    headerHeight: 38,
    rowHeight: 38,
    suppressColumnVirtualisation: false,
    context: { componentParent: app },
    defaultColDef: {
      editable: false,
      resizable: true,
      sortable: !editMode
    }
  }
}

// Helper to get flat value for comparator
function getFlatValue (value) {
  if (Array.isArray(value) && value.length > 0) {
    if (typeof value[0] === 'object' && 'name' in value[0]) {
      return value.map(d => d.name).join(';')
    } else return value.join(';')
  } else {
    return value
  }
}

// Custom comparator for data cells
function dataCellCompare (dataA, dataB) {
  let valueA = dataA.value
  let valueB = dataB.value
  if (['UNIT', 'NUMERIC'].includes(dataA.colType)) {
    if (!isNaN(parseFloat(valueA)) && !isNaN(parseFloat(valueB))) {
      return parseFloat(valueA) - parseFloat(valueB)
    }
  } else {
    valueA = getFlatValue(valueA)
    valueB = getFlatValue(valueB)
  }
  return valueA.localeCompare(valueB)
}

// Custom filter value for data cells (fix for #686)
function dataCellFilterValue (params) {
  return getFlatValue(params.data[params.column.colId].value)
}

// Build column definitions for a study/assay grid
export function buildColDef (params) {
  // Default columns
  const colDef = []
  let editFieldConfig
  let displayFieldConfig
  let fieldVisible

  const rowHeaderGroup = {
    headerName: 'Row',
    headerClass: ['bg-secondary', 'text-white'],
    suppressSizeToFit: true,
    suppressAutoSize: true,
    children: [
      {
        headerName: '#',
        field: 'rowNum',
        editable: false,
        headerClass: ['sodar-ss-data-header'],
        cellClass: [
          'text-right',
          'text-muted',
          'sodar-ss-data-unselectable',
          'sodar-ss-data-row-cell',
          'sodar-ss-data-rownum-cell'
        ],
        suppressSizeToFit: true,
        suppressAutoSize: true,
        pinned: 'left',
        unselectable: true,
        cellRenderer: null,
        minWidth: 65,
        maxWidth: 100,
        width: 65
      }
    ]
  }

  // Editing: gray out row column to avoid confusion
  if (params.editMode) {
    rowHeaderGroup.children[0].cellClass.push('bg-light')
  }
  colDef.push(rowHeaderGroup)

  // Sample sheet columns
  const topHeaderLength = params.table.top_header.length
  let headerIdx = 0
  let j = headerIdx
  let studySection = true

  // Iterate through top header
  for (let i = 0; i < topHeaderLength; i++) {
    const topHeader = params.table.top_header[i]

    // Set up header group
    let headerGroup = {
      headerName: topHeader.value,
      headerClass: ['text-white', 'bg-' + topHeader.colour],
      children: []
    }
    if (params.editMode) {
      headerGroup.cellRendererParams = { headers: topHeader.headers }
    }

    let configFieldIdx = 0 // For config management

    // Iterate through field headers
    while (j < headerIdx + topHeader.colspan) {
      const fieldHeader = params.table.field_header[j]

      // Define special column properties
      const maxValueLen = fieldHeader.max_value_len
      const colType = fieldHeader.col_type

      let colAlign
      if (['UNIT', 'NUMERIC'].includes(colType)) colAlign = 'right'
      else colAlign = 'left'

      let minW = params.sodarContext.min_col_width
      const maxW = params.sodarContext.max_col_width
      let calcW = maxValueLen * 10 + 25 // Default
      let colWidth
      let fieldEditable = false

      // External links are a special case
      if (colType === 'EXTERNAL_LINKS') {
        minW = 150
        calcW = maxValueLen * 120
      }

      // Set the final column width
      if (j < params.table.col_last_vis) {
        colWidth = calcW < minW ? minW : (calcW > maxW ? maxW : calcW)
      } else { // Last visible column is a special case
        colWidth = Math.max(calcW, minW)
      }

      // Get studyDisplayConfig
      if (params.studyDisplayConfig) {
        let displayNode
        if (!params.assayMode) {
          displayNode = params.studyDisplayConfig.nodes[i]
        } else {
          displayNode = params.studyDisplayConfig.assays[params.gridUuid].nodes[i]
        }
        if (displayNode) {
          for (let k = 0; k < displayNode.fields.length; k++) {
            const f = displayNode.fields[k]
            if (f.name === fieldHeader.name) {
              displayFieldConfig = f
              break
            }
          }
        }
      }

      if (displayFieldConfig) { // Visibility from config
        fieldVisible = displayFieldConfig.visible
      } else if (params.assayMode &&
            studySection &&
            fieldHeader.value !== 'Name') { // Hide study data in assay
        fieldVisible = false
      } else { // Hide if empty and not editing
        fieldVisible = !!(fieldEditable || params.table.col_values[j])
      }

      // Get editFieldConfig if editing
      if (params.editMode && params.editStudyConfig) {
        editFieldConfig = null
        let editNode = null
        const studyNodeLen = params.editStudyConfig.nodes.length

        if (!params.assayMode || i < studyNodeLen) {
          editNode = params.editStudyConfig.nodes[i]
        } else {
          editNode = params.editStudyConfig.assays[params.gridUuid].nodes[
            i - studyNodeLen]
        }

        if (editNode) {
          for (let k = 0; k < editNode.fields.length; k++) {
            const f = editNode.fields[k]
            if (f.name === fieldHeader.name &&
                (['Name', 'Protocol'].includes(f.name) ||
                f.type === fieldHeader.type)) {
              editFieldConfig = f
              break
            }
          }
        }
      }

      if (editFieldConfig && 'editable' in editFieldConfig) {
        fieldEditable = editFieldConfig.editable
      }

      // Create data header
      const header = {
        headerName: fieldHeader.value,
        field: 'col' + j.toString(),
        width: colWidth,
        minWidth: minW,
        hide: !fieldVisible,
        headerClass: ['sodar-ss-data-header'],
        cellRenderer: 'DataCellRenderer',
        cellRendererParams: {
          app: params.app,
          colType: colType,
          fieldEditable: fieldEditable // Needed here to update cellClass
        },
        comparator: dataCellCompare,
        filterValueGetter: dataCellFilterValue
      }

      // Cell classes
      if (!params.editMode) {
        header.cellClass = ['sodar-ss-data-cell', 'text-' + colAlign]
      } else {
        header.cellClass = function (p) {
          const colAlign = ['UNIT', 'NUMERIC'].includes(
            p.colDef.cellRendererParams.colType)
            ? 'right'
            : 'left'
          const cellClass = ['sodar-ss-data-cell', 'text-' + colAlign]

          // Set extra classes if non-editable
          if (('editable' in p.value && !p.value.editable) ||
              (!('editable' in p.value) &&
              !p.colDef.cellRendererParams.fieldEditable)) {
            if ('newInit' in p.value && p.value.newInit) {
              cellClass.push('sodar-ss-data-forbidden')
            } else cellClass.push('bg-light')
            cellClass.push('text-muted')
          }
          return cellClass
        }
      }

      // Make source name column pinned, disable hover
      // HACK: also create new header group to avoid name duplication
      if (j === 0) {
        header.pinned = 'left'
        header.cellRendererParams.enableHover = false
        headerGroup.children.push(header)
        colDef.push(headerGroup)
        headerGroup = {
          headerName: '',
          headerClass: ['bg-' + topHeader.colour],
          children: []
        }
      }

      // Editing: set up field and its header for editing
      if (params.editMode) {
        // Set header renderer for fields we can manage
        if (params.sodarContext.perms.edit_sheet) {
          let configAssayUuid = params.assayMode ? params.gridUuid : null
          let configNodeIdx = i

          if (params.assayMode) {
            if (configNodeIdx < params.studyNodeLen) configAssayUuid = null
            else configNodeIdx = i - params.studyNodeLen
          }

          header.headerComponent = 'HeaderEditRenderer'
          header.headerComponentParams = {
            app: params.app,
            modalComponent: params.app.$refs.columnConfigModal,
            colType: colType,
            fieldConfig: editFieldConfig,
            assayUuid: configAssayUuid,
            configNodeIdx: configNodeIdx,
            configFieldIdx: configFieldIdx,
            editable: fieldEditable, // Add here to allow checking by cell
            headerType: fieldHeader.type,
            assayMode: params.assayMode, // Needed for sample col in assay
            canEditConfig: params.sodarContext.perms.edit_config
          }
          header.width = header.width + 20 // Fit button in header
          header.minWidth = header.minWidth + 20
        }

        // Set up field editing
        if (editFieldConfig) {
          // Allow overriding field editability cell-by-cell
          header.editable = function (p) {
            if (p.colDef.field in p.node.data &&
                'editable' in p.node.data[p.colDef.field]) {
              return p.node.data[p.colDef.field].editable
            } else if ('headerComponentParams' in p.colDef) {
              return p.colDef.headerComponentParams.editable
            } else return false
          }

          // Set up cell editor selector
          header.cellEditorSelector = function (p) {
            let editorName = 'DataCellEditor'
            // TODO: Refactor so that default params are read from header
            const editorParams = Object.assign(p.colDef.cellEditorParams)
            const editContext = params.editContext

            // If sample name in an assay or an object ref, return selector
            // TODO: Simplify?
            if (p.colDef.headerComponentParams.assayMode &&
                p.column.originalParent.colGroupDef.headerName === 'Sample' &&
                p.colDef.headerName === 'Name' &&
                'newRow' in p.value &&
                p.value.newRow) {
              editorName = 'ObjectSelectEditor'
              editorParams.selectOptions = editContext.samples
            } else if (editorParams.headerInfo.header_type === 'protocol') {
              editorName = 'ObjectSelectEditor'
              editorParams.selectOptions = Object.assign(editContext.protocols)
            } else if (colType === 'ONTOLOGY') {
              editorName = 'OntologyEditor'
              editorParams.sodarOntologies = editContext.sodar_ontologies
            }

            return { component: editorName, params: editorParams }
          }

          // Set default cellEditorParams (may be updated in the selector)
          header.cellEditorParams = {
            app: params.app,
            // Header information to be passed for calling server
            headerInfo: {
              header_name: fieldHeader.name,
              header_type: fieldHeader.type,
              header_field: header.field, // For updating other cells
              obj_cls: fieldHeader.obj_cls
            },
            renderInfo: { align: colAlign, width: colWidth },
            editConfig: editFieldConfig, // Editor configuration
            gridUuid: params.gridUuid, // TODO: Could get this from header params
            sampleColId: params.sampleColId
          }

          // Add item type to generic material name
          if (fieldHeader.obj_cls === 'GenericMaterial' &&
              fieldHeader.type === 'name') {
            header.cellEditorParams.headerInfo.item_type = fieldHeader.item_type
          }
        }
      }

      if (j > 0) headerGroup.children.push(header)
      j++
      configFieldIdx += 1
    }

    headerIdx = j
    colDef.push(headerGroup)
    if (topHeader.value === 'Sample') studySection = false
  }

  // TODO: Reduce repetition in special column definitions
  // Study shortcut column
  if (!params.editMode &&
      !params.assayMode &&
      'shortcuts' in params.table &&
      params.table.shortcuts) {
    const shortcutHeaderGroup = {
      headerName: 'Links',
      headerClass: ['text-white', 'bg-secondary', 'sodar-ss-data-links-top'],
      children: [
        {
          headerName: 'Study',
          field: 'shortcutLinks',
          editable: false,
          headerClass: ['sodar-ss-data-header', 'sodar-ss-data-links-header'],
          cellClass: ['sodar-ss-data-links-cell', 'sodar-ss-data-unselectable'],
          suppressSizeToFit: true,
          suppressAutoSize: true,
          resizable: true,
          sortable: false,
          pinned: 'right',
          unselectable: true,
          width: 45 * Object.keys(params.table.shortcuts.schema).length,
          minWidth: 90,
          cellRenderer: 'StudyShortcutsRenderer',
          cellRendererParams: {
            schema: params.table.shortcuts.schema,
            modalComponent: params.app.$refs.studyShortcutModal
          }
        }
      ]
    }
    colDef.push(shortcutHeaderGroup)
  }

  // Assay iRODS button column
  if (!params.editMode && params.assayMode) {
    const assayContext = params.sodarContext.studies[
      params.currentStudyUuid].assays[params.gridUuid]
    if (params.sodarContext.irods_status && assayContext.display_row_links) {
      const assayIrodsPath = assayContext.irods_path
      const irodsHeaderGroup = {
        headerName: 'iRODS',
        headerClass: ['text-white', 'bg-secondary', 'sodar-ss-data-links-top'],
        children: [
          {
            headerName: 'Links',
            field: 'irodsLinks',
            editable: false,
            headerClass: ['sodar-ss-data-header', 'sodar-ss-data-links-header'],
            cellClass: ['sodar-ss-data-links-cell', 'sodar-ss-data-unselectable'],
            suppressSizeToFit: true,
            suppressAutoSize: true,
            resizable: true,
            sortable: false,
            pinned: 'right',
            unselectable: true,
            cellRenderer: 'IrodsButtonsRenderer',
            cellRendererParams: {
              app: params.app,
              irodsStatus: params.sodarContext.irods_status,
              irodsBackendEnabled: params.sodarContext.irods_backend_enabled,
              irodsWebdavUrl: params.sodarContext.irods_webdav_url,
              assayIrodsPath: assayIrodsPath,
              showFileList: true,
              modalComponent: params.app.$refs.dirModalRef
            },
            width: 152, // TODO: Attempt to calculate this somehow?
            minWidth: 152
          }
        ]
      }
      colDef.push(irodsHeaderGroup)
    }
  }

  // Row editing column
  if (params.editMode) {
    const rowEditGroup = {
      headerName: 'Edit',
      headerClass: ['text-white', 'bg-secondary', 'sodar-ss-data-links-top'],
      children: [
        {
          headerName: 'Row',
          field: 'rowEdit',
          editable: false,
          headerClass: ['sodar-ss-data-header', 'sodar-ss-data-links-header'],
          cellClass: ['sodar-ss-data-links-cell', 'sodar-ss-data-unselectable'],
          suppressSizeToFit: true,
          suppressAutoSize: true,
          resizable: true,
          sortable: false,
          pinned: 'right',
          unselectable: true,
          cellRenderer: 'RowEditRenderer',
          cellRendererParams: {
            app: params.app,
            gridUuid: params.gridUuid,
            assayMode: params.assayMode,
            sampleColId: params.sampleColId,
            sampleIdx: params.sampleIdx
          },
          width: 80,
          minWidth: 80
        }
      ]
    }
    colDef.push(rowEditGroup)
  }

  return colDef
}

// Build row data for a grid
export function buildRowData (params) {
  const rowData = []

  // Iterate through rows
  for (let i = 0; i < params.table.table_data.length; i++) {
    const rowCells = params.table.table_data[i]
    const row = { rowNum: i + 1 }
    let nodeUuid = null
    for (let j = 0; j < rowCells.length; j++) {
      const cellVal = rowCells[j]

      // Set node UUID
      if ('uuid' in cellVal && cellVal.uuid) {
        nodeUuid = cellVal.uuid // Get node UUID from first node cell
      } else cellVal.uuid = nodeUuid // Set node UUID to other cells

      // Copy col_type info to each cell (comparator can't access colDef)
      cellVal.colType = params.table.field_header[j].col_type

      // Set user friendly ontology accession URL
      if (params.sodarContext.ontology_url_template &&
          !params.editMode &&
          cellVal.colType === 'ONTOLOGY') {
        for (const term of cellVal.value) {
          if (term.accession &&
              !params.sodarContext.ontology_url_skip.some(
                x => term.accession.includes(x))) {
            let ontologyName = term.ontology_name
            // HACK for mislabeled HP terms
            if (ontologyName === 'HPO') ontologyName = 'HP'
            let url = params.sodarContext.ontology_url_template
            url = url.replace('{ontology_name}', ontologyName)
            url = url.replace('{accession}', encodeURIComponent(term.accession))
            term.accession = url
          }
        }
      }
      row['col' + j.toString()] = cellVal
    }
    // Add study shortcut field
    if (!params.editMode &&
        !params.assayMode &&
        'shortcuts' in params.table &&
        params.table.shortcuts) {
      row.shortcutLinks = params.table.shortcuts.data[i]
    }
    // Add iRODS field
    if (!params.editMode &&
        params.sodarContext.irods_status &&
        'irods_paths' in params.table &&
        params.table.irods_paths.length > 0) {
      row.irodsLinks = params.table.irods_paths[i]
    }
    rowData.push(row)
  }
  return rowData
}
