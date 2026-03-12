<script setup lang="ts">
import IrodsButtons from '@/components/IrodsButtons.vue'
import { type AssayShortcut } from '@/types.ts'
import { useAppStore } from '@/stores/appStore.ts'
import { useTableStore } from '@/stores/tableStore.ts'

const appStore = useAppStore()
const tableStore = useTableStore()

defineProps(['assayUuid', 'modalRef'])

// TODO: Add extra link support (see #2403)

function getTextClass (shortcut: AssayShortcut): string {
  let ret = 'mr-2 sodar-ss-assay-shortcut-text'
  if (shortcut.enabled === false) ret += ' text-muted'
  return ret
}
</script>

<template>
  <div v-if="appStore.getPerm('view_files')"
       class="card sodar-ss-assay-shortcut-card">
    <div class="card-header">
      <h4>Assay Shortcuts</h4>
    </div>
    <div class="card-body px-3 py-4 sodar-ss-assay-shortcut-body">
      <span v-for="(shortcut, index) in tableStore.assayShortcuts[assayUuid]"
              :key="index"
              class="rounded border bg-light text-nowrap mr-3
                     sodar-ss-assay-shortcut">
        <span :class="getTextClass(shortcut)">
          {{ shortcut.label }}
          <i v-if="shortcut.id.startsWith('track_hub')"
             class="iconify text-info ml-1 sodar-ss-assay-shortcut-icon
                    sodar-ss-assay-shortcut-icon-hub"
             :data-icon="shortcut.icon"
             :title="shortcut.title">
          </i>
          <i v-else-if="appStore.getPerm('is_superuser') &&
                        shortcut.assay_plugin"
             class="iconify text-danger ml-1 sodar-ss-assay-shortcut-icon
                    sodar-ss-assay-shortcut-icon-plugin"
             :data-icon="shortcut.icon"
             :title="shortcut.title">
          </i>
        </span>
        <IrodsButtons
            :edit-mode="false"
            :enabled="shortcut.enabled"
            :irods-backend-enabled="appStore.sodarContext![
              'irods_backend_enabled']"
            :irods-dir-modal-ref="modalRef"
            :irods-path="shortcut.path"
            :irods-status="appStore.sodarContext!.irods_status"
            :irods-webdav-url="appStore.sodarContext!.irods_webdav_url"
            :show-file-list="true">
        </IrodsButtons>
      </span>
    </div>
  </div>
</template>

<style scoped>
.sodar-ss-assay-shortcut {
  border: 1px solid #ced4da;
  padding: 12px 12px 14px;
}
.sodar-ss-assay-shortcut-body {
  white-space: nowrap;
  overflow-x: scroll;
}
.sodar-ss-assay-shortcut-text {
  vertical-align: middle;
}
</style>
