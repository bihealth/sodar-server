<template>
  <div class="row mb-4 sodar-ss-table-header-row"
       :id="'sodar-ss-section-' + gridIdSuffix">
    <div :class="'col-' + leftColWidth + ' pl-0'">
      <h4 :class="'font-weight-bold mb-0 ' + getTitleTextClass()">
        <i v-if="!params.assayMode"
           class="iconify"
           data-icon="mdi:folder-table"></i>
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
    </div>
    <div :class="'col-' + rightColWidth + ' text-right pr-0'">
      <span v-if="!params.assayMode" class="mr-2 sodar-ss-study-title-badge">
        <!-- iRODS collection status / stats badge -->
        <span v-if="!params.assayMode && !params.editMode"
              class="badge-group text-nowrap">
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
      tableContext: null,
      leftColWidth: 8,
      rightColWidth: 4
    }
  },
  methods: {
    getTitleTextClass () {
      if (!this.params.assayMode) return 'text-info'
      return 'text-danger'
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
      this.leftColWidth = 10
      this.rightColWidth = 2
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
  h4 {
    margin-left: 30px;
    text-indent: -30px;
  }

  @media screen and (max-width: 1200px) {
    span.sodar-ss-study-title-badge {
      display: none;
    }
  }
</style>
