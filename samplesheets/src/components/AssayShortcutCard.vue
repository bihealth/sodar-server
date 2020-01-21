<template>
  <span v-if="shortcutData">
    <div class="card sodar-ss-vue-assay-shortcut-card">
      <div class="card-header">
        <h4>Assay Shortcuts</h4>
      </div>
      <div class="card-body px-3 py-4 sodar-ss-vue-assay-shortcut-body">
        <span v-for="(shortcut, idx) in shortcutData"
             :key="idx"
             class="rounded border bg-light text-nowrap mr-3
                    sodar-ss-vue-assay-shortcut">
          <span :class="getTextClasses(shortcut)">
            {{ shortcut['label'] }}
            <i v-if="app.sodarContext['perms']['is_superuser'] && idx > 1"
                class="fa fa-puzzle-piece text-danger ml-1"
                title="Defined in assay plugin"
                v-b-tooltip.hover.window>
            </i>
          </span>
          <irods-buttons
              :app="app"
              :irods-status="app.sodarContext['irods_status']"
              :irods-backend-enabled="app.sodarContext['irods_backend_enabled']"
              :irods-webdav-url="app.sodarContext['irods_webdav_url']"
              :irods-path="shortcut['path']"
              :show-file-list="true"
              :modal-component="app.$refs.dirModalRef"
              :enabled="shortcut['enabled']">
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
    'app',
    'assayInfo',
    'shortcutData',
    'irodsBackendEnabled',
    'irodsWebdavUrl'
  ],
  methods: {
    getTextClasses (shortcut) {
      let classes = 'mr-2 sodar-ss-vue-assay-shortcut-text'
      if (!shortcut['enabled']) {
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
