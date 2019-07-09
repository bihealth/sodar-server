<template>
  <div id="app">
    <!-- Header -->
    <PageHeader v-if="sodarContext"
                ref="pageHeader"
                :app="getApp()">
    </PageHeader>

    <!-- Main container -->
    <div class="container-fluid sodar-page-container"
         id="sodar-ss-vue-container">

      <!-- Study data rendered -->
      <div v-if="sodarContext &&
                 gridsLoaded &&
                 !renderError &&
                 !activeSubPage"
                 :studyUuid="currentStudyUuid"
           id="sodar-ss-vue-content">

        <!-- Study -->
        <a class="sodar-ss-anchor" :id="currentStudyUuid"></a>
        <div class="row mb-4" id="sodar-ss-section-study">
          <h4 class="font-weight-bold mb-0 text-info">
            <i class="fa fa-fw fa-list-alt"></i>
            Study: {{ sodarContext['studies'][currentStudyUuid]['display_name'] }}
            <i v-if="sodarContext['perms']['is_superuser'] &&
                     sodarContext['studies'][currentStudyUuid]['plugin']"
               class="fa fa-puzzle-piece text-info ml-1"
               :title="sodarContext['studies'][currentStudyUuid]['plugin']"
               v-b-tooltip.hover>
            </i>
          </h4>
          <div class="ml-auto align-middle">
            <span class="mr-2">
              <!-- iRODS dir status / stats badge -->
              <span class="badge-group text-nowrap">
                <span class="badge badge-pill badge-secondary">iRODS</span>
                    <irods-stats-badge
                        v-if="sodarContext['irods_status']"
                        ref="studyStatsBadge"
                        :project-uuid="projectUuid"
                        :irods-status="sodarContext['irods_status']"
                        :irods-path="sodarContext['studies'][currentStudyUuid]['irods_path']">
                    </irods-stats-badge>
                <span v-if="!sodarContext['irods_status']"
                      class="badge badge-pill badge-danger">
                  Not Created
                </span>
              </span>
              <!-- Configuration -->
              <span class="badge-group">
                <span class="badge badge-pill badge-secondary">Config</span>
                <span v-if="sodarContext['configuration']"
                      class="badge badge-pill badge-info">
                  {{ sodarContext['configuration'] }}
                </span>
                <span v-else class="badge badge-pill badge-danger">
                  Unknown
                </span>
              </span>
            </span>
            <irods-buttons
                :app="getApp()"
                :irods-status="sodarContext['irods_status']"
                :irods-backend-enabled="sodarContext['irods_backend_enabled']"
                :irods-webdav-url="sodarContext['irods_webdav_url']"
                :irods-path="sodarContext['studies'][currentStudyUuid]['irods_path']"
                :show-file-list="false">
            </irods-buttons>
          </div>
        </div>

        <div class="card sodar-ss-data-card sodar-ss-data-card-study">
          <div class="card-header">
            <h4>Study Data
              <b-input-group class="sodar-header-input-group pull-right">
                <b-input-group-prepend>
                  <b-button
                      variant="secondary"
                      v-b-tooltip.hover
                      title="Toggle Study Column Visibility"
                      @click="onColumnToggle(currentStudyUuid, false)">
                    <i class="fa fa-eye"></i>
                  </b-button>
                  <b-button
                      variant="secondary"
                      v-b-tooltip.hover
                      title="Download TSV file for Excel"
                      :href="'export/study/' + currentStudyUuid">
                    <i class="fa fa-file-excel-o"></i>
                  </b-button>
                </b-input-group-prepend>
                <b-form-input
                    class="sodar-ss-data-filter"
                    type="text"
                    placeholder="Filter"
                    id="sodar-ss-data-filter-study"
                    @keyup="onFilterChange" />
              </b-input-group>
            </h4>
          </div>
          <div class="card-body p-0">
            <ag-grid-drag-select
                :app="getApp()"
                :grid-options="gridOptions['study']">
              <template slot-scope="{ selectedItems }">
                <ag-grid-vue
                    class="ag-theme-bootstrap"
                    id="sodar-ss-grid-study"
                    :style="getGridStyle()"
                    :columnDefs="columnDefs['study']"
                    :rowData="rowData['study']"
                    :gridOptions="gridOptions['study']"
                    @grid-ready="onGridReady">
                </ag-grid-vue>
              </template>
            </ag-grid-drag-select>
          </div>
        </div>

        <!-- Assays -->
        <span v-for="(assayInfo, assayUuid, index) in
                     sodarContext['studies'][currentStudyUuid]['assays']"
              :key="index">
          <a class="sodar-ss-anchor" :id="assayUuid"></a>
          <div class="row mb-4" :id="'sodar-ss-section-assay-' + assayUuid">
            <h4 class="font-weight-bold mb-0 text-danger">
              <i class="fa fa-fw fa-table"></i>
              Assay: {{ assayInfo['display_name'] }}
              <i v-if="sodarContext['perms']['is_superuser'] &&
                       assayInfo['plugin']"
                 class="fa fa-puzzle-piece text-danger ml-1"
                 :title="assayInfo['plugin']"
                 v-b-tooltip.hover>
              </i>
            </h4>
            <div class="ml-auto">
              <irods-buttons
                  v-if="sodarContext &&
                        gridsLoaded &&
                        !renderError &&
                        !activeSubPage"
                  :app="getApp()"
                  :irods-status="sodarContext['irods_status']"
                  :irods-backend-enabled="sodarContext['irods_backend_enabled']"
                  :irods-webdav-url="sodarContext['irods_webdav_url']"
                  :irodsPath="assayInfo['irods_path']"
                  :showFileList="false">
              </irods-buttons>
            </div>
          </div>

          <extra-content-table
              v-if="extraTables.assays[assayUuid]"
              :app="getApp()"
              :table-data="extraTables.assays[assayUuid]"
              :irods-status="sodarContext['irods_status']"
              :irods-backend-enabled="sodarContext['irods_backend_enabled']"
              :irods-webdav-url="sodarContext['irods_webdav_url']">
          </extra-content-table>

          <div class="card sodar-ss-data-card sodar-ss-data-card-assay">
            <div class="card-header">
              <h4>
                Assay Data
                <b-input-group class="sodar-header-input-group pull-right">
                  <b-input-group-prepend>
                    <b-button
                      variant="secondary"
                      v-b-tooltip.hover
                      title="Toggle Assay Column Visibility"
                      @click="onColumnToggle(assayUuid, true)">
                    <i class="fa fa-eye"></i>
                  </b-button>
                    <b-button
                        variant="secondary"
                        v-b-tooltip.hover
                        title="Download TSV file for Excel"
                        :href="'export/assay/' + assayUuid">
                      <i class="fa fa-file-excel-o"></i>
                    </b-button>
                  </b-input-group-prepend>
                  <b-form-input
                      class="sodar-ss-data-filter"
                      type="text"
                      placeholder="Filter"
                      :id="'sodar-ss-data-filter-assay-' + assayUuid"
                      :assay-uuid="assayUuid"
                      @keyup="onFilterChange" />
                </b-input-group>
              </h4>
            </div>
            <div class="card-body p-0">
              <ag-grid-drag-select
                  :app="getApp()"
                  :grid-options="gridOptions['assays'][assayUuid]">
                <ag-grid-vue
                    class="ag-theme-bootstrap"
                    :id="'sodar-ss-grid-assay-' + assayUuid"
                    :style="getGridStyle()"
                    :columnDefs="columnDefs['assays'][assayUuid]"
                    :rowData="rowData['assays'][assayUuid]"
                    :gridOptions="gridOptions['assays'][assayUuid]"
                    @grid-ready="onGridReady">
                </ag-grid-vue>
              </ag-grid-drag-select>
            </div>
          </div>
        </span>

      </div>

      <!-- Overview subpage -->
      <div v-else-if="activeSubPage === 'overview'" id="sodar-ss-vue-content">
        <Overview :app="getApp()">
        </Overview>
      </div>

      <!-- Parser Warnings subpage -->
      <div v-else-if="activeSubPage === 'warnings'" id="sodar-ss-vue-content">
        <ParserWarnings :app="getApp()">
        </ParserWarnings>
      </div>

      <!-- Render error -->
      <div v-else-if="renderError" id="sodar-ss-vue-content">
        <div class="alert alert-danger" id="sodar-ss-vue-alert-error">
          Error rendering study tables, please check your ISAtab files.
          Exception: {{ renderError }}
        </div>
      </div>

      <!-- No sheets available -->
      <div v-else-if="appSetupDone && !sheetsAvailable"
           id="sodar-ss-vue-content">
        <div class="alert alert-info" id="sodar-ss-vue-alert-empty">
          No sample sheets are currently available for this project.
          <span v-if="sodarContext['perms']['edit_sheet']">
            To add sample sheets, please import it from an existing ISAtab
            investigation.
          </span>
        </div>
      </div>

      <!-- Loading/busy -->
      <div v-else class="w-100 text-center" id="sodar-ss-vue-wait">
        <i class="fa fa-4x fa-spin fa-circle-o-notch text-muted mt-5"></i>
      </div>

    </div> <!-- Main container -->

    <!-- iRODS directory listing modal -->
    <irods-dir-modal
        v-if="sodarContext"
        :project-uuid="projectUuid"
        :irods-webdav-url="sodarContext['irods_webdav_url']"
        ref="dirModalRef">
    </irods-dir-modal>

    <!-- Modal for study shortcuts -->
    <shortcut-modal
        v-if="sodarContext && currentStudyUuid"
        :project-uuid="projectUuid"
        :study-uuid="currentStudyUuid"
        :irods-webdav-url="sodarContext['irods_webdav_url']"
        ref="shortcutModalRef">
    </shortcut-modal>

    <column-toggle-modal
      v-if="sodarContext && currentStudyUuid"
      :app="getApp()"
      ref="columnToggleModalRef">
    </column-toggle-modal>

    <!--<router-view/>-->
  </div>
</template>

<script>
import PageHeader from './components/PageHeader.vue'
import Overview from './components/Overview.vue'
import ParserWarnings from './components/ParserWarnings.vue'
import IrodsButtons from './components/IrodsButtons.vue'
import IrodsDirModal from './components/IrodsDirModal.vue'
import ShortcutModal from './components/ShortcutModal.vue'
import ColumnToggleModal from './components/ColumnToggleModal'
import IrodsStatsBadge from './components/IrodsStatsBadge.vue'
import ExtraContentTable from './components/ExtraContentTable.vue'
import {AgGridVue} from 'ag-grid-vue'
import DataCellRenderer from './components/renderers/DataCellRenderer.vue'
import IrodsButtonsRenderer from './components/renderers/IrodsButtonsRenderer.vue'
import ShortcutButtonsRenderer from './components/renderers/ShortcutButtonsRenderer.vue'
import AgGridDragSelect from './components/AgGridDragSelect.vue'

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
      columnValues: {
        'study': null,
        'assays': {}
      },
      extraTables: {
        'study': null,
        'assays': {}
      },
      currentStudyUuid: null,
      currentAssayUuid: null,
      gridsLoaded: false,
      gridsBusy: false,
      renderError: null,
      sheetsAvailable: null,
      activeSubPage: null,
      appSetupDone: false
    }
  },
  components: {
    PageHeader,
    Overview,
    ParserWarnings,
    IrodsButtons,
    IrodsDirModal,
    ShortcutModal,
    ColumnToggleModal,
    IrodsStatsBadge,
    ExtraContentTable,
    AgGridVue,
    AgGridDragSelect
  },
  methods: {

    /* Event Handlers ------------------------------------------------------- */

    onGridReady (params) {
      // this.gridApi = params.api
      // this.columnApi = params.columnApi
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

    onColumnToggle (uuid, assayMode) {
      this.$refs.columnToggleModalRef.showModal(uuid, assayMode)
    },

    /* Grid Setup ----------------------------------------------------------- */

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
              headerClass: ['sodar-ss-data-header'],
              cellClass: [
                'text-right', 'text-muted',
                'sodar-ss-data-unselectable',
                'sodar-ss-data-row-cell'
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
            calcW = maxValueLen * 120
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
            field: 'col' + j.toString(),
            width: colWidth,
            minWidth: minW,
            hide: !table['col_values'][j], // Hide by default if empty
            headerClass: ['sodar-ss-data-header'],
            cellRendererFramework: DataCellRenderer,
            cellRendererParams: {
              'app': this,
              'colType': colType,
              'colMeta': colMeta
            },
            cellClass: [
              'sodar-ss-data-cell',
              'text-' + fieldHeader['align']
            ]
          }

          // Make source name column pinned, disable hover
          // HACK: also create new header group to avoid name duplication
          if (j === 0) {
            header.pinned = 'left'
            header.cellRendererParams['enableHover'] = false
            headerGroup.children.push(header)
            colDef.push(headerGroup)
            headerGroup = {
              headerName: '',
              headerClass: ['bg-' + topHeader['colour']],
              children: []
            }
          }

          // Hide source and sample columns for assay table
          if (assayMode && studySection && header.headerName !== 'Name') {
            header.hide = true
          }

          if (j > 0) {
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

      if (!assayMode &&
          table.hasOwnProperty('shortcuts') &&
          table['shortcuts'] != null) {
        let shortcutHeaderGroup = {
          headerName: 'Links',
          headerClass: [
            'text-white',
            'bg-secondary',
            'sodar-ss-data-links-top'
          ],
          children: [
            {
              headerName: 'Study',
              field: 'shortcutLinks',
              editable: false,
              headerClass: [
                'sodar-ss-data-header',
                'sodar-ss-data-links-header'
              ],
              cellClass: [
                'sodar-ss-data-links-cell',
                'sodar-ss-data-unselectable'
              ],
              suppressSizeToFit: true,
              suppressAutoSize: true,
              resizable: true,
              sortable: false,
              pinned: 'right',
              unselectable: true,
              width: 45 * Object.keys(table['shortcuts']['schema']).length,
              minWidth: 90,
              cellRendererFramework: ShortcutButtonsRenderer,
              cellRendererParams: {
                schema: table['shortcuts']['schema'],
                modalComponent: this.$refs.shortcutModalRef
              }
            }
          ]
        }
        colDef.push(shortcutHeaderGroup)
      }

      if (assayMode) {
        let assayContext = this.sodarContext['studies'][this.currentStudyUuid]['assays'][uuid]
        if (this.sodarContext['irods_status'] && assayContext['display_row_links']) {
          let assayIrodsPath = assayContext['irods_path']
          let irodsHeaderGroup = {
            headerName: 'iRODS',
            headerClass: [
              'text-white',
              'bg-secondary',
              'sodar-ss-data-links-top'
            ],
            children: [
              {
                headerName: 'Links',
                field: 'irodsLinks',
                editable: false,
                headerClass: [
                  'sodar-ss-data-header',
                  'sodar-ss-data-links-header'
                ],
                cellClass: [
                  'sodar-ss-data-links-cell',
                  'sodar-ss-data-unselectable'
                ],
                suppressSizeToFit: true,
                suppressAutoSize: true,
                resizable: true,
                sortable: false,
                pinned: 'right',
                unselectable: true,
                cellRendererFramework: IrodsButtonsRenderer,
                cellRendererParams: {
                  app: this,
                  irodsStatus: this.sodarContext['irods_status'],
                  irodsBackendEnabled: this.sodarContext['irods_backend_enabled'],
                  irodsWebdavUrl: this.sodarContext['irods_webdav_url'],
                  assayIrodsPath: assayIrodsPath,
                  showFileList: true,
                  modalComponent: this.$refs.dirModalRef
                },
                width: 152, // TODO: Attempt to calculate this somehow?
                minWidth: 152
              }
            ]
          }
          colDef.push(irodsHeaderGroup)
        }
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

        // Add study shortcut field
        if (table.hasOwnProperty('shortcuts') && table['shortcuts'] != null) {
          row['shortcutLinks'] = table['shortcuts']['data'][i]
        }

        // Add iRODS field
        if (this.sodarContext['irods_status'] && 'irods_paths' in table &&
            table['irods_paths'].length > 0) {
          row['irodsLinks'] = table['irods_paths'][i]
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
      this.columnValues = {
        'study': null,
        'assays': {}
      }
      this.extraTables = {
        'study': null,
        'assays': {}
      }
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
      fetch(this.sodarContext['studies'][studyUuid]['table_url'], {
        credentials: 'same-origin'
      })
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
              this.columnValues['study'] = data['table_data']['study']['col_values']

              // Build assays
              for (let assayUuid in data['table_data']['assays']) {
                this.gridOptions['assays'][assayUuid] = this.getGridOptions()
                this.columnDefs['assays'][assayUuid] = this.buildColDef(
                  data['table_data']['assays'][assayUuid], true, assayUuid)
                this.rowData['assays'][assayUuid] = this.buildRowData(
                  data['table_data']['assays'][assayUuid])
                this.columnValues['assays'][assayUuid] =
                  data['table_data']['assays'][assayUuid]['col_values']

                // Get extra table
                if ('extra_table' in data['table_data']['assays'][assayUuid]) {
                  this.extraTables.assays[assayUuid] =
                      data['table_data']['assays'][assayUuid]['extra_table']
                }
              }

              this.renderError = null
              this.gridsLoaded = true
            }
            this.gridsBusy = false

            // Perform actions after render
            this.$nextTick(() => {
              // Scroll to assay anchor if set
              this.scrollToCurrentTable()

              // Update study badge stats
              if (this.sodarContext['irods_status']) {
                this.$refs.studyStatsBadge.updateStats() // TODO: Set up timer
              }
            })
          }
        )
    },

    /* Navigation ----------------------------------------------------------- */

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
      let fromSubPage = this.activeSubPage
      this.activeSubPage = null
      this.setPath()
      if (!fromSubPage && studyUuid === this.currentStudyUuid) {
        this.scrollToCurrentTable()
      } else {
        this.getStudy(studyUuid) // Will be scrolled after render
      }
    },

    showSubPage (pageId) {
      this.activeSubPage = pageId
      this.setPath()
      this.clearGrids() // TODO: Should keep in memory
      this.$nextTick(() => {
        this.scrollToCurrentTable()
      })
    },

    // Set path in current URL
    setPath () {
      if (this.activeSubPage) {
        this.$router.push({path: '/' + this.activeSubPage})
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
      let pageId = this.$route.fullPath.split('/')[1]

      if (this.$route.fullPath.indexOf('/study/') === -1 &&
          this.$route.fullPath.indexOf('/assay/') === -1 &&
          pageId) {
        this.showSubPage(pageId)
        this.setCurrentStudy(null)
        this.setCurrentAssay(null)
      } else if (this.$route.fullPath.indexOf('/assay/') !== -1) {
        this.activeSubPage = null
        this.setCurrentAssay(this.$route.fullPath.substr(7))

        for (let studyUuid in this.sodarContext['studies']) {
          if (this.currentAssayUuid in
              this.sodarContext['studies'][studyUuid]['assays']) {
            this.setCurrentStudy(studyUuid)
            break
          }
        }
      } else if (this.$route.fullPath.indexOf('/study/') !== -1) {
        this.activeSubPage = null
        this.setCurrentStudy(this.$route.fullPath.substr(7))
        this.setCurrentAssay(null)
      }
    },

    /* Display -------------------------------------------------------------- */

    showNotification (message, delay) {
      this.$refs.pageHeader.showNotification(message, delay)
    },

    /* Data and App Access -------------------------------------------------- */

    getGridOptionsByUuid (uuid) {
      if (uuid === this.currentStudyUuid) {
        return this.gridOptions['study'].columnApi
      } else if (uuid in this.gridOptions['assays']) {
        return this.gridOptions['assays'][uuid].columnApi
      }
    },

    // Workaround for #520 where "this" doesn't always appear initialized in templates
    getApp () {
      return this
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
      const data = await fetch(initialContext['context_url'], {
        credentials: 'same-origin'
      })
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

        if (!this.activeSubPage) {
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
  font: inherit !important;
}

.ag-root {
  border: 0 !important;
}

.ag-header-group-cell {
  border-right: 1px solid #dfdfdf !important;
}

.ag-header-cell {
  border-right: 1px solid #dfdfdf !important;
}

.ag-full-width-container {
  border-bottom: 1px solid #dfdfdf !important;
}

.ag-row {
  background-color: #ffffff !important;
}

.ag-cell {
  border-right: 1px solid #dfdfdf !important;
  border-top: 1px solid #dfdfdf !important;
  border-left: 1px solid transparent !important;
  border-bottom: 1px solid transparent !important;
  line-height: 28px !important;
  padding: 3px;
  height: 38px !important;
}

.sodar-ss-data-header {
  background-color: #f7f7f7 !important;
}

.sodar-ss-data-cell:focus {
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

.ag-pinned-right-header {
  border: 0 !important;
}

a.sodar-ss-anchor {
  display: block;
  position: relative;
  top: -75px;
  visibility: hidden;
}

.sodar-ss-data-links-top {
  border-left: 1px solid #dfdfdf !important;
  border-right: 1px solid #6c757d !important;
}

.sodar-ss-data-links-header {
  border-left: 1px solid #dfdfdf !important;
  border-right: 0 !important;
}

.sodar-ss-data-links-cell {
  border-left: 1px solid #dfdfdf !important;
  border-top: 1px solid #dfdfdf !important;
  border-right: 0 !important;
  border-bottom: 0 !important;
}

.sodar-ss-data-links-cell:focus {
  border-left: 1px solid #dfdfdf !important;
  border-top: 1px solid #dfdfdf !important;
  border-bottom: 0 !important;
}

.sodar-ss-data-row-cell:focus {
  border-right: 1px solid #dfdfdf !important;
  border-top: 1px solid #dfdfdf !important;
  border-left: 0 !important;
  border-bottom: 0 !important;
}

.agds-selected {
  background-color: #ffe8e8 !important;
}

</style>
