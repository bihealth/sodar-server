<template>
  <span v-if="assayShortcuts">
    <div class="card sodar-ss-vue-assay-shortcut-card">
      <div class="card-header">
        <h4>Assay Shortcuts</h4>
      </div>
      <div class="card-body px-3 py-4 sodar-ss-vue-assay-shortcut-body">
        <span v-for="(shortcut, idx) in assayShortcuts"
              :key="idx"
              class="rounded border bg-light text-nowrap mr-3
                     sodar-ss-vue-assay-shortcut">
          <span :class="getTextClasses(shortcut)">
            {{ shortcut.label }}
            <i v-if="sodarContext.perms.is_superuser && idx > 1"
               class="fa fa-puzzle-piece text-danger ml-1"
               title="Defined in assay plugin"
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
              :notify-callback="notifyCallback">
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
      let classes = 'mr-2 sodar-ss-vue-assay-shortcut-text'
      if (!shortcut.enabled) {
        classes = classes + ' text-muted'
      }
      return classes
    }
  }
}
</script>

<style scoped>
div.sodar-ss-vue-assay-shortcut-body {
  overflow-x: scroll;
}

span.sodar-ss-vue-assay-shortcut {
  border: 1px solid #ced4da;
  padding: 12px;
}

</style>
