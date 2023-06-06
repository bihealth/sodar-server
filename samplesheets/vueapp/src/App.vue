<template>
  <div id="app">
    <!-- Header -->
    <page-header
        v-if="sodarContext"
        ref="pageHeader"
        :app="getApp()"
        :handle-nav-callback="handleStudyNavigation"
        :show-sub-page-callback="showSubPage"
        :toggle-edit-mode-callback="toggleEditMode"
        :editor-help-modal="$refs.editorHelpModal"
        :win-export-modal="$refs.winExportModal"
        :version-save-modal="$refs.versionSaveModal">
    </page-header>

    <!-- Main container -->
    <div class="container-fluid sodar-page-container"
         id="sodar-ss-vue-container">

      <!-- Alerts from context API view -->
      <div v-if="sodarContext &&
                 sodarContext.perms.edit_sheet &&
                 sodarContext.alerts.length"
           class="pb-2"
           id="sodar-ss-alert-container">
        <div v-for="(alertData, alertIdx) in sodarContext.alerts"
             :key="alertIdx"
             :class="'alert sodar-ss-alert alert-' + alertData.level"
             v-html="alertData.html">
        </div>
      </div>

      <!-- Study data rendered -->
      <div v-if="sodarContext &&
                 gridsLoaded &&
                 !renderError &&
                 !activeSubPage"
           :id="contentId">

        <!-- Study -->
        <a class="sodar-ss-anchor" :id="currentStudyUuid"></a>
        <sheet-table-header
            :params="getTableHeaderParams(currentStudyUuid, false)">
        </sheet-table-header>

        <sheet-table
            :app="getApp()"
            :assay-mode="false"
            :column-defs="columnDefs.study"
            :grid-options="gridOptions.study"
            :grid-uuid="currentStudyUuid"
            :row-data="rowData.study"
            :table-height="tableHeights.study"
            :initial-filter="initialFilter">
        </sheet-table>

        <!-- Assays -->
        <span v-for="(assayInfo, assayUuid, index) in
                     sodarContext.studies[currentStudyUuid].assays"
              :key="index">
          <a class="sodar-ss-anchor" :id="assayUuid"></a>
          <sheet-table-header
              :params="getTableHeaderParams(assayUuid, true)">
          </sheet-table-header>

          <assay-shortcut-card
              v-if="!editMode &&
                    sodarContext.irods_status &&
                    assayShortcuts[assayUuid]"
              :sodar-context="sodarContext"
              :assay-info="assayInfo"
              :assay-shortcuts="assayShortcuts[assayUuid]"
              :modal-component="$refs.dirModalRef"
              :notify-callback="showNotification">
          </assay-shortcut-card>

          <sheet-table
              :app="getApp()"
              :assay-mode="true"
              :column-defs="columnDefs.assays[assayUuid]"
              :grid-options="gridOptions.assays[assayUuid]"
              :grid-uuid="assayUuid"
              :row-data="rowData.assays[assayUuid]"
              :table-height="tableHeights.assays[assayUuid]"
              :initial-filter="initialFilter">
          </sheet-table>
        </span>

      </div>

      <!-- Overview subpage -->
      <div v-else-if="activeSubPage === 'overview'" :id="contentId">
        <Overview :sodar-context="sodarContext">
        </Overview>
      </div>

      <!-- Parser Warnings subpage -->
      <div v-else-if="activeSubPage === 'warnings'" :id="contentId">
        <ParserWarnings
            :project-uuid="projectUuid"
            :sodar-context="sodarContext">
        </ParserWarnings>
      </div>

      <!-- Render error -->
      <div v-else-if="renderError" :id="contentId">
        <div class="alert alert-danger" id="sodar-ss-alert-error">
          Error rendering study tables, please check your ISA-Tab files.
          Exception: {{ renderError }}
        </div>
      </div>

      <!-- No sheets available -->
      <div v-else-if="appSetupDone && !sheetsAvailable"
           :id="contentId">
        <div class="alert alert-info" id="sodar-ss-alert-empty">
          No sample sheets are currently available for this project.
          <span v-if="sodarContext.perms.edit_sheet && !sheetSyncEnabled">
            To add sample sheets, please import them from an existing ISA-Tab
            investigation, create new sheets from a template or enable remote
            sheet synchonization.
          </span>
          <span v-if="sodarContext.perms.edit_sheet && sheetSyncEnabled">
            To add sample sheets, please wait for the synchonization to take
            place or trigger the synchonization manually.
          </span>
        </div>
      </div>

      <!-- Loading/busy -->
      <div v-else class="w-100 text-center" id="sodar-ss-wait">
        <img src="/icons/mdi/loading.svg?color=%236c757d&height=64"
             class="spin" />
      </div>

    </div> <!-- Main container -->

    <!-- Windows export notification modal -->
    <win-export-modal
        v-if="windowsOs"
        :app="getApp()"
        ref="winExportModal">
    </win-export-modal>

    <!-- iRODS directory listing modal -->
    <irods-dir-modal
        v-if="sodarContext"
        :app="getApp()"
        :project-uuid="projectUuid"
        :irods-webdav-url="sodarContext.irods_webdav_url"
        ref="dirModalRef">
    </irods-dir-modal>

    <!-- Modal for study shortcuts -->
    <study-shortcut-modal
        v-if="sodarContext && currentStudyUuid"
        :project-uuid="projectUuid"
        :study-uuid="currentStudyUuid"
        :irods-webdav-url="sodarContext.irods_webdav_url"
        ref="studyShortcutModal">
    </study-shortcut-modal>

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

    <!-- Editing: Ontology value edit modal -->
    <ontology-edit-modal
        v-if="editMode"
        :unsaved-data-cb="setUnsavedData"
        ref="ontologyEditModal">
    </ontology-edit-modal>

    <!-- Editing: Version save modal -->
    <version-save-modal
        v-if="editMode"
        :app="getApp()"
        ref="versionSaveModal">
    </version-save-modal>

    <!--<router-view/>-->
  </div>
</template>

<script>
import PageHeader from './components/PageHeader.vue'
import SheetTableHeader from './components/SheetTableHeader.vue'
import SheetTable from './components/SheetTable.vue'
import Overview from './components/Overview.vue'
import ParserWarnings from './components/ParserWarnings.vue'
import IrodsDirModal from './components/modals/IrodsDirModal.vue'
import StudyShortcutModal from './components/modals/StudyShortcutModal.vue'
import ColumnToggleModal from './components/modals/ColumnToggleModal.vue'
import ColumnConfigModal from './components/modals/ColumnConfigModal.vue'
import EditorHelpModal from './components/modals/EditorHelpModal.vue'
import WinExportModal from './components/modals/WinExportModal.vue'
import OntologyEditModal from './components/modals/OntologyEditModal.vue'
import VersionSaveModal from './components/modals/VersionSaveModal.vue'
import AssayShortcutCard from './components/AssayShortcutCard.vue'
import DataCellRenderer from './components/renderers/DataCellRenderer'
import HeaderEditRenderer from './components/renderers/HeaderEditRenderer'
import StudyShortcutsRenderer from './components/renderers/StudyShortcutsRenderer'
import IrodsButtonsRenderer from './components/renderers/IrodsButtonsRenderer'
import RowEditRenderer from './components/renderers/RowEditRenderer'
import DataCellEditor from './components/editors/DataCellEditor.vue'
import ObjectSelectEditor from './components/editors/ObjectSelectEditor.vue'
import OntologyEditor from './components/editors/OntologyEditor.vue'
import {
  initGridOptions,
  buildColDef,
  buildRowData
} from './utils/gridUtils.js'

const windowsPlatforms = ['Win32', 'Win64', 'Windows', 'WinCE']
const filterRegex = /^\S+\/filter\/(?<filter>\S+)*$/
const studyUrlRegex = /^\/(?<type>study|assay)\/(?<uuid>[0-9a-f-]+)\S*$/

export default {
  name: 'App',
  data () {
    return {
      projectUuid: null,
      sodarContext: null,
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
      sheetSyncEnabled: null,
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
      sourceColSpan: null,
      tableHeights: null,
      unsavedRow: null, // Info of currently unsaved row, or null if none
      updatingRow: false, // Row update in progress (bool)
      unsavedData: false, // Other updated data (bool)
      versionSaved: true, // Status of current version saved as backup
      editingCell: false, // Cell editing in progress (bool)
      initialFilter: null, // Initial value for table filter (from URL)
      contentId: 'sodar-ss-vue-content',
      windowsOs: false
    }
  },
  components: {
    PageHeader,
    SheetTableHeader,
    SheetTable,
    Overview,
    ParserWarnings,
    IrodsDirModal,
    StudyShortcutModal,
    ColumnToggleModal,
    ColumnConfigModal,
    EditorHelpModal,
    WinExportModal,
    OntologyEditModal,
    VersionSaveModal,
    AssayShortcutCard,
    /* eslint-disable vue/no-unused-components */
    // NOTE: These ARE used in gridUtils but this confuses eslint
    DataCellRenderer,
    HeaderEditRenderer,
    StudyShortcutsRenderer,
    IrodsButtonsRenderer,
    RowEditRenderer,
    DataCellEditor,
    ObjectSelectEditor,
    OntologyEditor
    /* eslint-enable vue/no-unused-components */
  },
  created () {
    if (windowsPlatforms.includes(window.navigator.platform)) {
      this.windowsOs = true
    }
    window.addEventListener('beforeunload', this.onBeforeUnload)
  },
  beforeDestroy () {
    window.removeEventListener('beforeunload', this.onBeforeUnload)
  },
  methods: {

    /* Event Handlers ------------------------------------------------------- */

    onBeforeUnload (event) {
      if (this.editMode &&
          (this.unsavedRow || this.updatingRow || this.unsavedData)) {
        event.preventDefault()
        event.returnValue = ''
      }
    },

    /* Grid Helpers --------------------------------------------------------- */

    getTableHeaderParams (gridUuid, assayMode) {
      return {
        assayMode: assayMode,
        editMode: this.editMode,
        gridUuid: gridUuid,
        projectUuid: this.projectUuid,
        sodarContext: this.sodarContext,
        studyUuid: this.currentStudyUuid,
        showNotificationCb: this.showNotification
      }
    },

    /* Grid Setup ----------------------------------------------------------- */

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

      // Get initial filter state from URL
      const filterMatch = filterRegex.exec(this.$route.fullPath)
      if (filterMatch) this.initialFilter = filterMatch.groups.filter

      // Set up current study
      this.gridOptions.study = initGridOptions(this, editMode)
      this.setCurrentStudy(studyUuid)
      this.setPath()

      // Retrieve study and assay tables for current study
      // TODO: Add timeout/retrying
      let url = this.sodarContext.studies[studyUuid].table_url
      if (editMode) url = url + '?edit=1'

      fetch(url, { credentials: 'same-origin' })
        .then(data => data.json())
        .then(data => { this.buildStudy(data) })
    },

    getColDefParams (tables, uuid, assayMode) {
      const params = {
        app: this,
        assayMode: assayMode,
        currentStudyUuid: this.currentStudyUuid,
        editContext: this.editContext,
        editMode: this.editMode,
        editStudyConfig: this.editStudyConfig,
        gridUuid: uuid,
        sampleColId: this.sampleColId,
        sampleIdx: this.sampleIdx,
        sodarContext: this.sodarContext,
        studyDisplayConfig: this.studyDisplayConfig,
        studyNodeLen: null,
        table: null
      }
      if (assayMode) {
        params.studyNodeLen = this.columnDefs.study.length - 3
        params.table = tables.assays[uuid]
      } else params.table = tables.study
      return params
    },

    buildStudy (data) {
      if ('render_error' in data) {
        this.renderError = data.render_error
        this.gridsLoaded = false
      } else {
        // Editing: Get study config
        if (this.editMode && 'study_config' in data) {
          this.editStudyConfig = data.study_config
        }
        // Editing: Get edit context
        if (this.editMode && 'edit_context' in data) {
          this.editContext = data.edit_context
        }

        // Get table heights
        this.tableHeights = data.table_heights
        // Get display config
        this.studyDisplayConfig = data.display_config
        // Store colspan
        this.sourceColSpan = data.tables.study.top_header[0].colspan

        // Store sampleColId & sampleIdx
        let colSpan = 0
        for (let i = 0; i < data.tables.study.top_header.length; i++) {
          if (data.tables.study.top_header[i].value === 'Sample') {
            this.sampleColId = 'col' + colSpan
            this.sampleIdx = colSpan + 1
            break
          }
          colSpan += data.tables.study.top_header[i].colspan
        }

        // Build study
        this.columnDefs.study = buildColDef(
          this.getColDefParams(data.tables, this.currentStudyUuid, false))
        this.rowData.study = buildRowData({
          table: data.tables.study,
          editMode: this.editMode,
          assayMode: false,
          sodarContext: this.sodarContext
        })

        // Build assays
        for (const assayUuid in data.tables.assays) {
          this.gridOptions.assays[assayUuid] = initGridOptions(this.editMode)
          this.columnDefs.assays[assayUuid] = buildColDef(
            this.getColDefParams(data.tables, assayUuid, true))
          this.rowData.assays[assayUuid] = buildRowData({
            table: data.tables.assays[assayUuid],
            editMode: this.editMode,
            assayMode: true,
            sodarContext: this.sodarContext
          })

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
      })
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
      this.$nextTick(() => { this.scrollToCurrentTable() })
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
        return
      }

      const urlMatch = studyUrlRegex.exec(this.$route.fullPath)
      if (this.$route.fullPath.indexOf('/assay/') !== -1) {
        this.activeSubPage = null
        this.setCurrentAssay(urlMatch.groups.uuid)
        for (const studyUuid in this.sodarContext.studies) {
          if (this.currentAssayUuid in
              this.sodarContext.studies[studyUuid].assays) {
            this.setCurrentStudy(studyUuid)
            break
          }
        }
      } else if (this.$route.fullPath.indexOf('/study/') !== -1) {
        this.activeSubPage = null
        this.setCurrentStudy(urlMatch.groups.uuid)
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

    handleCellEdit (upDataArr, refreshCells, verify) {
      // TODO: Add timeout / retrying
      // TODO: Cleanup unnecessary fields from JSON
      // TODO: In the future, add edited info in a queue and save periodically
      if (!Array.isArray(upDataArr)) upDataArr = [upDataArr]
      if (verify === undefined) verify = true

      fetch('/samplesheets/ajax/edit/cell/' + this.projectUuid, {
        method: 'POST',
        body: JSON.stringify({ updated_cells: upDataArr, verify: verify }),
        credentials: 'same-origin',
        headers: {
          Accept: 'application/json',
          'Content-Type': 'application/json',
          'X-CSRFToken': this.sodarContext.csrf_token
        }
      }).then(data => data.json())
        .then(
          data => {
            const gridUuids = this.getStudyGridUuids()
            if (data.detail === 'ok') {
              this.showNotification('Saved', 'success', 1000)
              this.editDataUpdated = true
              this.versionSaved = false
              // Update other occurrences of cell in UI
              for (let i = 0; i < gridUuids.length; i++) {
                this.updateCellUIValues(
                  this.getGridOptionsByUuid(
                    gridUuids[i]).api, upDataArr, refreshCells, false)
              }
            } else if (data.detail === 'alert') {
              // Handle verification alert from server
              if (confirm(data.alert_msg)) {
                // Call edit again
                this.handleCellEdit(upDataArr, refreshCells, false)
              } else {
                // Revert values in UI
                for (let i = 0; i < gridUuids.length; i++) {
                  this.updateCellUIValues(
                    this.getGridOptionsByUuid(
                      gridUuids[i]).api, upDataArr, refreshCells, true)
                }
              }
            } else {
              console.log('Save status: ' + data.detail) // DEBUG
              this.showNotification('Saving Failed', 'danger', 1000)
              // TODO: Mark invalid/unsaved field(s) in UI
            }
          }
        ).catch(function (error) {
          console.log('Error saving data: ' + error.detail)
        })
    },

    updateCellUIValues (gridApi, upDataArr, refreshCells, revert) {
      for (let i = 0; i < upDataArr.length; i++) {
        const upData = upDataArr[i]
        const fieldId = upData.header_field
        gridApi.forEachNode(function (rowNode) {
          const value = rowNode.data[fieldId]
          if (value && value.uuid === upData.uuid) {
            if (revert) value.value = upData.og_value
            else value.value = upData.value
            value.unit = upData.unit // TODO: Add support for reverting unit
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
          value.value = [] // By default, send empty list to server
        }
      }
      // Default unit
      if (editConfig && 'unit_default' in editConfig) {
        value.unit = editConfig.unit_default
      }

      return value
    },

    getNamePrefix (rowNode, cols, startIdx) {
      // Get name prefix for suffix name filling
      let namePrefix
      for (let i = 1; i < startIdx; i++) {
        const prevHeaderInfo = cols[i].colDef.cellEditorParams.headerInfo
        if (['name', 'process_name'].includes(prevHeaderInfo.header_type) &&
            prevHeaderInfo.item_type !== 'DATA') {
          namePrefix = rowNode.data[cols[i].colId].value
        }
      }
      return namePrefix
    },

    enableNextNodes (rowNode, gridOptions, gridUuid, startIdx) {
      // Enable editing for the next node(s) when inserting a new row
      // NOTE: Can't access cellEditorParams here as they are set dynamically
      const cols = gridOptions.columnApi.getColumns()
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
            value.value = this.getNamePrefix(rowNode, cols, startIdx) + value.value
            let createNew = true

            // Check if name already appears in column, update UUID if found
            gridOptions.api.forEachNode(function (r) {
              if (r.data[nextColId].value === value.value) {
                createNew = false
                value.uuid = r.data[nextColId].uuid
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
          let processActive = false
          let newInit = true
          let forceEmpty = false

          while (i < cols.length - 1 &&
              cols[i].originalParent.groupId === nextGroupId) {
            nextColId = cols[i].colId
            const value = this.getDefaultValue(nextColId, gridOptions, newInit, forceEmpty)
            const headerType = cols[i].colDef.cellEditorParams.headerInfo.header_type

            if (headerType === 'protocol') {
              value.editable = true
              if ('uuid_ref' in value && value.uuid_ref) {
                processActive = true
                newInit = false
                value.newInit = false // Update protocol ref column newInit
              } else forceEmpty = true
            } else if (headerType === 'process_name') {
              // Fill process name with default suffix if set
              const namePrefix = this.getNamePrefix(rowNode, cols, i)
              if (namePrefix && value.value) {
                value.value = namePrefix + value.value
                newInit = false
                value.newInit = false
                processActive = true
              } else value.value = '' // HACK: Reset default value if not filled
              value.editable = true // Process name should always be editable
            } else {
              // Only allow editing the rest of the cells if protocol is set
              if (processActive) {
                value.editable = cols[i].colDef.cellRendererParams.fieldEditable
              } else value.editable = false
            }
            rowNode.setDataValue(nextColId, value)
            i += 1
          }

          // If default protocol or name was filled, enable the next node(s) too
          if (processActive) enableNextIdx = i
        }
        // If we can immediately enable the next node(s), proceed
        if (enableNextIdx && enableNextIdx < cols.length - 1) {
          this.enableNextNodes(rowNode, gridOptions, gridUuid, enableNextIdx)
        }
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
        const studyCols = studyOptions.columnApi.getColumns()
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
      const cols = columnApi.getColumns()
      let nextNodeStartIdx = null
      // Since we split the source group we have to apply some trickery
      const parent = column.originalParent
      let groupId = parent.groupId
      if (groupId === '1' && this.sourceColSpan > 1) groupId = '2'
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
      const cols = gridOptions.columnApi.getColumns()
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
      this.unsavedRow = { gridUuid: gridUuid, id: res.add[0].id }
      gridApi.ensureIndexVisible(res.add[0].rowIndex) // Scroll to inserted row
      if (!assayMode) gridApi.ensureColumnVisible('col2') // Scroll to column
      else gridApi.ensureColumnVisible(this.sampleColId)
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
            if (data.detail === 'ok') {
              const cols = gridOptions.columnApi.getColumns()
              let nodeIdx = 0
              let sampleUuid
              let sampleName
              let startIdx = 1
              let lastSourceGroupIdx = 1
              if (this.sourceColSpan > 1) lastSourceGroupIdx = 2 // 2nd source group
              const lastSourceGroupId = cols[lastSourceGroupIdx].originalParent.groupId
              let groupId = cols[1].originalParent.groupId

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

                if (i < cols.length - 2 &&
                    groupId !== cols[i + 1].originalParent.groupId &&
                    cols[i + 1].originalParent.groupId !== lastSourceGroupId) {
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
                  name: sampleName, assays: []
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
              this.versionSaved = false
              this.showNotification('Row Inserted', 'success', 1000)
            } else {
              console.log('Row insert status: ' + data.detail) // DEBUG
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
        .then(data => {
          if (data.detail === 'ok') {
            this.editDataUpdated = true
            // Update sample list
            const sampleUuid = rowNode.data[this.sampleColId].uuid
            const sampleColId = this.sampleColId

            if (assayMode &&
                !(gridUuid in this.editContext.samples[sampleUuid].assays)) {
              let sampleFound = false
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
            } else if (!assayMode) {
              // Delete sample from editcontext if deleted from study
              let sampleFound = false
              gridOptions.api.forEachNode(function (r) {
                if (r.data[sampleColId].uuid === sampleUuid &&
                    r.id !== rowNode.id) {
                  sampleFound = true
                }
              })
              if (!sampleFound) delete this.editContext.samples[sampleUuid]
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
            console.log('Row delete status: ' + data.detail) // DEBUG
            this.showNotification('Delete Failed', 'danger', 1000)
          }
          finishCallback()
          this.updatingRow = false
        }).catch(this.handleRowUpdateError)
    },

    handleRowUpdateError (error) {
      this.updatingRow = false
      console.log('Error updating row: ' + error.detail)
    },

    handleFinishEditing () {
      fetch('/samplesheets/ajax/edit/finish/' + this.projectUuid, {
        method: 'POST',
        body: JSON.stringify({
          updated: this.editDataUpdated,
          version_saved: this.versionSaved
        }),
        credentials: 'same-origin',
        headers: {
          Accept: 'application/json',
          'Content-Type': 'application/json',
          'X-CSRFToken': this.sodarContext.csrf_token
        }
      }).then(data => data.json())
        .then(data => {
          if (data.detail === 'ok') {
            this.showNotification('Finished Editing', 'success', 1500)
          } else {
            console.log('Finish status: ' + data.detail) // DEBUG
            this.showNotification('Saving Version Failed', 'danger', 1000)
          }
        }).catch(function (error) {
          console.log('Error saving version: ' + error.detail)
          this.showNotification('Finishing Error', 'danger', 2000)
        })
      this.editStudyConfig = null
    },

    setDataUpdated (updated) {
      this.editDataUpdated = updated
    },

    setUnsavedData (unsaved) {
      this.unsavedData = unsaved
    },

    setVersionSaved (saved) {
      this.versionSaved = saved
    },

    /* Data and App Access -------------------------------------------------- */

    getStudyGridUuids (assayOnly) {
      // Return array of UUIDs for the current study and all assays
      if (!this.currentStudyUuid) return null
      const uuids = assayOnly ? [] : [this.currentStudyUuid]
      for (const k in this.columnDefs.assays) uuids.push(k)
      return uuids
    },

    getGridOptionsByUuid (uuid) {
      // TODO: Make sure this new method works! (If not, use $refs)
      if (uuid === this.currentStudyUuid) {
        return this.gridOptions.study
      } else if (uuid in this.columnDefs.assays) {
        return this.gridOptions.assays[uuid]
      }
    },

    getApp () {
      // Workaround for #520
      // TODO: Still needed?
      return this
    },

    findNextNodeIdx (cols, idx, maxIdx) {
      // Find next node index or null if not found
      // TODO: Use this wherever performing similar iteration
      const groupId = cols[idx].originalParent.groupId
      if (!maxIdx) maxIdx = cols.length
      while (idx < maxIdx) {
        if (groupId !== cols[idx].originalParent.groupId) return idx
        idx += 1
      }
      return null // TODO: Undefined ok?
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
        if (!this.activeSubPage) this.getStudy(this.currentStudyUuid)
      } else {
        this.sheetsAvailable = false
      }

      this.sheetSyncEnabled = this.sodarContext.sheet_sync_enabled
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

.ag-body-viewport {
  background-color: #eee;
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

.sodar-ss-row-btn {
  width: 26px !important; /* Quick HACK for uniform button size */
}

a.sodar-ss-data-ext-link {
  color: #ffffff;
  text-decoration: underline;
}

a.sodar-ss-data-ext-link:hover {
  text-decoration: none;
}

/* Common editor styles */

.sodar-ss-data-cell-popup {
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

div.sodar-ss-data-cell-busy {
  line-height: 38px !important;
  vertical-align: middle;
}

select#sodar-ss-data-cell-unit {
  margin-left: 4px;
}

.sodar-ss-select-firefox {
  padding-left: 8px !important;
}

input.sodar-ss-popup-input,
select.sodar-ss-popup-input {
  border: 1px solid #ced4da;
  border-radius: .25rem;
}

/* Fix forced outline on modal close buttons in Chrome */
button.close:focus {
  outline: none !important;
}

</style>
