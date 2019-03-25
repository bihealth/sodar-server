<template>
  <div class="row sodar-subtitle-container bg-white sticky-top">
    <h3><i class="fa fa-flask"></i> Sample Sheets</h3>
    <b-nav v-if="app.sheetsAvailable"
           pills
           class="sodar-ss-nav ml-4 mr-auto">
      <b-nav-item v-for="(studyInfo, studyUuid, index) in app.sodarContext['studies']"
                  :key="index"
                  @mousedown="app.handleStudyNavigation(studyUuid)"
                  v-b-tooltip.hover
                  :title="getStudyNavTitle(studyInfo['display_name'])"
                  :active="studyUuid === app.currentStudyUuid && !app.overviewActive"
                  :disabled="!app.sheetsAvailable || app.gridsBusy">
        <i class="fa fa-list-alt"></i> {{ studyInfo['display_name'] | truncate(20) }}
      </b-nav-item>
      <b-nav-item @mousedown="app.showOverview()"
                  :active="app.overviewActive"
                  :disabled="!app.sheetsAvailable || app.gridsBusy">
        <i class="fa fa-sitemap"></i> Overview
      </b-nav-item>
    </b-nav>
    <div class="ml-auto">
      <b-dropdown
          id="sodar-ss-nav-dropdown"
          :disabled="!app.sheetsAvailable || app.gridsBusy"
          right
          variant="success">
        <template slot="button-content">
          <i class="fa fa-navicon"></i>
        </template>
        <span v-for="(studyInfo, studyUuid, index) in app.sodarContext['studies']"
              :key="index">
          <b-dropdown-item
              href="#"
              class="sodar-ss-nav-item"
              @click="app.handleStudyNavigation(studyUuid)">
            <i class="fa fa-fw fa-list-alt text-info"></i> {{ studyInfo['display_name'] }}
          </b-dropdown-item>
          <b-dropdown-item
              v-for="(assayInfo, assayUuid, assayIndex) in studyInfo['assays']"
              :key="assayIndex"
              href="#"
              class="sodar-ss-nav-item"
              @click="app.handleStudyNavigation(studyUuid, assayUuid)">
            <i class="fa fa-fw fa-table text-danger ml-4"></i> {{ assayInfo['display_name'] }}
          </b-dropdown-item>
        </span>
        <b-dropdown-item
          href="#"
          class="sodar-ss-nav-item"
          @click="app.showOverview()">
          <i class="fa fa-fw fa-sitemap"></i> Overview
        </b-dropdown-item>
      </b-dropdown>
      <!-- TODO: Perm checks -->
      <b-dropdown
          id="sodar-ss-buttons-op"
          :disabled="app.gridsBusy"
          right
          variant="primary"
          text="Sheet Operations">
        <b-dropdown-item
            v-if="!app.sheetsAvailable &&
                  app.sodarContext['perms']['edit_sheet']"
            :href="'import/' + app.projectUuid">
          <i class="fa fa-fw fa-upload"></i> Import ISAtab
        </b-dropdown-item>
        <b-dropdown-item
            v-if="app.sheetsAvailable &&
                  app.sodarContext['perms']['edit_sheet']"
            :href="'import/' + app.projectUuid">
          <i class="fa fa-fw fa-refresh"></i> Replace ISAtab
        </b-dropdown-item>
        <b-dropdown-item
            v-if="app.sheetsAvailable &&
                  !app.renderError &&
                  app.sodarContext['perms']['create_dirs']"
            :href="'dirs/' + app.projectUuid">
          <i class="fa fa-fw fa-database"></i>
          <span v-if="app.sodarContext['irods_status']">Update</span><span v-else>Create</span> iRODS Directories
        </b-dropdown-item>
        <b-dropdown-item
            v-if="app.sheetsAvailable &&
                  app.sodarContext['perms']['delete_sheet']"
            :href="'delete/' + app.projectUuid">
          <i class="fa fa-fw fa-close"></i> Delete Sheets and Data
        </b-dropdown-item>
      </b-dropdown>
    </div>
  </div>
</template>

<script>
export default {
  name: 'PageHeader',
  props: [
    'app'
  ],
  methods: {
    getStudyNavTitle (studyName) {
      if (studyName.length > 20) {
        return studyName
      } else {
        return null
      }
    }
  }
}
</script>

<style scoped>

/* Force bg-success to active nav link (not supported by boostrap-vue) */
ul.sodar-ss-nav li a.active {
  background-color: #28a745 !important;
}

/* Hide navbar if browser is too narrow */
@media screen and (max-width: 1200px) {
  .sodar-ss-nav {
    display: none;
  }
}

</style>
