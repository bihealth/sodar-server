<template>
  <span v-if="assayShortcuts">
    <div class="card sodar-ss-assay-shortcut-card">
      <div class="card-header">
        <h4>Assay Shortcuts</h4>
      </div>
      <div class="card-body px-3 py-4 sodar-ss-assay-shortcut-body">
        <span v-for="(shortcut, idx) of assayShortcuts"
              :key="idx"
              class="rounded border bg-light text-nowrap mr-3
                     sodar-ss-assay-shortcut">
          <span :class="getTextClasses(shortcut)">
            {{ shortcut.label }}
            <i v-if="shortcut.id.startsWith('track_hub')"
               class="iconify text-info ml-1"
               :data-icon="shortcut.icon"
               :title="shortcut.title"
               v-b-tooltip.hover.window>
            </i>
            <i v-else-if="sodarContext.perms.is_superuser && shortcut.assay_plugin"
               class="iconify text-danger ml-1"
               :data-icon="shortcut.icon"
               :title="shortcut.title"
               v-b-tooltip.hover.window>
            </i>
          </span>
          <irods-buttons
              :irods-backend-enabled="sodarContext.irods_backend_enabled"
              :irods-status="sodarContext.irods_status"
              :irods-webdav-url="sodarContext.irods_webdav_url"
              :irods-path="shortcut.path"
              :show-file-list="true"
              :modal-component="modalComponent"
              :enabled="shortcut.enabled"
              :notify-callback="notifyCallback"
              :extra-links="shortcut.extra_links">
            </irods-buttons>
        </span>
      </div>
    </div>
  </span>
</template>

<script>
import IrodsButtons from './IrodsButtons.vue'

export default {
  name: 'AssayShortcutCard',
  components: {
    IrodsButtons
  },
  props: [
    'sodarContext',
    'assayShortcuts',
    'modalComponent',
    'notifyCallback'
  ],
  methods: {
    getTextClasses (shortcut) {
      let classes = 'mr-2 sodar-ss-assay-shortcut-text'
      if (!shortcut.enabled) {
        classes = classes + ' text-muted'
      }
      return classes
    }
  }
}
</script>

<style scoped>
div.sodar-ss-assay-shortcut-body {
  white-space: nowrap;
  overflow-x: scroll;
}

span.sodar-ss-assay-shortcut {
  border: 1px solid #ced4da;
  padding: 12px;
}

</style>
