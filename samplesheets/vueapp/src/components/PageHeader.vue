<template>
  <div class="row sodar-subtitle-container bg-white sticky-top"
       id="sodar-ss-vue-subtitle">
    <h3><i class="fa fa-flask"></i> Sample Sheets</h3>
    <b-nav v-if="app.sheetsAvailable"
           id="sodar-ss-nav-tabs"
           pills
           class="sodar-ss-nav ml-4 mr-auto">
      <b-nav-item v-for="(studyInfo, studyUuid, index) in app.sodarContext.studies"
                  :id="'sodar-ss-tab-study-' + studyUuid"
                  :key="index"
                  @mousedown="app.handleStudyNavigation(studyUuid)"
                  v-b-tooltip.hover
                  :title="getStudyNavTitle(studyInfo.display_name)"
                  :active="studyUuid === app.currentStudyUuid && !app.activeSubPage"
                  :disabled="!app.sheetsAvailable || app.gridsBusy">
        <i class="fa fa-list-alt"></i> {{ studyInfo.display_name | truncate(20) }}
      </b-nav-item>
      <b-nav-item id="sodar-ss-tab-overview"
                  @mousedown="app.showSubPage('overview')"
                  :active="app.activeSubPage === 'overview'"
                  :disabled="!app.sheetsAvailable || app.gridsBusy || app.editMode">
        <i class="fa fa-sitemap"></i> Overview
      </b-nav-item>
    </b-nav>
    <div class="ml-auto">
      <notify-badge ref="notifyBadge"></notify-badge>
      <span v-if="app.editMode"
            :class='"badge badge-pill badge-" + editVariant'
            id="sodar-ss-vue-badge-edit">
        <i class="fa fa-pencil"></i> {{ editMessage }}
      </span>
      <a v-if="app.editMode"
         title="Editor status and help"
         class="pl-1 pr-2"
         id="sodar-ss-vue-link-edit-help"
         @click="app.$refs.editorHelpModal.showModal()"
         v-b-tooltip.hover>
        <i class="fa fa-info-circle text-info"></i>
      </a>
      <!-- Nav dropdown -->
      <b-dropdown
          id="sodar-ss-nav-dropdown"
          :disabled="!app.sheetsAvailable || app.gridsBusy"
          right
          variant="success">
        <template slot="button-content">
          <i class="fa fa-bars"></i>
        </template>
        <span v-for="(studyInfo, studyUuid, index) in app.sodarContext.studies"
              :key="index">
          <b-dropdown-item
              href="#"
              :id="'sodar-ss-nav-study-' + studyUuid"
              class="sodar-ss-nav-item"
              @click="app.handleStudyNavigation(studyUuid)">
            <i class="fa fa-fw fa-list-alt text-info"></i> {{ studyInfo.display_name }}
          </b-dropdown-item>
          <b-dropdown-item
              v-for="(assayInfo, assayUuid, assayIndex) in studyInfo.assays"
              :key="assayIndex"
              href="#"
              :id="'sodar-ss-nav-assay-' + assayUuid"
              class="sodar-ss-nav-item"
              @click="app.handleStudyNavigation(studyUuid, assayUuid)">
            <i class="fa fa-fw fa-table text-danger ml-4"></i> {{ assayInfo.display_name }}
          </b-dropdown-item>
        </span>
        <b-dropdown-item
          href="#"
          id="sodar-ss-nav-overview"
          class="sodar-ss-nav-item"
          :disabled="app.editMode"
          @click="app.showSubPage('overview')">
          <i class="fa fa-fw fa-sitemap"></i> Overview
        </b-dropdown-item>
      </b-dropdown>
      <!-- Operations dropdown (only show if not in edit mode -->
      <b-dropdown
          v-if="!app.editMode"
          id="sodar-ss-op-dropdown"
          :disabled="app.gridsBusy || !app.sodarContext.perms.edit_sheet"
          right
          variant="primary"
          text="Sheet Operations">
        <b-dropdown-item
            v-if="!app.sheetsAvailable"
            class="sodar-ss-op-item"
            :href="'import/' + app.projectUuid">
          <i class="fa fa-fw fa-upload"></i> Import ISAtab
        </b-dropdown-item>
        <b-dropdown-item
            v-if="app.sheetsAvailable"
            class="sodar-ss-op-item"
            id="sodar-ss-op-item-edit"
            @click="toggleEditMode"
            :disabled="!app.sodarContext.allow_editing">
          <i class="fa fa-fw fa-pencil"></i> Edit Sheets
        </b-dropdown-item>
        <b-dropdown-item
            v-if="app.sheetsAvailable"
            class="sodar-ss-op-item"
            :disabled="!app.sodarContext.parser_warnings"
            @click="app.showSubPage('warnings')">
          <i class="fa fa-fw fa-exclamation-circle"></i> View Parser Warnings
        </b-dropdown-item>
        <b-dropdown-item
            v-if="app.sheetsAvailable &&
                  app.sodarContext.irods_status"
            class="sodar-ss-op-item"
            :href="'cache/update/' + app.projectUuid">
          <i class="fa fa-fw fa-refresh"></i> Update Sheet Cache
        </b-dropdown-item>
        <b-dropdown-item
            v-if="app.sheetsAvailable"
            class="sodar-ss-op-item"
            :href="'import/' + app.projectUuid">
          <i class="fa fa-fw fa-upload"></i> Replace ISAtab
        </b-dropdown-item>
        <b-dropdown-item
            v-if="app.sheetsAvailable && !app.windowsOs"
            class="sodar-ss-op-item"
            :href="'export/isa/' + app.projectUuid">
          <i class="fa fa-fw fa-download"></i> Export ISAtab
        </b-dropdown-item>
        <b-dropdown-item
            v-if="app.sheetsAvailable && app.windowsOs"
            class="sodar-ss-op-item"
            @click="app.$refs.winExportModal.showModal()">
          <i class="fa fa-fw fa-download"></i> Export ISAtab
        </b-dropdown-item>
        <b-dropdown-item
            v-if="app.sheetsAvailable &&
                  !app.renderError"
            class="sodar-ss-op-item"
            :href="'collections/' + app.projectUuid">
          <i class="fa fa-fw fa-database"></i>
          <span v-if="app.sodarContext.irods_status">Update</span><span v-else>Create</span> iRODS Collections
        </b-dropdown-item>
        <b-dropdown-item
            v-if="app.sheetsAvailable"
            class="sodar-ss-op-item"
            :href="'versions/' + app.projectUuid">
          <i class="fa fa-fw fa-files-o"></i> Sheet Versions
        </b-dropdown-item>
        <b-dropdown-item
            v-if="app.sheetsAvailable &&
                  app.sodarContext.perms.delete_sheet"
            class="sodar-ss-op-item"
            variant="danger"
            :href="'delete/' + app.projectUuid">
          <i class="fa fa-fw fa-close"></i> Delete Sheets and Data
        </b-dropdown-item>
      </b-dropdown>
      <!-- Finish editing button (replace op dropdown in edit mode) -->
      <b-button
          v-if="app.editMode"
          variant="primary"
          class="text-left"
          id="sodar-ss-vue-btn-edit-finish"
          :disabled="app.unsavedRow !== null"
          @click="toggleEditMode">
        Finish Editing <span class="pull-right"><i class="fa fa-check"></i></span>
      </b-button>
    </div>
  </div>
</template>

<script>
import NotifyBadge from './NotifyBadge.vue'

export default {
  name: 'PageHeader',
  components: {
    NotifyBadge
  },
  props: [
    'app'
  ],
  data () {
    return {
      notifyVisible: false,
      notifyMessage: null,
      notifyClasses: 'badge badge-pill sodar-ss-vue-nofify mx-2',
      editMode: false,
      editMessage: null,
      editVariant: 'info'
    }
  },
  methods: {
    onWindowsExportClick (event) {
      console.log('Clicked on windows!')
    },
    getStudyNavTitle (studyName) {
      if (studyName.length > 20) {
        return studyName
      } else {
        return null
      }
    },
    showNotification (message, variant, delay) {
      this.notifyClasses = 'badge badge-pill sodar-ss-vue-nofify mx-2 badge-'

      if (variant) {
        this.notifyClasses += variant
      } else {
        this.notifyClasses += 'light'
      }

      this.notifyMessage = message
      this.notifyVisible = true

      setTimeout(() => {
        this.notifyVisible = false
        this.notifyMessage = null
      }, delay || 2000)
    },
    toggleEditMode (editMode) {
      this.editMode = !this.editMode
      this.app.toggleEditMode()

      if (this.editMode) {
        this.editMessage = 'Edit Mode'
        this.editVariant = 'info'
      }
    },
    // TODO: Use this when saving values periodically in a queue
    setEditModeInfo (message, variant) {
      this.editMessage = message

      if (variant) {
        this.editVariant = variant
      }
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

button#sodar-ss-vue-btn-edit-finish {
  margin-left: 4px;
  width: 163px;
}

/* HACK because lol bootstrap */
a#sodar-ss-vue-link-edit-help i {
  vertical-align: middle;
  padding-bottom: 1px;
}

/* Hide navbar if browser is too narrow */
@media screen and (max-width: 1200px) {
  .sodar-ss-nav {
    display: none;
  }
}

</style>
