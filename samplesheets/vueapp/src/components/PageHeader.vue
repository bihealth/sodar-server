<template>
  <div class="row sodar-subtitle-container bg-white sticky-top"
       id="sodar-ss-subtitle">
    <h3 class="text-nowrap">
      <i class="iconify" data-icon="mdi:flask" /> Sample Sheets
    </h3>
    <b-nav
        v-if="app.sheetsAvailable"
        id="sodar-ss-nav-tabs"
        pills
        class="sodar-ss-nav ml-4 mr-auto">
      <b-nav-item
          v-for="(studyInfo, studyUuid, index) in app.sodarContext.studies"
          class="sodar-ss-tab-study"
          :id="'sodar-ss-tab-study-' + studyUuid"
          :key="index"
          @click="handleNavCallback(studyUuid)"
          v-b-tooltip.hover
          :title="getStudyNavTitle(studyInfo.display_name)"
          :active="studyUuid === app.currentStudyUuid && !app.activeSubPage"
          :disabled="!app.sheetsAvailable || app.gridsBusy">
        <i class="iconify" data-icon="mdi:folder-table"></i>
        {{ studyInfo.display_name | truncate(20) }}
      </b-nav-item>
      <b-nav-item
          id="sodar-ss-tab-overview"
          @click="showSubPageCallback('overview')"
          :active="app.activeSubPage === 'overview'"
          :disabled="!app.sheetsAvailable || app.gridsBusy || app.editMode">
        <i class="iconify" data-icon="mdi:sitemap"></i> Overview
      </b-nav-item>
    </b-nav>
    <div class="ml-auto align-middle">
      <notify-badge ref="notifyBadge"></notify-badge>
      <span v-if="app.editMode"
            class="badge badge-pill badge-info mr-2"
            id="sodar-ss-badge-edit">
        <a id="sodar-ss-link-edit-help"
           @click="editorHelpModal.showModal()"
           title="Editor status"
           v-b-tooltip.hover>
          <i class="iconify mr-1" data-icon="mdi:lead-pencil"></i>
          <span v-if="app.unsavedData || app.unsavedRow">Unsaved Changes</span>
          <span v-else-if="app.editDataUpdated">Changes Saved</span>
          <span v-else>Edit Mode</span>
        </a>
      </span>
      <!-- Nav dropdown -->
      <b-dropdown
          v-if="app.sheetsAvailable"
          id="sodar-ss-nav-dropdown"
          :disabled="app.gridsBusy"
          right
          variant="success">
        <template slot="button-content">
          <i class="iconify" data-icon="mdi:menu"></i><!-- TODO: Height -->
        </template>
        <span v-for="(studyInfo, studyUuid, index) in app.sodarContext.studies"
              :key="index">
          <b-dropdown-item
              href="#"
              :id="'sodar-ss-nav-study-' + studyUuid"
              class="sodar-ss-nav-item"
              @click="handleNavCallback(studyUuid)">
            <i class="iconify text-info" data-icon="mdi:folder-table"></i>
            {{ studyInfo.display_name }}
          </b-dropdown-item>
          <b-dropdown-item
              v-for="(assayInfo, assayUuid, assayIndex) in studyInfo.assays"
              :key="assayIndex"
              href="#"
              :id="'sodar-ss-nav-assay-' + assayUuid"
              class="sodar-ss-nav-item"
              @click="handleNavCallback(studyUuid, assayUuid)">
            <i class="iconify text-danger ml-4" data-icon="mdi:table-large"></i>
            {{ assayInfo.display_name }}
          </b-dropdown-item>
        </span>
        <b-dropdown-item
          href="#"
          id="sodar-ss-nav-overview"
          class="sodar-ss-nav-item"
          :disabled="app.editMode"
          @click="showSubPageCallback('overview')">
          <i class="iconify" data-icon="mdi:sitemap"></i> Overview
        </b-dropdown-item>
      </b-dropdown>
      <!-- Save version button (only show in edit mode) -->
      <b-button
          v-if="app.editMode"
          id="sodar-ss-btn-version-save"
          variant="primary"
          class="ml-1"
          title="Save current sheet version as backup"
          :disabled="app.versionSaved"
          @click="versionSaveModal.showModal()"
          v-b-tooltip.hover>
        <i class="iconify" data-icon="mdi:content-save-all"></i>
      </b-button>
      <!-- Operations dropdown (only show if not in edit mode) -->
      <b-dropdown
          v-if="!app.editMode"
          id="sodar-ss-op-dropdown"
          :disabled="app.gridsBusy ||
                     (!app.sheetsAvailable && !app.sodarContext.perms.edit_sheet) ||
                     (app.sheetsAvailable && !app.sodarContext.perms.view_tickets)"
          right
          variant="primary"
          text="Sheet Operations">
        <b-dropdown-item
            v-if="app.sheetSyncEnabled && app.sodarContext.perms.edit_sheet"
            class="sodar-ss-op-item"
            id="sodar-ss-op-item-sync"
            :href="'sync/' + app.projectUuid">
          <i class="iconify" data-icon="mdi:table-refresh"></i> Sync Sheets
        </b-dropdown-item>
        <b-dropdown-item
            v-if="!app.sheetsAvailable && !app.sheetSyncEnabled && app.sodarContext.perms.edit_sheet"
            class="sodar-ss-op-item"
            id="sodar-ss-op-item-import"
            :href="'import/' + app.projectUuid">
          <i class="iconify" data-icon="mdi:upload"></i> Import ISA-Tab
        </b-dropdown-item>
        <b-dropdown-item
            v-if="!app.sheetsAvailable && !app.sheetSyncEnabled && app.sodarContext.perms.edit_sheet"
            class="sodar-ss-op-item"
            id="sodar-ss-op-item-create"
            :href="'template/select/' + app.projectUuid">
          <i class="iconify" data-icon="mdi:auto-fix"></i> Create from Template
        </b-dropdown-item>
        <b-dropdown-item
            v-if="app.sheetsAvailable && !app.sheetSyncEnabled && app.sodarContext.perms.edit_sheet"
            class="sodar-ss-op-item"
            id="sodar-ss-op-item-edit"
            @click="toggleEditModeCallback"
            :disabled="!app.sodarContext.allow_editing">
          <i class="iconify" data-icon="mdi:lead-pencil"></i> Edit Sheets
        </b-dropdown-item>
        <b-dropdown-item
            v-if="app.sheetsAvailable && app.sodarContext.perms.edit_sheet"
            class="sodar-ss-op-item"
            id="sodar-ss-op-item-warnings"
            :disabled="!app.sodarContext.parser_warnings"
            @click="showSubPageCallback('warnings')">
          <i class="iconify" data-icon="mdi:alert"></i> View Parser Warnings
        </b-dropdown-item>
        <b-dropdown-item
            v-if="app.sheetsAvailable &&
                  app.sodarContext.irods_status &&
                  app.sodarContext.perms.update_cache"
            class="sodar-ss-op-item"
            id="sodar-ss-op-item-cache"
            :href="'cache/update/' + app.projectUuid">
          <i class="iconify" data-icon="mdi:database-refresh"></i> Update Sheet Cache
        </b-dropdown-item>
        <b-dropdown-item
            v-if="app.sheetsAvailable &&
                  !app.sheetSyncEnabled &&
                  app.sodarContext.perms.edit_sheet"
            class="sodar-ss-op-item"
            id="sodar-ss-op-item-replace"
            :href="'import/' + app.projectUuid">
          <i class="iconify" data-icon="mdi:upload"></i> Replace ISA-Tab
        </b-dropdown-item>
        <b-dropdown-item
            v-if="app.sheetsAvailable && !app.windowsOs"
            class="sodar-ss-op-item"
            id="sodar-ss-op-item-export"
            :href="'export/isa/' + app.projectUuid">
          <i class="iconify" data-icon="mdi:download"></i> Export ISA-Tab
        </b-dropdown-item>
        <b-dropdown-item
            v-else-if="app.sheetsAvailable && app.windowsOs"
            class="sodar-ss-op-item"
            id="sodar-ss-op-item-export"
            @click="winExportModal.showModal()">
          <i class="iconify" data-icon="mdi:download"></i> Export ISA-Tab
        </b-dropdown-item>
        <b-dropdown-item
            v-if="app.sheetsAvailable &&
                  !app.renderError &&
                  app.sodarContext.perms.create_colls"
            class="sodar-ss-op-item"
            id="sodar-ss-op-item-irods"
            :href="'collections/' + app.projectUuid">
          <span v-if="app.sodarContext.irods_status">
            <i class="iconify" data-icon="mdi:database-refresh"></i>
            Update iRODS Collections
          </span>
          <span v-else>
            <i class="iconify" data-icon="mdi:database-plus"></i>
            Create iRODS Collections
          </span>
        </b-dropdown-item>
        <b-dropdown-item
            v-if="app.sheetsAvailable && !app.sheetSyncEnabled"
            class="sodar-ss-op-item"
            id="sodar-ss-op-item-versions"
            :href="'versions/' + app.projectUuid">
          <i class="iconify" data-icon="mdi:table-search"></i> Sheet Versions
        </b-dropdown-item>
        <b-dropdown-item
            v-if="app.sheetsAvailable &&
                  app.sodarContext.irods_status &&
                  app.sodarContext.perms.view_tickets"
            class="sodar-ss-op-item"
            id="sodar-ss-op-item-tickets"
            :href="'irods/tickets/' + app.projectUuid">
          <i class="iconify" data-icon="mdi:ticket"></i> iRODS Access Tickets
        </b-dropdown-item>
        <b-dropdown-item
            v-if="app.sheetsAvailable &&
                  app.sodarContext.irods_status &&
                  app.sodarContext.perms.edit_sheet"
            class="sodar-ss-op-item"
            id="sodar-ss-op-item-requests"
            :href="'irods/requests/' + app.projectUuid">
          <i class="iconify" data-icon="mdi:trash-can"></i> iRODS Delete Requests
        </b-dropdown-item>
        <b-dropdown-item
            v-if="app.sheetsAvailable &&
                  app.sodarContext.perms.delete_sheet &&
                  !app.sheetSyncEnabled"
            class="sodar-ss-op-item"
            id="sodar-ss-op-item-delete"
            variant="danger"
            :href="'delete/' + app.projectUuid">
          <i class="iconify" data-icon="mdi:close-thick"></i> Delete Sheets
          <span v-if="app.sodarContext.irods_status">and Data</span>
        </b-dropdown-item>
      </b-dropdown>
      <!-- Finish editing button (replace op dropdown in edit mode) -->
      <b-button
          v-if="app.editMode"
          variant="primary"
          class="text-left"
          id="sodar-ss-btn-edit-finish"
          :title="getFinishEditTitle()"
          :disabled="app.unsavedRow !== null"
          @click="toggleEditModeCallback"
          v-b-tooltip.hover>
        Finish Editing
        <span class="pull-right">
          <i class="iconify" data-icon="mdi:check-bold"></i>
        </span>
      </b-button>
    </div>
  </div>
</template>

<script>
import NotifyBadge from './NotifyBadge.vue'

export default {
  name: 'PageHeader',
  components: { NotifyBadge },
  props: [
    'app',
    'handleNavCallback',
    'showSubPageCallback',
    'toggleEditModeCallback',
    'editorHelpModal',
    'winExportModal',
    'versionSaveModal'
  ],
  data () {
    return {
      notifyVisible: false,
      notifyMessage: null,
      notifyClasses: 'badge badge-pill sodar-ss-nofify mx-2',
      editMessage: null,
      editVariant: 'info'
    }
  },
  methods: {
    getStudyNavTitle (studyName) {
      if (studyName.length > 20) return studyName
    },
    showNotification (message, variant, delay) {
      this.notifyClasses = 'badge badge-pill sodar-ss-nofify mx-2 badge-'
      if (variant) this.notifyClasses += variant
      else this.notifyClasses += 'light'

      this.notifyMessage = message
      this.notifyVisible = true
      setTimeout(() => {
        this.notifyVisible = false
        this.notifyMessage = null
      }, delay || 2000)
    },
    getFinishEditTitle () {
      if (!this.app.unsavedRow) {
        let title = 'Exit edit mode'
        if (!this.app.versionSaved) {
          title += ' and save current sheet version as backup'
        }
        return title
      } else {
        return 'Please save or discard your unsaved table row before exiting edit mode'
      }
    },
    getEditModeBadgeText () {
      if (this.app.unsavedData) return 'Unsaved Changes'
      return 'Edit Mode'
    }
  }
}
</script>

<style scoped>

div#sodar-ss-op-dropdown {
  margin-left: 4px;
}

/* Force bg-success to active nav link (not supported by boostrap-vue) */
ul.sodar-ss-nav li a.active {
  background-color: #28a745 !important;
}

button#sodar-ss-btn-edit-finish {
  margin-left: 4px;
  width: 163px;
}

/* Hide navbar if browser is too narrow */
@media screen and (max-width: 1300px) {
  .sodar-ss-nav {
    display: none;
  }
}

</style>
