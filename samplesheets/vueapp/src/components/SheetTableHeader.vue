<template>
  <div class="row mb-4"
       :id="'sodar-ss-section-' + gridIdSuffix">
    <h4 :class="'font-weight-bold mb-0 ' + getTitleTextClass()">
      <i v-if="!params.assayMode" class="iconify" data-icon="mdi:folder-table"></i>
      <i v-else class="iconify" data-icon="mdi:table-large"></i>
      {{ gridName }}: {{ tableContext.display_name }}
      <span v-if="params.sodarContext.perms.is_superuser &&
                  tableContext.plugin"
            class="sodar-ss-table-plugin">
        <i :class="'iconify ml-1 ' + getTitleTextClass()"
           data-icon="mdi:puzzle"
           :title="tableContext.plugin"
           v-b-tooltip.hover>
        </i>
      </span>
      <span v-else-if="params.sodarContext.perms.edit_sheet &&
                       !tableContext.plugin &&
                       params.assayMode"
            class="sodar-ss-table-plugin">
        <i class="iconify text-muted ml-1"
           data-icon="mdi:puzzle-remove"
           title="No assay plugin found: displaying default iRODS links"
           v-b-tooltip.hover>
        </i>
      </span>
    </h4>
    <div :class="getRightDivClass()">
      <span v-if="!params.assayMode" class="mr-2">
        <!-- iRODS collection status / stats badge -->
        <span v-if="!params.editMode" class="badge-group text-nowrap">
          <span class="badge badge-pill badge-secondary">iRODS</span>
            <irods-stats-badge
                v-if="params.sodarContext.irods_status"
                ref="studyStatsBadge"
                :project-uuid="params.projectUuid"
                :irods-status="params.sodarContext.irods_status"
                :irods-path="tableContext.irods_path">
            </irods-stats-badge>
          <span v-if="!params.sodarContext.irods_status"
                class="badge badge-pill badge-danger">
            Not Created
          </span>
        </span>
        <!-- Configuration -->
        <span class="badge-group" id="sodar-ss-badge-sheet-config">
          <span class="badge badge-pill badge-secondary">Config</span>
          <span v-if="params.sodarContext.configuration"
                class="badge badge-pill badge-info">
            {{ params.sodarContext.configuration }}
          </span>
          <span v-else class="badge badge-pill badge-danger">
            Unknown
          </span>
        </span>
      </span>
      <irods-buttons
          :irods-status="params.sodarContext.irods_status"
          :irods-backend-enabled="params.sodarContext.irods_backend_enabled"
          :irods-webdav-url="params.sodarContext.irods_webdav_url"
          :irods-path="tableContext.irods_path"
          :show-file-list="false"
          :edit-mode="params.editMode"
          :notify-callback="params.showNotificationCb">
      </irods-buttons>
    </div>
  </div>
</template>

<script>
import IrodsButtons from '@/components/IrodsButtons.vue'
import IrodsStatsBadge from '@/components/IrodsStatsBadge.vue'

export default {
  name: 'SheetTableHeader',
  components: {
    IrodsButtons,
    IrodsStatsBadge
  },
  props: ['params'],
  data () {
    return {
      gridName: null,
      gridIdSuffix: null,
      tableContext: null
    }
  },
  methods: {
    getTitleTextClass () {
      if (!this.params.assayMode) return 'text-info'
      return 'text-danger'
    },
    getRightDivClass () {
      // TODO: Is align-middle actually needed??
      let cls = 'ml-auto'
      if (this.params.assayMode) cls += ' align-middle'
      return cls
    }
  },
  beforeMount () {
    if (!this.params.assayMode) {
      this.gridIdSuffix = 'study'
      this.gridName = 'Study'
      this.tableContext = this.params.sodarContext.studies[this.params.gridUuid]
    } else {
      this.gridIdSuffix = 'assay-' + this.params.gridUuid
      this.gridName = 'Assay'
      this.tableContext = this.params.sodarContext.studies[
        this.params.studyUuid].assays[this.params.gridUuid]
    }
  },
  mounted () {
    // Update study badge stats
    if (!this.params.assayMode &&
        this.params.sodarContext.irods_status &&
        this.$refs.studyStatsBadge) {
      this.$refs.studyStatsBadge.updateStats() // TODO: Set up timer
    }
  }
}
</script>

<style scoped>
</style>
