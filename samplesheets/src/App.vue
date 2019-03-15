<template>
  <div id="app">
    <!-- Header -->
    <PageHeader v-if="sodarContext"
                :app="this">
    </PageHeader>

    <!-- Main container -->
    <div class="container-fluid sodar-page-container">

      <!-- Study data rendered -->
      <div v-if="sodarContext &&
                 gridsLoaded &&
                 !renderError &&
                 !overviewActive"
                 :studyUuid="currentStudyUuid">

        <!-- Study -->
        <a class="sodar-ss-anchor" :id="currentStudyUuid"></a>
        <div class="row mb-4">
          <h4 class="font-weight-bold mb-0 text-info">
            <i class="fa fa-fw fa-list-alt"></i>
            Study: {{ sodarContext['studies'][currentStudyUuid]['display_name'] }}
            <!-- TODO: Add config/iRODS badges and iRODS buttons here -->
          </h4>
        </div>

        <div class="card sodar-ss-data-card sodar-ss-data-card-study">
          <div class="card-header">
            <h4>Study Data
              <b-input-group class="sodar-header-input-group pull-right">
                <b-input-group-prepend>
                  <b-button variant="secondary"
                            v-b-tooltip.hover
                            title="Download TSV file for Excel"
                            :href="'export/study/' + currentStudyUuid">
                    <i class="fa fa-file-excel-o"></i>
                  </b-button>
                </b-input-group-prepend>
                <b-form-input class="sodar-ss-data-filter"
                       type="text"
                       placeholder="Filter"
                       id="sodar-ss-data-filter-study"
                       @keyup="onFilterChange" />
              </b-input-group>
            </h4>
          </div>
          <div class="card-body p-0">
            <ag-grid-vue class="ag-theme-bootstrap"
                         :style="getGridStyle()"
                         :columnDefs="columnDefs['study']"
                         :rowData="rowData['study']"
                         :gridOptions="gridOptions['study']"
                         @grid-ready="onGridReady">
            </ag-grid-vue>
          </div>
        </div>

        <!-- Assays -->
        <span v-for="(assayInfo, assayUuid, index) in
                     sodarContext['studies'][currentStudyUuid]['assays']"
              :key="index">
          <a class="sodar-ss-anchor" :id="assayUuid"></a>
          <div class="row mb-4">
            <h4 class="font-weight-bold mb-0 text-danger">
              <i class="fa fa-fw fa-table"></i>
              Assay: {{ assayInfo['display_name'] }}
            </h4>
          </div>
          <div class="card sodar-ss-data-card sodar-ss-data-card-assay">
            <div class="card-header">
              <h4>
                Assay Data
                <b-input-group class="sodar-header-input-group pull-right">
                  <b-input-group-prepend>
                    <b-button variant="secondary"
                              v-b-tooltip.hover
                              title="Show/hide study details"
                              :id="'sodar-ss-assay-hide-' + assayUuid"
                              @mousedown="onAssayHideToggle($event, assayUuid)">
                      <i class="fa fa-eye-slash"></i>
                    </b-button>
                    <b-button variant="secondary"
                              v-b-tooltip.hover
                              title="Download TSV file for Excel"
                              :href="'export/assay/' + assayUuid">
                      <i class="fa fa-file-excel-o"></i>
                    </b-button>
                  </b-input-group-prepend>
                  <b-form-input class="sodar-ss-data-filter"
                         type="text"
                         placeholder="Filter"
                         :id="'sodar-ss-data-filter-assay-' + assayUuid"
                         :assay-uuid="assayUuid"
                         @keyup="onFilterChange" />
                </b-input-group>
              </h4>
            </div>
            <div class="card-body p-0">
              <ag-grid-vue :style="getGridStyle()"
                           class="ag-theme-bootstrap"
                           :columnDefs="columnDefs['assays'][assayUuid]"
                           :rowData="rowData['assays'][assayUuid]"
                           :gridOptions="gridOptions['assays'][assayUuid]"
                           @grid-ready="onGridReady">
            </ag-grid-vue>
            </div>
          </div>
        </span>

      </div>

      <!-- Overview mode -->
      <div v-else-if="overviewActive">
        <Overview :app="this">
        </Overview>
      </div>

      <!-- Render error -->
      <div v-else-if="renderError">
        <div class="alert alert-danger">
          Error rendering study tables, please check your ISAtab files.
          Exception: {{ renderError }}
        </div>
      </div>

      <!-- No sheets available -->
      <div v-else-if="appSetupDone && !sheetsAvailable">
        <div class="alert alert-info">
          No sample sheets are currently available for this project.
          <span v-if="sodarContext['perms']['edit_sheet']">
            To add sample sheets, please import it from an existing ISAtab
            investigation.
          </span>
        </div>
      </div>

      <!-- Loading/busy -->
      <div v-else class="w-100 text-center">
        <i class="fa fa-4x fa-spin fa-circle-o-notch text-muted mt-5"></i>
      </div>

    </div> <!-- Main container -->

    <!--<router-view/>-->
  </div>
</template>

<script>
import PageHeader from './components/PageHeader.vue'
import Overview from './components/Overview.vue'
import {AgGridVue} from 'ag-grid-vue'
import DataCellRenderer from './components/renderers/DataCellRenderer.vue'

export default {
  name: 'App',
  data () {
    return {
      projectUuid: null,
      sodarContext: null,
      gridOptions: {
        'study': null,
        'assays': {}
      },
      columnDefs: {
        'study': null,
        'assays': {}
      },
      rowData: {
        'study': null,
        'assays': {}
      },
      hideableAssayCols: {},
      currentStudyUuid: null,
      currentAssayUuid: null,
      gridsLoaded: false,
      gridsBusy: false,
      renderError: null,
      sheetsAvailable: null,
      overviewActive: false,
      appSetupDone: false
    }
  },
  components: {
    PageHeader,
    Overview,
    AgGridVue
  },
  methods: {
    onGridReady (params) {
      // this.gridApi = params.api
      // this.columnApi = params.columnApi
      // this.columnApi.autoSizeAllColumns()
    },

    onFilterChange (event) {
      let gridApi
      if (event.target.id === 'sodar-ss-data-filter-study') {
        gridApi = this.gridOptions['study'].api
      } else if (event.target.id.indexOf('sodar-ss-data-filter-assay') !== -1) {
        let assayUuid = event.target.getAttribute('assay-uuid')
        gridApi = this.gridOptions['assays'][assayUuid].api
      }
      if (gridApi) {
        gridApi.setQuickFilter(event.target.value)
      }
    },

    onAssayHideToggle (event, assayUuid) {
      let columnApi = this.gridOptions['assays'][assayUuid].columnApi
      let hideStatus = this.hideableAssayCols[assayUuid]['hidden']

      // Toggle visibility
      columnApi.setColumnsVisible(
        this.hideableAssayCols[assayUuid]['cols'], hideStatus)
      this.hideableAssayCols[assayUuid]['hidden'] = !hideStatus

      // Update icon
      if (hideStatus) {
        event.currentTarget.children[0].className = 'fa fa-eye text-warning'
      } else {
        event.currentTarget.children[0].className = 'fa fa-eye-slash'
      }
    },

    getGridOptions () {
      return {
        // debug: true,
        pagination: false,
        animateRows: false,
        rowSelection: 'single',
        suppressMovableColumns: true,
        suppressColumnMoveAnimation: true,
        singleClickEdit: false,
        headerHeight: 38,
        rowHeight: 38,
        suppressColumnVirtualisation: false,
        context: {
          componentParent: this
        },
        defaultColDef: {
          editable: false,
          resizable: true,
          sortable: true
        }
      }
    },

    getGridStyle () {
      return 'height: ' + this.sodarContext['table_height'] + 'px;'
    },

    buildColDef (table, assayMode, uuid) {
      let hideableCols = [] // Store hideable assay column fields here

      // Default columns
      let colDef = [
        {
          headerName: 'Row',
          headerClass: ['bg-secondary', 'text-white'],
          suppressSizeToFit: true,
          suppressAutoSize: true,
          children: [
            {
              headerName: '#',
              field: 'rowNum',
              editable: false,
              headerClass: ['bg-light'],
              cellClass: [
                'bg-light', 'text-right', 'text-muted',
                'sodar-ss-data-unselectable'
              ],
              suppressSizeToFit: true,
              suppressAutoSize: true,
              pinned: 'left',
              unselectable: true,
              cellRendererFramework: null,
              minWidth: 65,
              maxWidth: 100,
              width: 65
            }
          ]
        }
      ]

      // Build column data
      let topHeaderLength = table['top_header'].length
      let headerIdx = 0
      let j = headerIdx
      let studySection = true

      // Iterate through top header
      for (let i = 0; i < topHeaderLength; i++) {
        let topHeader = table['top_header'][i]
        let headerGroup = {
          headerName: topHeader['value'],
          headerClass: ['text-white', 'bg-' + topHeader['colour']],
          children: []
        }

        // Iterate through field headers
        while (j < headerIdx + topHeader['colspan']) {
          let fieldHeader = table['field_header'][j]
          // Check if data is present from col_values
          if (table['col_values'][j] === 1) {
            // Define special column properties
            let maxValueLen = fieldHeader['max_value_len']
            let colType = fieldHeader['col_type']
            let minW = this.sodarContext['min_col_width']
            let maxW = this.sodarContext['max_col_width']
            let calcW = maxValueLen * 10 + 25 // Default
            let colWidth

            // External links are a special case
            if (colType === 'EXTERNAL_LINKS') {
              minW = 140
              calcW = maxValueLen * 90
            }

            // Set the final column width
            if (j < table['col_last_vis']) {
              colWidth = calcW < minW ? minW : (calcW > maxW ? maxW : calcW)
            } else { // Last visible column is a special case
              colWidth = Math.max(calcW, minW)
            }

            // Set up column metadata
            let colMeta = []
            for (let k = 0; k < table['table_data'].length; k++) {
              colMeta.push(table['table_data'][k][j])
            }

            // Create header
            let header = {
              headerName: fieldHeader['value'],
              field: 'col' + j.toString(), // TODO: Proper naming
              width: colWidth,
              minWidth: minW,
              cellRendererFramework: DataCellRenderer,
              cellRendererParams: {
                'colType': colType,
                'colMeta': colMeta
              },
              cellClassRules: {
                // Right align numbers (but not for names)
                'text-right': function (params) {
                  return params.colDef.headerName !== 'Name' &&
                    !isNaN(parseFloat(params.value)) &&
                    isFinite(params.value)
                }
              }
            }

            // Hide source and sample columns for assay table
            if (assayMode && studySection && header.headerName !== 'Name') {
              header.hide = true
              hideableCols.push(header.field)
            }

            headerGroup.children.push(header)
          }
          j++
        }

        headerIdx = j
        colDef.push(headerGroup)

        if (topHeader['value'] === 'Sample') {
          studySection = false
        }
      }

      if (assayMode) {
        this.hideableAssayCols[uuid] = {}
        this.hideableAssayCols[uuid]['hidden'] = true
        this.hideableAssayCols[uuid]['cols'] = hideableCols
      }

      return colDef
    },

    buildRowData (table) {
      let rowData = []

      // Iterate through rows
      for (let i = 0; i < table['table_data'].length; i++) {
        let rowCells = table['table_data'][i]
        let row = {
          'rowNum': i + 1
        }
        for (let j = 0; j < rowCells.length; j++) {
          row['col' + j.toString()] = rowCells[j]['value']
        }
        rowData.push(row)
      }
      return rowData
    },

    // Clear current grids
    clearGrids () {
      this.gridOptions = {
        'study': null,
        'assays': {}
      }
      this.columnDefs = {
        'study': null,
        'assays': {}
      }
      this.rowData = {
        'study': null,
        'assays': {}
      }
      this.hideableAssayCols = {}
    },

    getStudy (studyUuid) {
      this.gridsLoaded = false
      this.gridsBusy = true
      this.clearGrids()

      // Set up current study
      this.gridOptions['study'] = this.getGridOptions()
      this.setCurrentStudy(studyUuid)
      this.setPath()

      // Retrieve study and assay tables for current study
      // TODO: Add timeout/retrying
      fetch(this.sodarContext['studies'][studyUuid]['table_url'])
        .then(data => data.json())
        .then(
          data => {
            if ('render_error' in data) {
              this.renderError = data['render_error']
              this.gridsLoaded = false
            } else {
              // Build study
              this.columnDefs['study'] = this.buildColDef(
                data['table_data']['study'], false, studyUuid)
              this.rowData['study'] = this.buildRowData(data['table_data']['study'])

              // Build assays
              for (let assayUuid in data['table_data']['assays']) {
                this.gridOptions['assays'][assayUuid] = this.getGridOptions()
                this.columnDefs['assays'][assayUuid] = this.buildColDef(
                  data['table_data']['assays'][assayUuid], true, assayUuid)
                this.rowData['assays'][assayUuid] = this.buildRowData(
                  data['table_data']['assays'][assayUuid])
              }

              this.renderError = null
              this.gridsLoaded = true
            }
            this.gridsBusy = false

            // Scroll to assay anchor if set
            this.$nextTick(() => {
              this.scrollToCurrentTable()
            })
          }
        )
    },

    setCurrentStudy (studyUuid) {
      this.currentStudyUuid = studyUuid
    },

    setCurrentAssay (assayUuid) {
      this.currentAssayUuid = assayUuid
    },

    scrollToCurrentTable () {
      let anchorElem
      if (this.gridsLoaded && this.currentAssayUuid) {
        anchorElem = document.getElementById(this.currentAssayUuid)
        anchorElem.scrollIntoView()
      } else { // No assay -> scroll to top instead
        anchorElem = document.getElementsByClassName('sodar-app-container')[0]
        anchorElem.scrollTop = 0
      }
    },

    handleStudyNavigation (studyUuid, assayUuid) {
      this.setCurrentAssay(assayUuid)
      let fromOverview = this.overviewActive
      this.overviewActive = false
      this.setPath()
      if (!fromOverview && studyUuid === this.currentStudyUuid) {
        this.scrollToCurrentTable()
      } else {
        this.getStudy(studyUuid) // Will be scrolled after render
      }
    },

    showOverview () {
      this.overviewActive = true
      this.setPath()
      this.clearGrids()
      this.$nextTick(() => {
        this.scrollToCurrentTable()
      })
    },

    // Set path in current URL
    setPath () {
      if (this.overviewActive) {
        this.$router.push({path: '/overview'})
      } else if (this.currentStudyUuid && !this.currentAssayUuid) {
        this.$router.push({path: '/study/' + this.currentStudyUuid})
      } else if (this.currentAssayUuid) {
        this.$router.push({path: '/assay/' + this.currentAssayUuid})
      } else {
        this.$router.push({path: '/'})
      }
    },

    // Set up current page target from URL path
    setTargetByPath () {
      if (this.$route.fullPath.indexOf('/overview') !== -1) {
        this.overviewActive = true
        this.setCurrentStudy(null)
        this.setCurrentAssay(null)
      } else if (this.$route.fullPath.indexOf('/assay/') !== -1) {
        this.overviewActive = false
        this.setCurrentAssay(this.$route.fullPath.substr(7))

        for (let studyUuid in this.sodarContext['studies']) {
          if (this.currentAssayUuid in
              this.sodarContext['studies'][studyUuid]['assays']) {
            this.setCurrentStudy(studyUuid)
            break
          }
        }
      } else if (this.$route.fullPath.indexOf('/study/') !== -1) {
        this.overviewActive = false
        this.setCurrentStudy(this.$route.fullPath.substr(7))
        this.setCurrentAssay(null)
      }
    }
  },
  watch: {
    $route () { // to, from
      const prevStudyUuid = this.currentStudyUuid
      this.setTargetByPath()
      if (this.currentStudyUuid && this.currentStudyUuid !== prevStudyUuid) {
        this.getStudy(this.currentStudyUuid)
      }
    }
  },
  beforeMount () {
    // Get initial context data from the rendered page
    const initialContext = JSON.parse(
      document.getElementById('sodar-ss-app-context')
        .getAttribute('app-context') || '{}')
    this.projectUuid = initialContext['project_uuid']

    const setUpInitialData = async () => {
      // Get full context data from an API view
      // TODO: Add timeout/retrying
      const data = await fetch(initialContext['context_url'])
      const jsonData = await data.json()
      this.sodarContext = JSON.parse(jsonData)

      // Set up current view target based on entry point URL
      this.setTargetByPath()

      // If study UUID isn't found from URL, set the default initial value
      if (!this.currentStudyUuid) {
        this.setCurrentStudy(initialContext['initial_study'])
      }
      this.appSetupDone = true

      if (this.currentStudyUuid) {
        this.sheetsAvailable = true

        if (!this.overviewActive) {
          this.getStudy(this.currentStudyUuid)
        }
      } else {
        this.sheetsAvailable = false
      }
    }
    setUpInitialData()
  }
}
</script>

<style>
/* NOTE: These are just temporary tweaks, scss theme to be created */
/* NOTE: border-collapse will not work as ag-grid is not rendered as a table */

.ag-theme-bootstrap, .ag-theme-bootstrap .ag-header {
  font: inherit;
}

.ag-root {
  border: 0;
}

.ag-header-group-cell {
  border-right: 1px solid #dfdfdf !important;
}

.ag-header-cell {
  border-right: 1px solid #dfdfdf !important;
}

.ag-row {
  background-color: #ffffff !important;
}

.ag-cell {
  border-right: 1px solid #dfdfdf !important;
  border-top: 1px solid #dfdfdf !important;
  line-height: 28px !important;
  padding: 3px;
  height: 38px !important;
}

.ag-cell-focus {
  border: 1px solid #000000 !important;
}

.ag-header-group-text {
  line-height: 38px;
  font-weight: bold;
}

.ag-header-cell-text {
  line-height: 38px;
  font-weight: bold;
}

a.sodar-ss-anchor {
  display: block;
  position: relative;
  top: -75px;
  visibility: hidden;
}

</style>
