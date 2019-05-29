<template>
  <span class="text-nowrap sodar-ss-irods-links">
    <b-button
        v-if="showFileList &&
              irodsBackendEnabled &&
              irodsWebdavUrl"
        variant="secondary"
        class="sodar-list-btn sodar-ss-irods-btn sodar-vue-popup-list-btn"
        title="List files"
        :disabled="!getEnabledState()"
        @click="onDirListClick"
        v-b-tooltip.hover.d300>
      <i class="fa fa-folder-open-o"></i>
    </b-button>
    <b-button
        variant="secondary"
        class="sodar-list-btn sodar-ss-irods-btn sodar-ss-irods-copy-btn
               sodar-irods-copy-path-btn"
        title="Copy iRODS path into clipboard"
        v-clipboard="irodsPath"
        @click="onCopyBtnClick"
        :disabled="!getEnabledState()"
        v-b-tooltip.hover.d300>
      <i class="fa fa-terminal"></i>
    </b-button>
    <b-button
        variant="secondary"
        class="sodar-list-btn sodar-ss-irods-btn sodar-ss-irods-copy-btn
               sodar-irods-copy-dav-btn"
        title="Copy WebDAV URL into clipboard"
        v-clipboard="irodsWebdavUrl + irodsPath"
        @click="onCopyBtnClick"
        :disabled="!getEnabledState()"
        v-b-tooltip.hover.d300>
      <i class="fa fa-clipboard"></i>
    </b-button>
    <b-button
        variant="secondary"
        class="sodar-list-btn sodar-ss-irods-btn sodar-irods-copy-btn
               sodar-irods-dav-btn"
        title="Browse Files in WebDAV"
        :href="irodsWebdavUrl + irodsPath"
        :disabled="!getEnabledState()"
        v-b-tooltip.hover.d300>
      <i class="fa fa-external-link"></i>
    </b-button>
  </span>
</template>

<script>

export default {
  name: 'IrodsButtons',
  props: [
    'app',
    'irodsBackendEnabled',
    'irodsStatus',
    'irodsWebdavUrl',
    'irodsPath',
    'showFileList',
    'modalComponent',
    'enabled'
  ],
  methods: {
    getEnabledState () {
      if (!this.irodsStatus || this.enabled === false) {
        return false
      }
      return true
    },
    onDirListClick (event) {
      let modalTitle = 'Files in iRODS: ' + this.irodsPath.split('/').pop()
      this.modalComponent.setTitle(modalTitle)
      this.modalComponent.showModal(this.irodsPath)
    },
    onCopyBtnClick (event) {
      // HACK! this.app appears unset in some cases, not sure why? see #511
      if (this.app) {
        this.app.showNotification('Copied!', 'success', 1000)
      } else {
        this.$parent.showNotification('Copied!', 'success', 1000)
      }
    }
  }
}
</script>

<style scoped>
</style>
