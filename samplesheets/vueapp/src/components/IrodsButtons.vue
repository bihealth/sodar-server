<template>
  <span class="text-nowrap sodar-ss-irods-links">
    <b-button
        v-for="extraLink in extraLinks"
        :key="extraLink.id"
        variant="secondary"
        :class="'sodar-list-btn sodar-ss-irods-btn ' + extraLink.class"
        :title="extraLink.title"
        :href="extraLink.url"
        :disabled="!(getEnabledState() && extraLink.enabled)"
        v-b-tooltip.hover.d300.window>
      <i :class="'fa ' + extraLink.icon"></i>
    </b-button>
    <b-button
        v-if="showFileList &&
              irodsBackendEnabled &&
              irodsWebdavUrl"
        variant="secondary"
        class="sodar-list-btn sodar-ss-irods-btn sodar-ss-popup-list-btn"
        title="List files"
        :disabled="!getEnabledState()"
        @click="onDirListClick"
        v-b-tooltip.hover.d300.window>
      <i class="iconify" data-icon="mdi:folder-open-outline"></i>
    </b-button>
    <b-button
        variant="secondary"
        class="sodar-list-btn sodar-ss-irods-btn sodar-ss-irods-copy-btn
               sodar-irods-copy-path-btn"
        title="Copy iRODS path into clipboard"
        v-clipboard="irodsPath"
        @click="onCopyBtnClick"
        :disabled="!getEnabledState()"
        v-b-tooltip.hover.d300.window>
      <i class="iconify" data-icon="mdi:console-line"></i>
    </b-button>
    <b-button
        variant="secondary"
        class="sodar-list-btn sodar-ss-irods-btn sodar-ss-irods-copy-btn
               sodar-irods-copy-dav-btn"
        title="Copy WebDAV URL into clipboard"
        v-clipboard:copy="irodsWebdavUrl + irodsPath"
        v-clipboard:success="onCopyBtnClick"
        :disabled="!getEnabledState()"
        v-b-tooltip.hover.d300.window>
      <i class="iconify" data-icon="mdi:clipboard-text-multiple"></i>
    </b-button>
    <b-button
        variant="secondary"
        class="sodar-list-btn sodar-ss-irods-btn sodar-irods-copy-btn
               sodar-irods-dav-btn"
        title="Browse Files in WebDAV"
        :href="irodsWebdavUrl + irodsPath"
        :disabled="!getEnabledState()"
        v-b-tooltip.hover.d300.window>
      <i class="iconify" data-icon="mdi:open-in-new"></i>
    </b-button>
  </span>
</template>

<script>

export default {
  name: 'IrodsButtons',
  props: [
    'irodsBackendEnabled',
    'irodsStatus',
    'irodsWebdavUrl',
    'irodsPath',
    'showFileList',
    'modalComponent',
    'enabled',
    'editMode',
    'notifyCallback',
    'extraLinks'
  ],
  methods: {
    getEnabledState () {
      return !this.editMode && this.irodsStatus && this.enabled !== false
    },
    onDirListClick (event) {
      const modalTitle = 'Files in iRODS: ' + this.irodsPath.split('/').pop()
      this.modalComponent.setTitle(modalTitle)
      this.modalComponent.showModal(this.irodsPath)
    },
    onCopyBtnClick (event) {
      this.notifyCallback('Copied', 'success', 1000)
    }
  }
}
</script>

<style scoped>
.sodar-list-btn {
  margin-left: 4px;
}

</style>
