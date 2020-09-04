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
                 sodarContext.perms.edit_sheet &&
                 sodarContext.alerts.length"
           class="pb-2"
           id="sodar-ss-vue-alert-container">
        <div v-for="(alertData, alertIdx) in sodarContext.alerts"
             :key="alertIdx"
             :class="'alert sodar ss-vue-alert alert-' + alertData.level">
          {{ alertData.text }}
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
            Study: {{ sodarContext.studies[currentStudyUuid].display_name }}
            <i v-if="sodarContext.perms.is_superuser &&
                     sodarContext.studies[currentStudyUuid].plugin"
               class="fa fa-puzzle-piece text-info ml-1"
               :title="sodarContext.studies[currentStudyUuid].plugin"
               v-b-tooltip.hover>
            </i>
          </h4>
          <div class="ml-auto align-middle">
            <span class="mr-2">
              <!-- iRODS collection status / stats badge -->
              <span v-if="!editMode" class="badge-group text-nowrap">
                <span class="badge badge-pill badge-secondary">iRODS</span>
                    <irods-stats-badge
                        v-if="sodarContext.irods_status"
                        ref="studyStatsBadge"
                        :project-uuid="projectUuid"
                        :irods-status="sodarContext.irods_status"
                        :irods-path="sodarContext.studies[currentStudyUuid].irods_path">
                    </irods-stats-badge>
                <span v-if="!sodarContext.irods_status"
                      class="badge badge-pill badge-danger">
                  Not Created
                </span>
              </span>
              <!-- Configuration -->
              <span class="badge-group">
                <span class="badge badge-pill badge-secondary">Config</span>
                <span v-if="sodarContext.configuration"
                      class="badge badge-pill badge-info">
                  {{ sodarContext.configuration }}
                </span>
                <span v-else class="badge badge-pill badge-danger">
                  Unknown
                </span>
              </span>
            </span>
            <irods-buttons
                :app="getApp()"
                :irods-status="sodarContext.irods_status"
                :irods-backend-enabled="sodarContext.irods_backend_enabled"
                :irods-webdav-url="sodarContext.irods_webdav_url"
                :irods-path="sodarContext.studies[currentStudyUuid].irods_path"
                :show-file-list="false">
            </irods-buttons>
          </div>
        </div>

        <!-- Study Card -->
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
              <b-button
                  v-if="editMode"
                  variant="primary"
                  class="sodar-header-button mr-2 pull-right"
                  :disabled="unsavedRow !== null"
                  @click="handleRowInsert(currentStudyUuid, false)">
                <i class="fa fa-plus"></i> Insert Row
              </b-button>
            </h4>
          </div>
          <div class="card-body p-0">
            <ag-grid-drag-select
                :app="getApp()"
                :uuid="currentStudyUuid">
              <template>
                <ag-grid-vue
                    class="ag-theme-bootstrap"
                    id="sodar-ss-grid-study"
                    ref="studyGrid"
                    :style="getGridStyle()"
                    :columnDefs="columnDefs.study"
                    :rowData="rowData.study"
                    :gridOptions="gridOptions.study"
                    :frameworkComponents="frameworkComponents">
                </ag-grid-vue>
              </template>
            </ag-grid-drag-select>
          </div>
        </div>

        <!-- Assays -->
        <span v-for="(assayInfo, assayUuid, index) in
                     sodarContext.studies[currentStudyUuid].assays"
              :key="index">
          <a class="sodar-ss-anchor" :id="assayUuid"></a>
          <div class="row mb-4" :id="'sodar-ss-section-assay-' + assayUuid">
            <h4 class="font-weight-bold mb-0 text-danger">
              <i class="fa fa-fw fa-table"></i>
              Assay: {{ assayInfo.display_name }}
              <i v-if="sodarContext.perms.is_superuser &&
                       assayInfo.plugin"
                 class="fa fa-puzzle-piece text-danger ml-1"
                 :title="assayInfo.plugin"
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
                  :irods-status="sodarContext.irods_status"
                  :irods-backend-enabled="sodarContext.irods_backend_enabled"
                  :irods-webdav-url="sodarContext.irods_webdav_url"
                  :irodsPath="assayInfo.irods_path"
                  :showFileList="false">
              </irods-buttons>
            </div>
          </div>

          <assay-shortcut-card
              v-if="!editMode &&
                    sodarContext.irods_status &&
                    assayShortcuts[assayUuid]"
              :app="getApp()"
              :assay-info="assayInfo"
              :shortcut-data="assayShortcuts[assayUuid]"
              :irods-backend-enabled="sodarContext.irods_backend_enabled"
              :irods-webdav-url="sodarContext.irods_webdav_url">
          </assay-shortcut-card>

          <!-- Assay Card -->
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
                <b-button
                  v-if="editMode"
                  variant="primary"
                  class="sodar-header-button mr-2 pull-right"
                  :disabled="unsavedRow !== null"
                  @click="handleRowInsert(assayUuid, true)">
                <i class="fa fa-plus"></i> Insert Row
              </b-button>
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
                    :columnDefs="columnDefs.assays[assayUuid]"
                    :rowData="rowData.assays[assayUuid]"
                    :gridOptions="gridOptions.assays[assayUuid]"
                    :frameworkComponents="frameworkComponents">
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
          <span v-if="sodarContext.perms.edit_sheet">
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
        :irods-webdav-url="sodarContext.irods_webdav_url"
        ref="dirModalRef">
    </irods-dir-modal>

    <!-- Modal for study shortcuts -->
    <shortcut-modal
        v-if="sodarContext && currentStudyUuid"
        :project-uuid="projectUuid"
        :study-uuid="currentStudyUuid"
        :irods-webdav-url="sodarContext.irods_webdav_url"
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
        v-if="editMode && sodarContext.perms.edit_sheet"
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
import AssayShortcutCard from './components/AssayShortcutCard.vue'
import { AgGridVue } from 'ag-grid-vue'
import DataCellRenderer from './components/renderers/DataCellRenderer.vue'
import IrodsButtonsRenderer from './components/renderers/IrodsButtonsRenderer.vue'
import ShortcutButtonsRenderer from './components/renderers/ShortcutButtonsRenderer.vue'
import FieldHeaderEditRenderer from './components/renderers/FieldHeaderEditRenderer'
import RowEditRenderer from './components/renderers/RowEditRenderer.vue'
import DataCellEditor from './components/editors/DataCellEditor.vue'
import ObjectSelectEditor from './components/editors/ObjectSelectEditor.vue'
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
        study: null,
        assays: {}
      },
      // Column definitions are managed here
      columnDefs: {
        study: null,
        assays: {}
      },
      // NOTE: These will NOT be updated, use getGridOptionsByUuid().rowData
      rowData: {
        study: null,
        assays: {}
      },
      assayShortcuts: {},
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
      editContext: null,
      editStudyData: false,
      editStudyConfig: null,
      editDataUpdated: false,
      studyDisplayConfig: null,
      sampleColId: null,
      sampleIdx: null,
      unsavedRow: null, // Info of currently unsaved row, or null if none
      updatingRow: false, // Row update in progress (bool)
      contentId: 'sodar-ss-vue-content',
      /* NOTE: cell editor only works if provided through frameworkComponents? */
      frameworkComponents: {
        dataCellEditor: DataCellEditor,
        objectSelectEditor: ObjectSelectEditor
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
    AssayShortcutCard,
    AgGridVue,
    AgGridDragSelect
  },
  created () {
    window.addEventListener('beforeunload', this.onBeforeUnload)
  },
  beforeDestroy () {
    window.removeEventListener('beforeunload', this.onBeforeUnload)
  },
  methods: {

    /* Event Handlers ------------------------------------------------------- */

    onBeforeUnload (event) {
      if (this.editMode &&
          (this.unsavedRow || this.updatingRow)) {
        event.preventDefault()
        event.returnValue = ''
      }
    },

    onFilterChange (event) {
      let gridApi
      if (event.currentTarget.id === 'sodar-ss-data-filter-study') {
        gridApi = this.getGridOptionsByUuid(this.currentStudyUuid).api
      } else if (event.currentTarget.id.indexOf('sodar-ss-data-filter-assay') !== -1) {
        const assayUuid = event.currentTarget.getAttribute('assay-uuid')
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

    // Helper to get flat value for comparator
    getFlatValue (value) {
      if (Array.isArray(value) && value.length > 0) {
        if (typeof value[0] === 'object' && 'name' in value[0]) {
          return value.map(d => d.name).join(';')
        } else return value.join(';')
      } else {
        return value
      }
    },

    // Custom comparator for data cells
    dataCellCompare (dataA, dataB) {
      let valueA = dataA.value
      let valueB = dataB.value
      if (['UNIT', 'NUMERIC'].includes(dataA.colType)) {
        if (!isNaN(parseFloat(valueA)) && !isNaN(parseFloat(valueB))) {
          return parseFloat(valueA) - parseFloat(valueB)
        }
      } else {
        valueA = this.getFlatValue(valueA)
        valueB = this.getFlatValue(valueB)
      }
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
      return 'height: ' + this.sodarContext.table_height + 'px;'
    },

    buildColDef (table, assayMode, uuid, editMode) {
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
              'text-right', 'text-muted',
              'sodar-ss-data-unselectable',
              'sodar-ss-data-row-cell',
              'sodar-ss-data-rownum-cell'
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
      const topHeaderLength = table.top_header.length
      let headerIdx = 0
      let j = headerIdx
      let studySection = true

      // Iterate through top header
      for (let i = 0; i < topHeaderLength; i++) {
        const topHeader = table.top_header[i]

        // Set up header group
        let headerGroup = {
          headerName: topHeader.value,
          headerClass: ['text-white', 'bg-' + topHeader.colour],
          children: []
        }
        if (editMode) {
          headerGroup.cellRendererParams = { headers: topHeader.headers }
        }

        let configFieldIdx = 0 // For config management

        // Iterate through field headers
        while (j < headerIdx + topHeader.colspan) {
          const fieldHeader = table.field_header[j]

          // Define special column properties
          const maxValueLen = fieldHeader.max_value_len
          const colType = fieldHeader.col_type

          let colAlign
          if (['UNIT', 'NUMERIC'].includes(colType)) {
            colAlign = 'right'
          } else {
            colAlign = 'left'
          }

          let minW = this.sodarContext.min_col_width
          const maxW = this.sodarContext.max_col_width
          let calcW = maxValueLen * 10 + 25 // Default
          let colWidth
          let fieldEditable = false

          // External links are a special case
          if (colType === 'EXTERNAL_LINKS') {
            minW = 140
            calcW = maxValueLen * 120
          }

          // Set the final column width
          if (j < table.col_last_vis) {
            colWidth = calcW < minW ? minW : (calcW > maxW ? maxW : calcW)
          } else { // Last visible column is a special case
            colWidth = Math.max(calcW, minW)
          }

          // Get studyDisplayConfig
          if (this.studyDisplayConfig) {
            let displayNode

            if (!assayMode) {
              displayNode = this.studyDisplayConfig.nodes[i]
            } else {
              displayNode = this.studyDisplayConfig.assays[uuid].nodes[i]
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
          } else if (assayMode &&
                studySection &&
                fieldHeader.value !== 'Name') { // Hide study data in assay
            fieldVisible = false
          } else { // Hide if empty and not editing
            fieldVisible = !!(fieldEditable || table.col_values[j])
          }

          // Get editFieldConfig if editing
          if (editMode && this.editStudyConfig) {
            editFieldConfig = null
            let editNode = null
            const studyNodeLen = this.editStudyConfig.nodes.length

            if (!assayMode || i < studyNodeLen) {
              editNode = this.editStudyConfig.nodes[i]
            } else {
              editNode = this.editStudyConfig.assays[uuid].nodes[i - studyNodeLen]
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
            cellRendererFramework: DataCellRenderer,
            cellRendererParams: {
              app: this,
              colType: colType,
              fieldEditable: fieldEditable // Needed here to update cellClass
            },
            comparator: this.dataCellCompare,
            filterValueGetter: this.dataCellFilterValue
          }

          // Cell classes
          if (!editMode) {
            header.cellClass = ['sodar-ss-data-cell', 'text-' + colAlign]
          } else {
            header.cellClass = function (params) {
              const colAlign = ['UNIT', 'NUMERIC'].includes(
                params.colDef.cellRendererParams.colType) ? 'right' : 'left'
              const cellClass = ['sodar-ss-data-cell', 'text-' + colAlign]

              // Set extra classes if non-editable
              if (('editable' in params.value && !params.value.editable) ||
                  (!('editable' in params.value) &&
                  !params.colDef.cellRendererParams.fieldEditable)) {
                if ('newInit' in params.value && params.value.newInit) {
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
          if (editMode) {
            // Store sample column ID and index
            if (!assayMode &&
                topHeader.value === 'Sample' &&
                header.headerName === 'Name') {
              this.sampleColId = header.field
              this.sampleIdx = j + 1 // +1 for row number column
            }

            // Set header renderer for fields we can manage
            if (this.sodarContext.perms.edit_sheet &&
                !['EXTERNAL_LINKS', 'ONTOLOGY'].includes(colType)) {
              let configAssayUuid = assayMode ? uuid : null
              let configNodeIdx = i

              if (assayMode) {
                // NOTE: -3 because of row/edit cols and split source column
                const studyNodeLen = this.columnDefs.study.length - 3
                if (configNodeIdx < studyNodeLen) {
                  configAssayUuid = null
                } else {
                  configNodeIdx = i - studyNodeLen
                }
              }

              header.headerComponentFramework = FieldHeaderEditRenderer
              header.headerComponentParams = {
                app: this.getApp(),
                modalComponent: this.$refs.columnConfigModal,
                colType: colType,
                fieldConfig: editFieldConfig,
                assayUuid: configAssayUuid,
                configNodeIdx: configNodeIdx,
                configFieldIdx: configFieldIdx,
                editable: fieldEditable, // Add here to allow checking by cell
                headerType: fieldHeader.type,
                assayMode: assayMode // Needed for sample col in assay
              }

              header.width = header.width + 20 // Fit button in header
              header.minWidth = header.minWidth + 20
            }

            // Set up field editing
            if (editFieldConfig) {
              // Allow overriding field editability cell-by-cell
              header.editable = function (params) {
                if (params.colDef.field in params.node.data &&
                    'editable' in params.node.data[params.colDef.field]) {
                  return params.node.data[params.colDef.field].editable
                } else if ('headerComponentParams' in params.colDef) {
                  return params.colDef.headerComponentParams.editable
                } else return false
              }

              // Set up cell editor selector
              header.cellEditorSelector = function (params) {
                let editorName = 'dataCellEditor'
                // TODO: Refactor so that default params are read from header
                const editorParams = Object.assign(
                  params.colDef.cellEditorParams
                )
                const editContext = editorParams.app.editContext

                // If sample name in an assay or an object ref, return selector
                // TODO: Simplify?
                if (params.colDef.headerComponentParams.assayMode &&
                    params.column.originalParent.colGroupDef.headerName === 'Sample' &&
                    params.colDef.headerName === 'Name' &&
                    'newRow' in params.value &&
                    params.value.newRow) {
                  editorName = 'objectSelectEditor'
                  editorParams.selectOptions = editContext.samples
                } else if (editorParams.headerInfo.header_type === 'protocol') {
                  editorName = 'objectSelectEditor'
                  editorParams.selectOptions = Object.assign(editContext.protocols)
                }

                return { component: editorName, params: editorParams }
              }

              // Set default cellEditorParams (may be updated in the selector)
              header.cellEditorParams = {
                app: this.getApp(),
                // Header information to be passed for calling server
                headerInfo: {
                  header_name: fieldHeader.name,
                  header_type: fieldHeader.type,
                  header_field: header.field, // For updating other cells
                  obj_cls: fieldHeader.obj_cls
                },
                renderInfo: {
                  align: colAlign,
                  width: colWidth
                },
                editConfig: editFieldConfig, // Editor configuration
                gridUuid: uuid, // TODO: Could get this from header params
                sampleColId: this.sampleColId
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
      if (!this.editMode &&
          !assayMode && 'shortcuts' in table && table.shortcuts) {
        const shortcutHeaderGroup = {
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
              width: 45 * Object.keys(table.shortcuts.schema).length,
              minWidth: 90,
              cellRendererFramework: ShortcutButtonsRenderer,
              cellRendererParams: {
                schema: table.shortcuts.schema,
                modalComponent: this.$refs.shortcutModalRef
              }
            }
          ]
        }
        colDef.push(shortcutHeaderGroup)
      }

      // Assay iRODS button column
      if (!this.editMode && assayMode) {
        const assayContext = this.sodarContext.studies[this.currentStudyUuid].assays[uuid]
        if (this.sodarContext.irods_status && assayContext.display_row_links) {
          const assayIrodsPath = assayContext.irods_path
          const irodsHeaderGroup = {
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
                  irodsStatus: this.sodarContext.irods_status,
                  irodsBackendEnabled: this.sodarContext.irods_backend_enabled,
                  irodsWebdavUrl: this.sodarContext.irods_webdav_url,
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

      // Row editing column
      if (this.editMode) {
        const rowEditGroup = {
          headerName: 'Edit',
          headerClass: [
            'text-white',
            'bg-secondary',
            'sodar-ss-data-links-top'
          ],
          children: [
            {
              headerName: 'Row',
              field: 'rowEdit',
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
              cellRendererFramework: RowEditRenderer,
              cellRendererParams: {
                app: this,
                gridUuid: uuid,
                assayMode: assayMode,
                sampleColId: this.sampleColId,
                sampleIdx: this.sampleIdx
              },
              width: 80,
              minWidth: 80
            }
          ]
        }
        colDef.push(rowEditGroup)
      }

      return colDef
    },

    buildRowData (table, assayMode) {
      const rowData = []

      // Iterate through rows
      for (let i = 0; i < table.table_data.length; i++) {
        const rowCells = table.table_data[i]
        const row = { rowNum: i + 1 }
        for (let j = 0; j < rowCells.length; j++) {
          const cellVal = rowCells[j]
          // Copy col_type info to each cell (comparator can't access colDef)
          cellVal.colType = table.field_header[j].col_type
          row['col' + j.toString()] = cellVal
        }

        // Add study shortcut field
        if (!this.editMode &&
            !assayMode &&
            'shortcuts' in table &&
            table.shortcuts) {
          row.shortcutLinks = table.shortcuts.data[i]
        }

        // Add iRODS field
        if (!this.editMode &&
            this.sodarContext.irods_status &&
            'irods_paths' in table &&
            table.irods_paths.length > 0) {
          row.irodsLinks = table.irods_paths[i]
        }

        rowData.push(row)
      }
      return rowData
    },

    // Clear current grids
    clearGrids () {
      this.gridOptions = { study: null, assays: {} }
      this.columnDefs = { study: null, assays: {} }
      this.rowData = { study: null, assays: {} }
      this.assayShortcuts = {}
      this.sampleColId = null
      this.sampleIdx = null
    },

    getStudy (studyUuid, editMode) {
      this.gridsLoaded = false
      this.gridsBusy = true
      this.clearGrids()

      // Clear additional data
      this.editContext = null
      this.unsavedRow = null

      // Set up current study
      this.gridOptions.study = this.initGridOptions(editMode)
      this.setCurrentStudy(studyUuid)
      this.setPath()

      // Retrieve study and assay tables for current study
      // TODO: Add timeout/retrying
      let url = this.sodarContext.studies[studyUuid].table_url

      if (editMode) {
        url = url + '?edit=1'
      }

      fetch(url, { credentials: 'same-origin' })
        .then(data => data.json())
        .then(
          data => {
            if ('render_error' in data) {
              this.renderError = data.render_error
              this.gridsLoaded = false
            } else {
              // Editing: Get study config
              if (editMode && 'study_config' in data) {
                this.editStudyConfig = data.study_config
              }

              // Editing: Get edit context
              if (editMode && 'edit_context' in data) {
                this.editContext = data.edit_context
              }

              // Get display config
              this.studyDisplayConfig = data.display_config

              // Build study
              this.columnDefs.study = this.buildColDef(
                data.tables.study, false, studyUuid, editMode)
              this.rowData.study = this.buildRowData(data.tables.study, false)

              // Build assays
              for (const assayUuid in data.tables.assays) {
                this.gridOptions.assays[assayUuid] = this.initGridOptions(editMode)
                this.columnDefs.assays[assayUuid] = this.buildColDef(
                  data.tables.assays[assayUuid], true, assayUuid, editMode)
                this.rowData.assays[assayUuid] = this.buildRowData(
                  data.tables.assays[assayUuid], true)

                // Get assay shortcuts
                if ('shortcuts' in data.tables.assays[assayUuid]) {
                  this.assayShortcuts[assayUuid] =
                      data.tables.assays[assayUuid].shortcuts
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
              if (this.sodarContext.irods_status && this.$refs.studyStatsBadge) {
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
      const fromSubPage = this.activeSubPage
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
      this.$router.push({ path: path }).catch(error => error)
    },

    // Set up current page target from URL path
    setTargetByPath () {
      const pageId = this.$route.fullPath.split('/')[1]

      if (this.$route.fullPath.indexOf('/study/') === -1 &&
          this.$route.fullPath.indexOf('/assay/') === -1 &&
          pageId) {
        this.showSubPage(pageId)
        this.setCurrentStudy(null)
        this.setCurrentAssay(null)
      } else if (this.$route.fullPath.indexOf('/assay/') !== -1) {
        this.activeSubPage = null
        this.setCurrentAssay(this.$route.fullPath.substr(7))

        for (const studyUuid in this.sodarContext.studies) {
          if (this.currentAssayUuid in
              this.sodarContext.studies[studyUuid].assays) {
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
          this.currentStudyUuid = Object.keys(this.sodarContext.studies)[0]
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

      fetch('/samplesheets/ajax/edit/cell/' + this.projectUuid, {
        method: 'POST',
        body: JSON.stringify({ updated_cells: upDataArr }),
        credentials: 'same-origin',
        headers: {
          Accept: 'application/json',
          'Content-Type': 'application/json',
          'X-CSRFToken': this.sodarContext.csrf_token
        }
      }).then(data => data.json())
        .then(
          data => {
            if (data.message === 'ok') {
              this.showNotification('Changes Saved', 'success', 1000)
              this.editDataUpdated = true

              // Update other occurrences of cell in UI
              const gridUuids = this.getStudyGridUuids()
              for (let i = 0; i < gridUuids.length; i++) {
                this.updateCellUIValues(
                  this.getGridOptionsByUuid(
                    gridUuids[i]).api, upDataArr, refreshCells)
              }
            } else {
              console.log('Save status: ' + data.message) // DEBUG
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
        const upData = upDataArr[i]
        const fieldId = upData.header_field

        gridApi.forEachNode(function (rowNode) {
          const value = rowNode.data[fieldId]
          if (value && value.uuid === upData.uuid) {
            value.value = upData.value
            value.unit = upData.unit
            rowNode.setDataValue(fieldId, value)
          }
        })

        if (refreshCells) {
          gridApi.refreshCells({ columns: [fieldId], force: true })
        }
      }
    },

    getDefaultValue (colId, gridOptions, newInit, forceEmpty) {
      // Return empty or default value for a newly created cell
      // TODO: Cleanup and simplify
      // console.log('getDefaultValue() called: ' + colId) // DEBUG
      const column = gridOptions.columnApi.getColumn(colId)
      const colType = column.colDef.cellRendererParams.colType
      let editConfig = null
      if ('cellEditorParams' in column.colDef) {
        editConfig = column.colDef.cellEditorParams.editConfig
      }

      if (newInit === undefined) newInit = false
      if (forceEmpty === undefined) forceEmpty = false
      const value = {
        uuid: null,
        colType: colType,
        value: '',
        newRow: true,
        newInit: newInit
      }
      // Default value
      if (forceEmpty === false &&
          editConfig &&
          'default' in editConfig &&
          editConfig.default) {
        if (editConfig.format === 'protocol') {
          let name = ''
          // TODO: Use find() instead
          for (let i = 0; i < this.editContext.protocols.length; i++) {
            if (this.editContext.protocols[i].uuid === editConfig.default) {
              name = this.editContext.protocols[i].name
              break
            }
          }
          value.value = name
          value.uuid_ref = editConfig.default
        } else {
          value.value = editConfig.default
        }
      } else { // Special value notation if default is not found
        if (editConfig && editConfig.format === 'protocol') {
          value.value = { name: '', uuid: null }
        } else if (colType === 'ONTOLOGY') {
          value.value = { name: null, accession: null, ontology_name: null }
        }
      }
      // Default unit
      if (editConfig && 'unit_default' in editConfig) {
        value.unit = editConfig.unit_default
      }

      return value
    },

    enableNextNodes (rowNode, gridOptions, gridUuid, startIdx) {
      // Enable editing for the next node(s) when inserting a new row
      // NOTE: Can't access cellEditorParams here as they are set dynamically
      const cols = gridOptions.columnApi.getAllColumns()
      // console.log('enableNextNodes() called at: ' + cols[startIdx].colId) // DEBUG

      // Only enable node(s) if they are in newInit mode
      if (!rowNode.data[cols[startIdx].colId].newInit) {
        // console.log('Nothing to enable') // DEBUG
        return
      }

      if (startIdx && startIdx < cols.length - 1) { // -1 for edit column
        let nextColId = cols[startIdx].colId
        const nextGroupId = cols[startIdx].originalParent.groupId
        const nextNodeCls = cols[startIdx].colDef.cellEditorParams.headerInfo.obj_cls
        let enableNextIdx = null

        // If the next node is a material, enable editing its name
        // Else if it's a process, enable editing for all cells (if available)
        if (nextNodeCls === 'GenericMaterial') {
          const itemType = cols[startIdx].colDef.cellEditorParams.headerInfo.item_type
          const headerType = cols[startIdx].colDef.cellEditorParams.headerInfo.header_type
          let value = this.getDefaultValue(nextColId, gridOptions, true)

          // If default name suffix is set, fill name, enable node and continue
          if (headerType === 'name' &&
              !(['SOURCE', 'DATA'].includes(itemType)) &&
              value.value) {
            let namePrefix = ''

            for (let i = 1; i < startIdx; i++) {
              const prevHeaderInfo = cols[i].colDef.cellEditorParams.headerInfo
              if (prevHeaderInfo.obj_cls === 'GenericMaterial' &&
                  prevHeaderInfo.header_type === 'name' &&
                  prevHeaderInfo.item_type !== 'DATA') {
                namePrefix = rowNode.data[cols[i].colId].value
              }
            }
            value.value = namePrefix + value.value
            let createNew = true

            // Check if name already appears in column
            gridOptions.api.forEachNode(function (r) {
              if (r.data[nextColId].value === value.value) {
                createNew = false
              }
            })

            value.newInit = false
            value.editable = true
            rowNode.setDataValue(nextColId, value)
            this.handleNodeUpdate(
              value,
              cols[startIdx],
              rowNode,
              gridOptions,
              gridUuid,
              createNew)
            return
          }

          value.editable = true
          if (itemType === 'DATA') value.newInit = false // Empty name is OK
          rowNode.setDataValue(nextColId, value)

          // Immediately enable next node after a data node (name can be blank)
          if (itemType === 'DATA') {
            for (let i = startIdx + 1; i < cols.length - 1; i++) {
              if (cols[i].originalParent.groupId !== nextGroupId) {
                enableNextIdx = i
                break
              }
              value = this.getDefaultValue(cols[i].colId, gridOptions, false, true)
              // value.newInit = false
              value.editable = false
              rowNode.setDataValue(cols[i].colId, value)
            }
          }
        } else if (nextNodeCls === 'Process') {
          let i = startIdx
          let protocolFilled = false
          let newInit = true
          let forceEmpty = false

          while (i < cols.length &&
              cols[i].originalParent.groupId === nextGroupId) {
            nextColId = cols[i].colId
            const value = this.getDefaultValue(nextColId, gridOptions, newInit, forceEmpty)
            const headerType = cols[i].colDef.cellEditorParams.headerInfo.header_type

            if (headerType === 'protocol') {
              value.editable = true
              if ('uuid_ref' in value && value.uuid_ref) {
                protocolFilled = true
                newInit = false
                value.newInit = false // Update protocol ref column newInit
              } else forceEmpty = true
            } else if (headerType === 'process_name') {
              value.editable = true // Process name should always be editable
            } else {
              // Only allow editing the rest of the cells if protocol is set
              if (protocolFilled) {
                value.editable = cols[i].colDef.cellRendererParams.fieldEditable
              } else {
                value.editable = false
              }
            }
            rowNode.setDataValue(nextColId, value)
            i += 1
          }

          // If default protocol was filled, enable the next node(s) too
          if (protocolFilled) enableNextIdx = i
        }
        // If we can immediately enable the next node(s), proceed
        if (enableNextIdx) this.enableNextNodes(rowNode, gridOptions, gridUuid, enableNextIdx)
      }
    },

    handleNodeUpdate (
      firstCellValue, column, rowNode, gridOptions, gridUuid, createNew
    ) {
      // console.log('handleNodeUpdate() called; colId=' + column.colId) // DEBUG
      const gridApi = gridOptions.api
      const columnApi = gridOptions.columnApi
      const firstColId = column.colId // ID of the identifying node column
      let assayMode = false

      if (gridUuid in this.sodarContext.studies[this.currentStudyUuid].assays) {
        assayMode = true
      }

      // Sample in an assay is a special case
      if (assayMode && column.originalParent.colGroupDef.headerName === 'Sample') {
        const studyOptions = this.getGridOptionsByUuid(this.currentStudyUuid)
        const studyApi = studyOptions.api
        const studyCols = studyOptions.columnApi.getAllColumns()
        let studyCopyRow = null
        const sampleColId = this.sampleColId

        // Get sample row from study table
        studyApi.forEachNode(function (rowNode) {
          if (!studyCopyRow &&
              rowNode.data[sampleColId].uuid === firstCellValue.uuid_ref) {
            studyCopyRow = rowNode
          }
        })

        // Fill in preceeding nodes
        for (let i = 1; i < this.sampleIdx; i++) {
          // TODO: Create a generic helper for copying
          const copyColId = studyCols[i].colId
          const copyData = Object.assign(studyCopyRow.data[copyColId])
          copyData.newRow = true
          copyData.newInit = false
          copyData.editable = columnApi.getColumn(copyColId).colDef.cellRendererParams.fieldEditable
          rowNode.setDataValue(copyColId, copyData)
        }
      }

      // Find other cells within the same node to be updated
      const nodeCols = []
      const cols = columnApi.getAllColumns()
      let nextNodeStartIdx = null
      // Since we split the source group we have to apply some trickery
      let groupId = column.originalParent.groupId
      if (groupId === '1') groupId = '2'
      let startIdx

      for (let i = 1; i < cols.length - 1; i++) {
        if (cols[i].colId === firstColId) {
          startIdx = i + 1
          break
        }
      }

      for (let i = startIdx; i < cols.length - 1; i++) {
        const col = cols[i]
        // NOTE: Must use originalParent to work with hidden columns
        if (col.originalParent.groupId === groupId) {
          nodeCols.push(col)
        } else if (col.colId !== firstColId &&
              col.originalParent.groupId !== groupId) {
          nextNodeStartIdx = i
          break
        }
      }

      // IF node is new THEN fill out other cells with default/empty values
      if (createNew) {
        for (let i = 0; i < nodeCols.length; i++) {
          const newColId = nodeCols[i].colId
          const value = this.getDefaultValue(nodeCols[i].colId, gridOptions)
          rowNode.setDataValue(newColId, value)
        }
      } else { // ELSE set UUIDs and update cell values (only in the same table)
        let copyRowNode = null
        gridApi.forEachNode(function (rowNode) {
          if (!copyRowNode && rowNode.data[firstColId].value === firstCellValue.value) {
            copyRowNode = rowNode
          }
        })

        for (let i = 0; i < nodeCols.length; i++) {
          const copyColId = nodeCols[i].colId
          const copyData = Object.assign(copyRowNode.data[copyColId])
          copyData.newInit = false
          copyData.editable = columnApi.getColumn(copyColId).colDef.cellRendererParams.fieldEditable
          rowNode.setDataValue(copyColId, copyData)
        }
      }

      // Enable the next node(s), if we are initializing node for the 1st time
      if (nextNodeStartIdx) {
        this.enableNextNodes(rowNode, gridOptions, gridUuid, nextNodeStartIdx)
      }

      // Redraw row node for all changes to be displayed
      gridApi.redrawRows({ rows: [rowNode] })
    },

    handleRowInsert (gridUuid, assayMode) {
      const gridOptions = this.getGridOptionsByUuid(gridUuid)
      const gridApi = gridOptions.api

      // Insert empty row
      const row = { rowNum: 'NEW' }
      const cols = gridOptions.columnApi.getAllColumns()
      const emptyData = {
        value: null,
        uuid: null,
        newRow: true, // Node in newly initialized row (not saved yet)
        newInit: true, // Newly initialized node (no data yet)
        editable: null
      }

      if (!assayMode) { // Study table
        let editable = true
        for (let i = 1; i < cols.length - 1; i++) {
          row[cols[i].colId] = Object.assign(
            {}, emptyData, { editable: editable })
          // Initially only make first column (source ID) editable
          if (editable) editable = false
        }
      } else { // Assay table
        // Find the start of the sample node
        // Fill cells with init data and enable sample name
        if (this.sampleColId) {
          for (let i = 1; i < cols.length - 1; i++) {
            row[cols[i].colId] = Object.assign(
              {}, emptyData, { editable: cols[i].colId === this.sampleColId })
          }
        } else { // Sample node not found
          this.showNotification('Sample Not Found', 'danger', 1000)
        }
      }

      const res = gridApi.applyTransaction({ add: [row] })
      this.unsavedRow = {
        gridUuid: gridUuid,
        id: res.add[0].id
      }
      gridApi.ensureIndexVisible(res.add[0].rowIndex) // Scroll to inserted row
    },

    handleRowSave (gridOptions, rowNode, newRowData, assayMode, finishCallback) {
      let newSample = false
      if (!assayMode && !rowNode.data[this.sampleColId].uuid) newSample = true
      this.updatingRow = true

      fetch('/samplesheets/ajax/edit/row/insert/' + this.projectUuid, {
        method: 'POST',
        body: JSON.stringify({ new_row: newRowData }),
        credentials: 'same-origin',
        headers: {
          Accept: 'application/json',
          'Content-Type': 'application/json',
          'X-CSRFToken': this.sodarContext.csrf_token
        }
      }).then(data => data.json())
        .then(
          data => {
            if (data.message === 'ok') {
              const cols = gridOptions.columnApi.getAllColumns()
              let nodeIdx = 0
              let sampleUuid
              let sampleName
              let startIdx = 1
              let groupId = cols[2].originalParent.groupId // 2nd source group!

              // Modify starting index and group id for assay table updating
              if (assayMode) {
                startIdx = this.sampleIdx
                groupId = cols[startIdx].originalParent.groupId
              }

              // Set cell data to match an existing row
              for (let i = startIdx; i < cols.length - 1; i++) {
                const value = rowNode.data[cols[i].colId]
                if (!value.uuid) value.uuid = data.node_uuids[nodeIdx]
                value.newRow = false
                value.newInit = false
                value.editable = cols[i].colDef.cellRendererParams.fieldEditable
                rowNode.setDataValue(cols[i].colId, value)

                // Save sample info if new sample was added in study
                if (!assayMode && cols[i].colId === this.sampleColId) {
                  sampleUuid = data.node_uuids[nodeIdx]
                  sampleName = rowNode.data[cols[i].colId].value
                }

                if (i > 2 && // NOTE: Skip split source column
                    i < cols.length - 2 &&
                    groupId !== cols[i + 1].originalParent.groupId) {
                  groupId = cols[i + 1].originalParent.groupId
                  nodeIdx += 1
                }
              }

              // Set rowNum for row
              const rowNums = []
              gridOptions.api.forEachNode(function (r) {
                if (r !== rowNode) rowNums.push(parseInt(r.data[cols[0].colId]))
              })
              rowNode.setDataValue(cols[0].colId, Math.max(...rowNums) + 1)

              // Update sample list if a new sample was added in study/assay
              if (!assayMode && newSample && sampleUuid) {
                this.editContext.samples[sampleUuid] = {
                  name: sampleName,
                  assays: []
                }
              } else if (assayMode) {
                const sampleUuid = rowNode.data[this.sampleColId].uuid
                if (!(newRowData.assay in this.editContext.samples[sampleUuid].assays)) {
                  this.editContext.samples[sampleUuid].assays.push(newRowData.assay)
                }
              }

              // Finalize
              gridOptions.api.refreshCells({ force: true }) // for cellClass
              this.unsavedRow = null
              this.editDataUpdated = true
              this.showNotification('Row Inserted', 'success', 1000)
            } else {
              console.log('Row insert status: ' + data.message) // DEBUG
              this.showNotification('Insert Failed', 'danger', 1000)
            }

            finishCallback()
            this.updatingRow = false
          }
        ).catch(this.handleRowUpdateError)
    },

    handleRowDelete (
      gridOptions, gridUuid, rowNode, delRowData, assayMode, finishCallback) {
      const newRow = this.unsavedRow &&
          this.unsavedRow.gridUuid === gridUuid &&
          this.unsavedRow.id === rowNode.id

      // Unsaved row (simply remove from grid)
      if (newRow) {
        gridOptions.api.applyTransaction({ remove: [rowNode.data] })
        this.unsavedRow = null // Since we only allow editing one row for now..
        return
      }

      // Else update in database
      this.updatingRow = true

      fetch('/samplesheets/ajax/edit/row/delete/' + this.projectUuid, {
        method: 'POST',
        body: JSON.stringify({ del_row: delRowData }),
        credentials: 'same-origin',
        headers: {
          Accept: 'application/json',
          'Content-Type': 'application/json',
          'X-CSRFToken': this.sodarContext.csrf_token
        }
      }).then(data => data.json())
        .then(
          data => {
            if (data.message === 'ok') {
              this.editDataUpdated = true

              // Update sample list
              const sampleUuid = rowNode.data[this.sampleColId].uuid

              if (assayMode &&
                  !(gridUuid in this.editContext.samples[sampleUuid].assays)) {
                let sampleFound = false
                const sampleColId = this.sampleColId

                gridOptions.api.forEachNode(function (r) {
                  if (r.data[sampleColId].uuid === sampleUuid &&
                      r.id !== rowNode.id) {
                    sampleFound = true
                  }
                })

                if (!sampleFound) {
                  this.editContext.samples[
                    sampleUuid].assays = this.editContext.samples[
                    sampleUuid].assays.filter(
                    v => v !== gridUuid)
                }
              }

              gridOptions.api.applyTransaction({ remove: [rowNode.data] })

              // Update row numbers
              let rowNum = 1
              gridOptions.api.forEachNode(function (r) {
                r.setDataValue('rowNum', rowNum)
                rowNum += 1
              })

              this.showNotification('Row Deleted', 'success', 1000)
            } else {
              console.log('Row delete status: ' + data.message) // DEBUG
              this.showNotification('Delete Failed', 'danger', 1000)
            }

            finishCallback()
            this.updatingRow = false
          }
        ).catch(this.handleRowUpdateError)
    },

    handleRowUpdateError (error) {
      this.updatingRow = false
      console.log('Error updating row: ' + error.message)
    },

    handleFinishEditing () {
      fetch('/samplesheets/ajax/edit/finish/' + this.projectUuid, {
        method: 'POST',
        body: JSON.stringify({
          updated: this.editDataUpdated
        }),
        credentials: 'same-origin',
        headers: {
          Accept: 'application/json',
          'Content-Type': 'application/json',
          'X-CSRFToken': this.sodarContext.csrf_token
        }
      }).then(data => data.json())
        .then(
          data => {
            if (data.message === 'ok') {
              this.showNotification('Finished Editing', 'success', 1000)
            } else {
              console.log('Finish status: ' + data.message) // DEBUG
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

    getStudyGridUuids (assayOnly) {
      // Return array of UUIDs for the current study and all assays
      if (!this.currentStudyUuid) {
        return null
      }
      const uuids = assayOnly ? [] : [this.currentStudyUuid]
      for (var k in this.columnDefs.assays) {
        uuids.push(k)
      }
      return uuids
    },

    getGridOptionsByUuid (uuid) {
      if (uuid === this.currentStudyUuid) {
        return this.$refs.studyGrid.gridOptions
      } else if (uuid in this.columnDefs.assays) {
        // TODO: Why is this an array?
        return this.$refs['assayGrid' + uuid][0].gridOptions
      }
    },

    getApp () {
      // Workaround for #520
      return this
    },

    findNextNodeIdx (cols, idx, maxIdx) {
      // Find next node index or null if not found
      // TODO: Use this wherever performing similar iteration
      const groupId = cols[idx].originalParent.groupId
      if (!maxIdx) maxIdx = cols.length
      while (idx < maxIdx) {
        if (groupId !== cols[idx].originalParent.groupId) {
          return idx
        }
        idx += 1
      }
      return null
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
    this.projectUuid = initialContext.project_uuid

    const setUpInitialData = async () => {
      // Get full context data from an API view
      // TODO: Add timeout/retrying
      const data = await fetch(initialContext.context_url, {
        credentials: 'same-origin'
      })
      const jsonData = await data.json()
      this.sodarContext = JSON.parse(jsonData)

      // Set up current view target based on entry point URL
      this.setTargetByPath()

      // If study UUID isn't found from URL, set the default initial value
      if (!this.currentStudyUuid) {
        this.setCurrentStudy(initialContext.initial_study)
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

.sodar-ss-data-rownum-cell {
  padding-top: 4px; /* HACK for ag-grid CSS issue */
}

.sodar-ss-data-forbidden {
  background: repeating-linear-gradient(
    -45deg, #ddd, #ddd 5px, #eee 5px, #eee 10px
  );
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

.sodar-ss-vue-row-btn {
  width: 26px !important; /* Quick HACK for uniform button size */
}

/* Common editor styles */

.sodar-ss-vue-edit-popup {
  border: 1px solid #6c757d;
  background: #ffffff;
  padding: 10px;
}

input.ag-cell-edit-input {
  -moz-appearance: none;
  -webkit-appearance: none;
  appearance: none;

  border: 0;
  width: 100%;
  height: 38px !important;
  background-color: #ffffd8 !important;
  padding-left: 11px;
  padding-right: 14px;
  padding-top: 0;
  padding-bottom: 2px;
}

select.ag-cell-edit-input {
  -moz-appearance: none;
  -webkit-appearance: none;
  appearance: none;

  border: 0;
  width: 100%;
  height: 38px !important;
  background-color: #ffffd8 !important;
  background-repeat: no-repeat;
  background-size: 0.5em auto;
  background-position: right 0.25em center;
  padding-left: 12px;
  padding-right: 18px;
  padding-top: 0;
  padding-bottom: 2px !important;

  background-image: url("data:image/svg+xml;charset=utf-8, \
    <svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 60 40'> \
      <polygon points='0,0 60,0 30,40' style='fill:black;'/> \
    </svg>");
}

select#sodar-ss-vue-edit-select-unit {
  margin-left: 4px;
}

.sodar-ss-vue-select-firefox {
  padding-left: 8px !important;
}

input.sodar-ss-vue-popup-input,
select.sodar-ss-vue-popup-input {
  border: 1px solid #ced4da;
  border-radius: .25rem;
}

</style>
