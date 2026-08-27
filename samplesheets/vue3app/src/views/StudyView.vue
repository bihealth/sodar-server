<script setup lang="ts">
import { nextTick, onMounted, useTemplateRef, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useToast } from 'bootstrap-vue-next'

import AssayShortcutCard from '@/components/AssayShortcutCard.vue'
import ColumnConfigModal from '@/components/modals/ColumnConfigModal.vue'
import ColumnToggleModal from '@/components/modals/ColumnToggleModal.vue'
import DataCellEditor from '@/components/editors/DataCellEditor.vue'
import DataCellRenderer from '@/components/renderers/DataCellRenderer.vue'
import HeaderEditRenderer from '@/components/renderers/HeaderEditRenderer.vue'
import IrodsButtonsRenderer from '@/components/renderers/IrodsButtonsRenderer.vue'
import IrodsDirModal from '@/components/modals/IrodsDirModal.vue'
import ObjectSelectEditor from '@/components/editors/ObjectSelectEditor.vue'
import OntologyEditModal from '@/components/modals/OntologyEditModal.vue'
import OntologyEditor from '@/components/editors/OntologyEditor.vue'
import RowEditRenderer from '@/components/renderers/RowEditRenderer.vue'
import SheetTable from '@/components/SheetTable.vue'
import SheetTableHeader from '@/components/SheetTableHeader.vue'
import StudyShortcutModal from '@/components/modals/StudyShortcutModal.vue'
import StudyShortcutsRenderer from '@/components/renderers/StudyShortcutsRenderer.vue'
import WaitSection from '@/components/WaitSection.vue'

import { useAppStore } from '@/stores/appStore.ts'
import { useEditStore } from '@/stores/editStore.ts'
import { useTableStore } from '@/stores/tableStore.ts'

import { getAjaxRequestInit } from '@/utils/appUtils.ts'
import {
  buildColDef,
  buildRowData,
  initGridOptions
} from '@/utils/gridUtils.ts'
import { getNotifyCb } from '@/utils/notifyCb.ts'
import {
  type AssayRenderTable,
  type AssayShortcuts,
  type ColDefBuildParams,
  type RenderTableData,
  type StudyEditConfig,
  type StudyEditContext
} from '@/types.ts'

// External Data ---------------------------------------------------------------

// Set up route
const route = useRoute()
// Set up stores
const appStore = useAppStore()
const editStore = useEditStore()
const tableStore = useTableStore()

// Init notify callback for bootstrap-vue-next toasts
const { create } = useToast()
appStore.notifyCb = getNotifyCb(create)

// Set up template references
const colConfigCompRef = useTemplateRef('columnConfigModalComponent')
const colToggleCompRef = useTemplateRef('columnToggleModalComponent')
const irodsDirCompRef = useTemplateRef('irodsDirModalComponent')
const ontologyEditCompRef = useTemplateRef('ontologyEditModalComponent')
const studyShortcutCompRef = useTemplateRef('studyShortcutModalComponent')

// Helpers ---------------------------------------------------------------------

function buildStudy (data: RenderTableData) {
  // TODO: Handle render_error
  if (appStore.editMode && 'study_config' in data) {
    tableStore.studyEditConfig = data.study_config as StudyEditConfig
  }
  if (appStore.editMode && 'edit_context' in data) {
    editStore.editContext = data.edit_context as StudyEditContext
  }
  tableStore.tableHeights = data.table_heights
  tableStore.studyDisplayConfig = data.display_config
  tableStore.sourceColSpan = data.tables.study.top_header[0]?.colspan || -1

  // Store sampleColId & sampleIdx
  let colSpan = 0
  for (let i = 0; i < data.tables.study.top_header.length; i++) {
    if (data.tables.study.top_header[i]?.value === 'Sample') {
      tableStore.sampleColId = 'col' + colSpan
      tableStore.sampleIdx = colSpan + 1
      break
    }
    colSpan += data.tables.study.top_header[i]?.colspan || 1
  }

  // Build study gridOptions, columnDefs and rowData
  tableStore.gridOptions.study = initGridOptions({}, appStore.editMode)
  const colDefBuildParams: ColDefBuildParams = {
    assayMode: false,
    irodsDirModal: irodsDirCompRef,
    studyNodeLen: data.tables.study.top_header.length,
    studyShortcutModal: studyShortcutCompRef,
    table: data.tables.study,
    tableUuid: appStore.currentStudyUuid,
  }
  if (appStore.editMode) {
    colDefBuildParams.colConfigModal = colConfigCompRef
    colDefBuildParams.ontologyEditModal = ontologyEditCompRef
  }
  tableStore.columnDefs.study = buildColDef(colDefBuildParams)
  tableStore.rowData.study = buildRowData(data.tables.study, false)

  for (const assayUuid in data.tables.assays) {
    // Build assay gridOptions, columnDefs and rowData
    tableStore.gridOptions.assays[assayUuid] = initGridOptions(
      {}, appStore.editMode)
    const assayTable = data.tables.assays[assayUuid] as AssayRenderTable
    tableStore.columnDefs.assays[assayUuid] = buildColDef(
        Object.assign(colDefBuildParams, {
          assayMode: true,
          table: assayTable,
          tableUuid: assayUuid
        }))
    tableStore.rowData.assays[assayUuid] = buildRowData(assayTable, true)

    // Get assay shortcuts
    if ('shortcuts' in (data.tables.assays[assayUuid] as AssayRenderTable)) {
      tableStore.assayShortcuts[
        assayUuid] = (
          (data.tables.assays[assayUuid] as AssayRenderTable)
            .shortcuts as AssayShortcuts)
    }
  }
}

function getStudy (studyUuid: string, editMode: boolean) {
  // Clear existing data
  appStore.gridsBusy = true
  appStore.gridsLoaded = false
  tableStore.$reset() // TODO: $reset() might not work here, see #2511
  editStore.$reset()
  // Set filter state
  if (route.query.filter) {
    tableStore.initialFilter = route.query.filter as string
    route.query.filter = '' // Clear filter from further navigation
  }

  // Retrieve study tables
  let url: string = appStore.sodarContext!.studies[studyUuid]!.table_url
  if (editMode) url += '?edit=1'
  // TODO: Add timeout / retrying / error handling
  fetch(url, getAjaxRequestInit())
    .then(data => data.json())
    .then(data => {
      buildStudy(data)
      appStore.gridsBusy = false
      appStore.gridsLoaded = true
      scrollToCurrentTable()
    })
}

async function scrollToCurrentTable () {
  await nextTick() // Ensure DOM is rendered
  if (appStore.gridsLoaded && 'assayUuid' in route.params) {
    const anchorId = 'assay-anchor-' + route.params.assayUuid
    const anchorElem = document.getElementById(anchorId)
    if (anchorElem) anchorElem.scrollIntoView()
  } else {
    const anchorElem = document.getElementsByClassName('sodar-app-container')[0]
    if (anchorElem) anchorElem.scrollTop = 0
  }
}

// API and Life Cycle ----------------------------------------------------------

// Expose components for ag-grid
defineExpose({
  DataCellEditor,
  DataCellRenderer,
  HeaderEditRenderer,
  IrodsButtonsRenderer,
  ObjectSelectEditor,
  OntologyEditor,
  RowEditRenderer,
  StudyShortcutsRenderer
})

// Update current study UUID based on route
if ('studyUuid' in route.params &&
    appStore.currentStudyUuid !== route.params.studyUuid) {
  appStore.currentStudyUuid = route.params.studyUuid!.toString()
}
// Get initial study once sodarContext is retrieved
if (appStore.sheetsAvailable && !appStore.gridsLoaded) {
  getStudy(appStore.currentStudyUuid, appStore.editMode)
} else {
  watch(() => appStore.sodarContext, (newContext) => {
    if (newContext !== null && appStore.sheetsAvailable) {
      getStudy(appStore.currentStudyUuid, appStore.editMode)
    }
  })
}
// Get new study when study UUID or edit mode are updated
watch(() =>
    [appStore.currentStudyUuid, appStore.editMode],
    ([newUuid, newEditMode]) => {
  getStudy(newUuid as string, newEditMode as boolean)
})
onMounted(() => {
  // Scroll to current table on load
  if (appStore.gridsLoaded) {
    scrollToCurrentTable()
  }
})
</script>

<template>
  <div v-if="!appStore.gridsBusy && appStore.gridsLoaded">
    <!-- Study -->
    <SheetTableHeader
        :assay-mode="false"
        :table-uuid="appStore.currentStudyUuid">
    </SheetTableHeader>
    <SheetTable
        :assay-mode="false"
        :col-toggle-modal-ref="colToggleCompRef"
        :table-uuid="appStore.currentStudyUuid">
    </SheetTable>
    <!-- Assays -->
    <div v-for="assayUuid in
                Object.keys(appStore.sodarContext!.studies[
                  appStore.currentStudyUuid]!.assays)"
         :key="assayUuid">
      <a class="sodar-ss-anchor"
         :id="'assay-anchor-' + assayUuid.toString()"></a>
      <SheetTableHeader
          :assay-mode="true"
          :table-uuid="assayUuid">
      </SheetTableHeader>
      <AssayShortcutCard
          v-if="!appStore.editMode &&
                appStore.getPerm('view_files') &&
                appStore.sodarContext!.irods_status &&
                assayUuid in tableStore.assayShortcuts"
          :assay-uuid="assayUuid"
          :modal-ref="irodsDirCompRef">
      </AssayShortcutCard>
      <SheetTable
          :assay-mode="true"
          :col-toggle-modal-ref="colToggleCompRef"
          :table-uuid="assayUuid">
      </SheetTable>
    </div>
  </div>
  <div v-else-if="appStore.sodarContext && !appStore.sheetsAvailable">
    <div class="alert alert-info" id="sodar-ss-alert-empty">
      No sample sheets are currently available for this project.
      <span v-if="appStore.getPerm('edit_sheet') &&
                  !appStore.sodarContext!.sheet_sync_enabled">
        To add sample sheets, please import them from an existing ISA-Tab
        investigation, create new sheets from a template or enable remote
        sheet synchonization.
      </span>
      <span v-if="appStore.getPerm('edit_sheet') &&
                  appStore.sodarContext!.sheet_sync_enabled">
        To add sample sheets, please wait for the synchonization to take
        place or trigger the synchonization manually.
      </span>
    </div>
  </div>
  <WaitSection v-else></WaitSection>
  <!-- Modals -->
  <ColumnConfigModal
      id="sodar-ss-col-config-modal-component"
      ref="columnConfigModalComponent">
  </ColumnConfigModal>
  <ColumnToggleModal
      id="sodar-ss-col-toggle-modal-component"
      ref="columnToggleModalComponent">
  </ColumnToggleModal>
  <IrodsDirModal
      id="sodar-ss-irods-dir-modal-component"
      ref="irodsDirModalComponent">
  </IrodsDirModal>
  <OntologyEditModal
      id="sodar-ss-ontology-edit-modal-component"
      ref="ontologyEditModalComponent">
  </OntologyEditModal>
  <StudyShortcutModal
      id="sodar-ss-study-shortcut-modal-component"
      ref="studyShortcutModalComponent">
  </StudyShortcutModal>
</template>

<style scoped>
</style>
