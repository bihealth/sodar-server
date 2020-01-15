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

      <!-- Alerts from context API view -->
      <div v-if="sodarContext &&
                 sodarContext['perms']['edit_sheet'] &&
                 sodarContext['alerts'].length"
           class="pb-2"
           id="sodar-ss-vue-alert-container">
        <div v-for="(alertData, alertIdx) in sodarContext['alerts']"
             :key="alertIdx"
             :class="'alert sodar ss-vue-alert alert-' + alertData['level']">
          {{ alertData['text'] }}
        </div>
      </div>

      <!-- Study data rendered -->
      <div v-if="sodarContext &&
                 gridsLoaded &&
                 !renderError &&
                 !activeSubPage"
                 :studyUuid="currentStudyUuid"
           :id="contentId">

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
              <span v-if="!editMode" class="badge-group text-nowrap">
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
                      title="Download table as Excel file (Note: not ISAtab compatible)"
                      :href="'export/excel/study/' + currentStudyUuid">
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
                :uuid="currentStudyUuid">
              <template slot-scope="{ selectedItems }">
                <ag-grid-vue
                    class="ag-theme-bootstrap"
                    id="sodar-ss-grid-study"
                    ref="studyGrid"
                    :style="getGridStyle()"
                    :columnDefs="columnDefs['study']"
                    :rowData="rowData['study']"
                    :gridOptions="gridOptions['study']"
                    :frameworkComponents="frameworkComponents"
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
              v-if="!editMode && extraTables.assays[assayUuid]"
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
                        title="Download table as Excel file (Note: not ISAtab compatible)"
                        :href="'export/excel/assay/' + assayUuid">
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
                  :uuid="assayUuid">
                <ag-grid-vue
                    class="ag-theme-bootstrap"
                    :id="'sodar-ss-grid-assay-' + assayUuid"
                    :ref="'assayGrid' + assayUuid"
                    :style="getGridStyle()"
                    :columnDefs="columnDefs['assays'][assayUuid]"
                    :rowData="rowData['assays'][assayUuid]"
                    :gridOptions="gridOptions['assays'][assayUuid]"
                    :frameworkComponents="frameworkComponents"
                    @grid-ready="onGridReady">
                </ag-grid-vue>
              </ag-grid-drag-select>
            </div>
          </div>
        </span>

      </div>

      <!-- Overview subpage -->
      <div v-else-if="activeSubPage === 'overview'" :id="contentId">
        <Overview :app="getApp()">
        </Overview>
      </div>

      <!-- Parser Warnings subpage -->
      <div v-else-if="activeSubPage === 'warnings'" :id="contentId">
        <ParserWarnings :app="getApp()">
        </ParserWarnings>
      </div>

      <!-- Render error -->
      <div v-else-if="renderError" :id="contentId">
        <div class="alert alert-danger" id="sodar-ss-vue-alert-error">
          Error rendering study tables, please check your ISAtab files.
          Exception: {{ renderError }}
        </div>
      </div>

      <!-- No sheets available -->
      <div v-else-if="appSetupDone && !sheetsAvailable"
           :id="contentId">
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

    <!-- Modal for column visibility toggling -->
    <column-toggle-modal
        v-if="sodarContext && currentStudyUuid"
        :app="getApp()"
        ref="columnToggleModalRef">
    </column-toggle-modal>

    <!-- Editing: Column configuration modal -->
    <column-config-modal
        v-if="editMode && sodarContext['perms']['manage_sheet']"
        :app="getApp()"
        :project-uuid="projectUuid"
        :study-uuid="currentStudyUuid"
        ref="columnConfigModal">
    </column-config-modal>

    <!-- Editing: Editor help modal -->
    <editor-help-modal
        v-if="editMode"
        ref="editorHelpModal">
    </editor-help-modal>

    <!--<router-view/>-->
  </div>
</template>

<script>
import PageHeader from './components/PageHeader.vue'
import Overview from './components/Overview.vue'
import ParserWarnings from './components/ParserWarnings.vue'
import IrodsButtons from './components/IrodsButtons.vue'
import IrodsDirModal from './components/modals/IrodsDirModal.vue'
import ShortcutModal from './components/modals/ShortcutModal.vue'
import ColumnToggleModal from './components/modals/ColumnToggleModal.vue'
import ColumnConfigModal from './components/modals/ColumnConfigModal.vue'
import EditorHelpModal from './components/modals/EditorHelpModal.vue'
import IrodsStatsBadge from './components/IrodsStatsBadge.vue'
import ExtraContentTable from './components/ExtraContentTable.vue'
import {AgGridVue} from 'ag-grid-vue'
import DataCellRenderer from './components/renderers/DataCellRenderer.vue'
import IrodsButtonsRenderer from './components/renderers/IrodsButtonsRenderer.vue'
import ShortcutButtonsRenderer from './components/renderers/ShortcutButtonsRenderer.vue'
import FieldHeaderEditRenderer from './components/renderers/FieldHeaderEditRenderer'
import DataCellEditor from './components/editors/DataCellEditor.vue'
import AgGridDragSelect from './components/AgGridDragSelect.vue'

export default {
  name: 'App',
  data () {
    return {
      projectUuid: null,
      sodarContext: null,
      // Initial grid options
      // NOTE: These will NOT be updated, use getGridOptionsByUuid() instead
      gridOptions: {
        'study': null,
        'assays': {}
      },
      // Column definitions are managed here
      columnDefs: {
        'study': null,
        'assays': {}
      },
      // NOTE: These will NOT be updated, use getGridOptionsByUuid().rowData
      rowData: {
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
      appSetupDone: false,
      selectEnabled: true,
      editMode: false,
      editStudyData: false,
      editStudyConfig: null,
      editDataUpdated: false,
      contentId: 'sodar-ss-vue-content',
      /* NOTE: cell editor only works if provided through frameworkComponents? */
      frameworkComponents: {
        dataCellEditor: DataCellEditor
      }
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
    ColumnConfigModal,
    EditorHelpModal,
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
      if (event.currentTarget.id === 'sodar-ss-data-filter-study') {
        gridApi = this.getGridOptionsByUuid(this.currentStudyUuid).api
      } else if (event.currentTarget.id.indexOf('sodar-ss-data-filter-assay') !== -1) {
        let assayUuid = event.currentTarget.getAttribute('assay-uuid')
        gridApi = this.getGridOptionsByUuid(assayUuid).api
      }
      if (gridApi) {
        gridApi.setQuickFilter(event.currentTarget.value)
      }
    },

    onColumnToggle (uuid, assayMode) {
      this.$refs.columnToggleModalRef.showModal(uuid, assayMode)
    },

    /* Grid Helpers --------------------------------------------------------- */

    // Helper to get flat value for
    getFlatValue (value) {
      if (Array.isArray(value) && value.length > 0) {
        if (value[0].hasOwnProperty('name')) {
          return value.map(d => d['name']).join(';')
        }
      } else {
        return value
      }
    },

    // Custom comparator for data cells
    dataCellCompare (dataA, dataB) {
      let valueA = dataA['value']
      let valueB = dataB['value']

      // Integer/float sort
      if (dataA['colType']) {
        return parseFloat(valueA) - parseFloat(valueB)
      }

      // Join array values into strings
      valueA = this.getFlatValue(valueA)
      valueB = this.getFlatValue(valueB)

      // String sort
      return valueA.localeCompare(valueB)
    },

    // Custom filter value for data cells (fix for #686)
    dataCellFilterValue (params) {
      return this.getFlatValue(params.data[params.column.colId].value)
    },

    /* Grid Setup ----------------------------------------------------------- */

    initGridOptions (editMode) {
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
          sortable: !editMode
        }
      }
    },

    getGridStyle () {
      return 'height: ' + this.sodarContext['table_height'] + 'px;'
    },

    buildColDef (table, assayMode, uuid, editMode) {
      // Currently uneditable fields
      const uneditableFields = ['name', 'protocol', 'performer', 'perform date']

      // Default columns
      let colDef = []
      let editFieldConfig

      let rowHeaderGroup = {
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

      // Editing: gray out row column to avoid confusion
      if (this.editMode) {
        rowHeaderGroup.children[0].cellClass.push('bg-light')
      }
      colDef.push(rowHeaderGroup)

      // Sample sheet columns
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
        let configFieldIdx = 0 // For config management

        // Iterate through field headers
        while (j < headerIdx + topHeader['colspan']) {
          let fieldHeader = table['field_header'][j]

          // Define special column properties
          let maxValueLen = fieldHeader['max_value_len']
          let colType = fieldHeader['col_type']

          let colAlign
          if (['UNIT', 'NUMERIC'].includes(colType)) {
            colAlign = 'right'
          } else {
            colAlign = 'left'
          }

          let minW = this.sodarContext['min_col_width']
          let maxW = this.sodarContext['max_col_width']
          let calcW = maxValueLen * 10 + 25 // Default
          let colWidth
          let fieldEditable = false

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

          // Get editFieldConfig if editing
          if (editMode && this.editStudyConfig) {
            editFieldConfig = null
            let editNode = null
            let studyNodeLen = this.editStudyConfig['nodes'].length

            if (!assayMode || i < studyNodeLen) {
              editNode = this.editStudyConfig['nodes'][i]
            } else {
              editNode = this.editStudyConfig['assays'][uuid]['nodes'][i - studyNodeLen]
            }

            if (editNode) {
              for (let k = 0; k < editNode['fields'].length; k++) {
                let f = editNode['fields'][k]

                if (f['name'] === fieldHeader['name'] &&
                    f['type'] === fieldHeader['type']) {
                  editFieldConfig = f
                  break
                }
              }
            }
          }

          if (editFieldConfig &&
              editFieldConfig.hasOwnProperty('editable')) {
            fieldEditable = editFieldConfig['editable']
          }

          // Create data header
          let header = {
            headerName: fieldHeader['value'],
            field: 'col' + j.toString(),
            width: colWidth,
            minWidth: minW,
            hide: !fieldEditable && !table['col_values'][j], // Hide if empty and not editing
            headerClass: ['sodar-ss-data-header'],
            cellRendererFramework: DataCellRenderer,
            cellRendererParams: {
              'app': this // NOTE: colType no longer necessary, passed to cell
            },
            cellClass: [
              'sodar-ss-data-cell',
              'text-' + colAlign
            ],
            comparator: this.dataCellCompare,
            filterValueGetter: this.dataCellFilterValue
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

          // Editing: set up field and its header for editing
          if (editMode) {
            // Set header renderer for fields we can manage
            if (this.sodarContext['perms']['manage_sheet'] &&
                !uneditableFields.includes(fieldHeader['value'].toLowerCase()) &&
                !['EXTERNAL_LINKS', 'ONTOLOGY'].includes(colType)) {
              let configAssayUuid = assayMode ? uuid : null
              let configNodeIdx = i
              let defFieldIdx = configFieldIdx

              if (i === 0) { // Subtract source name if in source
                defFieldIdx = configFieldIdx - 1
              }

              if (assayMode) {
                // NOTE: -2 because of row column and split source column
                let studyNodeLen = this.columnDefs['study'].length - 2
                if (configNodeIdx < studyNodeLen) {
                  configAssayUuid = null
                } else {
                  configNodeIdx = i - studyNodeLen
                }
              }

              header.headerComponentFramework = FieldHeaderEditRenderer
              header.headerComponentParams = {
                'modalComponent': this.$refs.columnConfigModal,
                'colType': colType,
                'fieldConfig': editFieldConfig,
                'assayUuid': configAssayUuid,
                'configNodeIdx': configNodeIdx,
                'configFieldIdx': configFieldIdx,
                'defNodeIdx': i + 2, // Add 2 for row & source groups
                'defFieldIdx': defFieldIdx
              }
              header.width = header.width + 20 // Fit button in header
              header.minWidth = header.minWidth + 20
            }

            // Set up field editing
            if (editFieldConfig &&
                !['Name', 'Protocol'].includes(fieldHeader['value'])) {
              header.editable = fieldEditable
              header.cellEditor = 'dataCellEditor'
              header.cellEditorParams = {
                'app': this.getApp(),
                // Header information to be passed for calling server
                'headerInfo': {
                  'header_name': fieldHeader['name'],
                  'header_type': fieldHeader['type'],
                  'header_field': header.field, // For updating other cells
                  'obj_cls': fieldHeader['obj_cls']
                },
                'renderInfo': {
                  'align': colAlign,
                  'width': colWidth
                },
                // Editor configuration to be passed to DataCellEditor
                'editConfig': editFieldConfig
              }
            }
            if (!fieldEditable) { // Not editable at initial loading
              header.cellClass = header.cellClass.concat(['bg-light', 'text-muted'])
            }
          }

          if (j > 0) {
            headerGroup.children.push(header)
          }

          j++
          configFieldIdx += 1
        }

        headerIdx = j
        colDef.push(headerGroup)

        if (topHeader['value'] === 'Sample') {
          studySection = false
        }
      }

      // Study shortcut column
      if (!this.editMode &&
          !assayMode &&
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

      if (!this.editMode && assayMode) {
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
          let cellVal = rowCells[j]
          // Copy col_type info to each cell (comparator can't access colDef)
          cellVal['colType'] = table['field_header'][j]['col_type']
          row['col' + j.toString()] = cellVal
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
      this.extraTables = {
        'study': null,
        'assays': {}
      }
    },

    getStudy (studyUuid, editMode) {
      this.gridsLoaded = false
      this.gridsBusy = true
      this.clearGrids()

      // Set up current study
      this.gridOptions['study'] = this.initGridOptions(editMode)
      this.setCurrentStudy(studyUuid)
      this.setPath()

      // Retrieve study and assay tables for current study
      // TODO: Add timeout/retrying
      let url = this.sodarContext['studies'][studyUuid]['table_url']

      if (editMode) {
        url = url + '?edit=1'
      }

      fetch(url, {credentials: 'same-origin'})
        .then(data => data.json())
        .then(
          data => {
            if ('render_error' in data) {
              this.renderError = data['render_error']
              this.gridsLoaded = false
            } else {
              // Editing: Get study config
              if (editMode && data.hasOwnProperty('study_config')) {
                this.editStudyConfig = data['study_config']
              }

              // Build study
              this.columnDefs['study'] = this.buildColDef(
                data['tables']['study'], false, studyUuid, editMode)
              this.rowData['study'] = this.buildRowData(data['tables']['study'])

              // Build assays
              for (let assayUuid in data['tables']['assays']) {
                this.gridOptions['assays'][assayUuid] = this.initGridOptions(editMode)
                this.columnDefs['assays'][assayUuid] = this.buildColDef(
                  data['tables']['assays'][assayUuid], true, assayUuid, editMode)
                this.rowData['assays'][assayUuid] = this.buildRowData(
                  data['tables']['assays'][assayUuid])

                // Get extra table
                if ('extra_table' in data['tables']['assays'][assayUuid]) {
                  this.extraTables.assays[assayUuid] =
                      data['tables']['assays'][assayUuid]['extra_table']
                }
              }

              this.editStudyData = this.editMode
              this.renderError = null
              this.gridsLoaded = true
            }
            this.gridsBusy = false

            // Perform actions after render
            this.$nextTick(() => {
              // Scroll to assay anchor if set
              this.scrollToCurrentTable()

              // Update study badge stats
              if (this.sodarContext['irods_status'] && this.$refs.studyStatsBadge) {
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

      if (!fromSubPage &&
          studyUuid === this.currentStudyUuid &&
          this.editMode === this.editStudyData) {
        this.scrollToCurrentTable()
      } else {
        this.getStudy(studyUuid, this.editMode) // Will be scrolled after render
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
      let path = '/'

      if (this.activeSubPage) {
        path = '/' + this.activeSubPage
      } else if (this.currentStudyUuid && !this.currentAssayUuid) {
        path = '/study/' + this.currentStudyUuid
      } else if (this.currentAssayUuid) {
        path = '/assay/' + this.currentAssayUuid
      }
      // TODO: Why does this raise NavigationDuplicated? (see issue #667)
      this.$router.push({path: path}).catch(error => error)
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

    toggleEditMode () {
      this.editMode = !this.editMode

      if (this.editMode) {
        if (!this.currentStudyUuid) {
          this.currentStudyUuid = Object.keys(this.sodarContext['studies'])[0]
        }
        this.handleStudyNavigation(this.currentStudyUuid)
      } else {
        this.handleFinishEditing() // Call actions for finishing editing
        this.selectEnabled = true // Just in case
        if (!this.editMode && this.currentStudyUuid) {
          this.handleStudyNavigation(this.currentStudyUuid, this.currentAssayUuid)
        }
      }
      this.editDataUpdated = false
    },

    /* Display -------------------------------------------------------------- */

    showNotification (message, variant, delay) {
      // NOTE: This is a shortcut for the NotifyBadge component in PageHeader
      this.$refs.pageHeader.$refs.notifyBadge.show(
        message, variant, delay)
    },

    /* Editing -------------------------------------------------------------- */

    handleCellEdit (upDataArr, refreshCells) {
      // TODO: Add timeout / retrying
      // TODO: Cleanup unnecessary fields from JSON
      // TODO: In the future, add edited info in a queue and save periodically
      if (!Array.isArray(upDataArr)) {
        upDataArr = [upDataArr]
      }

      fetch('/samplesheets/api/edit/post/' + this.projectUuid, {
        method: 'POST',
        body: JSON.stringify({'updated_cells': upDataArr}),
        credentials: 'same-origin',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
          'X-CSRFToken': this.sodarContext['csrf_token']
        }
      }).then(data => data.json())
        .then(
          data => {
            if (data['message'] === 'ok') {
              this.showNotification('Changes Saved', 'success', 1000)
              this.editDataUpdated = true

              // Update other occurrences of cell in UI
              let gridUuids = this.getStudyGridUuids()
              for (let i = 0; i < gridUuids.length; i++) {
                this.updateCellUIValues(
                  this.getGridOptionsByUuid(
                    gridUuids[i]).api, upDataArr, refreshCells)
              }
            } else {
              console.log('Save status: ' + data['message']) // DEBUG
              this.showNotification('Saving Failed', 'danger', 1000)
              // TODO: Mark invalid/unsaved field(s) in UI
            }
          }
        ).catch(function (error) {
          console.log('Error saving data: ' + error.message)
        })
    },

    updateCellUIValues (gridApi, upDataArr, refreshCells) {
      for (let i = 0; i < upDataArr.length; i++) {
        let upData = upDataArr[i]
        let fieldId = upData['header_field']

        gridApi.forEachNode(function (rowNode) {
          let value = rowNode.data[fieldId]
          if (value &&
              value['uuid'] === upData['uuid'] &&
              value['value'] === upData['og_value']) {
            value['value'] = upData['value']
            value['unit'] = upData['unit']
            rowNode.setDataValue(fieldId, value)
          }
        })

        if (refreshCells) {
          gridApi.refreshCells({'columns': [fieldId], 'force': true})
        }
      }
    },

    refreshField (fieldId) {
      let gridUuids = this.getStudyGridUuids()

      for (let i = 0; i < gridUuids.length; i++) {
        this.getGridOptionsByUuid(gridUuids[i]).api.refreshCells(
          {'columns': [fieldId], 'force': true})
      }
    },

    handleFinishEditing () {
      fetch('/samplesheets/api/edit/finish/' + this.projectUuid, {
        method: 'POST',
        body: JSON.stringify({'updated': this.editDataUpdated}),
        credentials: 'same-origin',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
          'X-CSRFToken': this.sodarContext['csrf_token']
        }
      }).then(data => data.json())
        .then(
          data => {
            if (data['message'] === 'ok') {
              this.showNotification('Finished Editing', 'success', 1000)
            } else {
              console.log('Finish status: ' + data['message']) // DEBUG
              this.showNotification('Saving Version Failed', 'danger', 1000)
            }
          }
        ).catch(function (error) {
          console.log('Error saving version: ' + error.message)
          this.showNotification('Finishing Error', 'danger', 2000)
        })

      this.editStudyConfig = null
    },

    setDataUpdated (updated) {
      this.editDataUpdated = updated
    },

    /* Data and App Access -------------------------------------------------- */

    // Return array of UUIDs for the current study and all assays
    getStudyGridUuids () {
      if (!this.currentStudyUuid) {
        return null
      }
      let uuids = [this.currentStudyUuid]
      for (var k in this.columnDefs['assays']) {
        uuids.push(k)
      }
      return uuids
    },

    getGridOptionsByUuid (uuid) {
      if (uuid === this.currentStudyUuid) {
        return this.$refs['studyGrid'].gridOptions
      } else if (uuid in this.columnDefs['assays']) {
        // TODO: Why is this an array?
        return this.$refs['assayGrid' + uuid][0].gridOptions
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
  border: 1px solid #6c757d !important;
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
  background-color: #e2f0ff !important;
}

div.sodar-ss-data {
  width: 100%;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  padding-right: 3px;
  border: 1px solid transparent;
}

div.sodar-ss-data-hover {
  z-index: 1100;
  width: auto;
  position: fixed;
  background-color: #ffffe0;
  border: 1px solid #dfdfdf;
  box-shadow: 0 3px 3px -3px #909090;
}

.sodar-ss-data-btn {
  height: 28px;
  line-height: 27px;
  margin-top: 5px;
  padding-top: 0;
  color: #ffffff !important;
}

</style>
