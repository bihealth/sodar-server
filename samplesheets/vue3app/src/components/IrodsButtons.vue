<script setup lang="ts">
import { BButton, useToast } from 'bootstrap-vue-next'
import { useClipboard } from '@vueuse/core'
import { TOAST_INTERVAL_DEFAULT } from '@/constants.ts'

const props = defineProps([
  'editMode',
  'enabled',
  'extraLinks',
  'irodsBackendEnabled',
  'irodsDirModalRef',
  'irodsWebdavUrl',
  'irodsPath',
  'irodsStatus',
  'showFileList'
])
const { create } = useToast()
const clipboard = useClipboard()

function getEnabledState (): boolean {
  return !props.editMode && props.irodsStatus && props.enabled !== false
}

// Copy path and display notification toast
function copyPath () {
  clipboard.copy(props.irodsPath)
  create({
    body: 'iRODS path copied into clipboard',
    variant: 'info',
    modelValue: TOAST_INTERVAL_DEFAULT
  })
}
</script>

<template>
  <span class="text-nowrap sodar-ss-irods-links">
    <BButton
        v-for="extraLink in extraLinks"
        :key="extraLink.id"
        variant="secondary"
        :class="'sodar-list-btn sodar-ss-irods-btn mr-1 ' + extraLink.class"
        :title="extraLink.title"
        :href="extraLink.url"
        :disabled="!(getEnabledState() && extraLink.enabled)">
    </BButton>
    <BButton
        v-if="showFileList && irodsBackendEnabled && irodsWebdavUrl"
        variant="secondary"
        class="sodar-list-btn sodar-ss-irods-btn sodar-ss-irods-list-btn mr-1"
        title="List files"
        @click="props.irodsDirModalRef.show(props.irodsPath)"
        :disabled="!getEnabledState()">
      <i class="iconify" data-icon="mdi:folder-open-outline"></i>
    </BButton>
    <BButton
        variant="secondary"
        class="sodar-list-btn sodar-ss-irods-btn sodar-ss-irods-copy-btn
               sodar-irods-copy-path-btn mr-1"
        title="Copy iRODS path into clipboard"
        @click="copyPath()"
        :disabled="!getEnabledState()">
      <i class="iconify" data-icon="mdi:console-line"></i>
    </BButton>
    <BButton
        variant="secondary"
        class="sodar-list-btn sodar-ss-irods-btn sodar-ss-irods-copy-btn
               sodar-irods-copy-dav-btn mr-1"
        title="Copy WebDAV URL into clipboard"
        @click="clipboard.copy(props.irodsWebdavUrl + props.irodsPath)"
        :disabled="!getEnabledState()">
      <i class="iconify" data-icon="mdi:clipboard-text-multiple"></i>
    </BButton>
    <BButton
        variant="secondary"
        class="sodar-list-btn sodar-ss-irods-btn sodar-irods-dav-btn"
        title="Browse Files in WebDAV"
        :href="irodsWebdavUrl + irodsPath"
        :disabled="!getEnabledState()">
      <i class="iconify" data-icon="mdi:open-in-new"></i>
    </BButton>
  </span>
</template>

<style scoped>
</style>
