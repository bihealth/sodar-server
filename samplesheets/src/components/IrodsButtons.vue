<template>
  <span class="text-nowrap">
    <b-button
        v-if="showFileList &&
              irodsBackendEnabled &&
              irodsWebdavUrl"
        variant="secondary"
        class="sodar-list-btn sodar-ss-irods-btn sodar-vue-popup-list-btn"
        title="List files"
        :disabled="setDisabledState()"
        @click="onDirListClick"
        v-b-tooltip.hover>
      <i class="fa fa-folder-open-o"></i>
    </b-button>
    <b-button
        variant="secondary"
        class="sodar-list-btn sodar-ss-irods-btn sodar-ss-irods-copy-btn sodar-irods-copy-path-btn"
        title="Copy iRODS path into clipboard"
        v-clipboard="irodsPath"
        :disabled="setDisabledState()"
        v-b-tooltip.hover>
      <i class="fa fa-terminal"></i>
    </b-button>
    <b-button
        variant="secondary"
        class="sodar-list-btn sodar-ss-irods-btn sodar-ss-irods-copy-btn sodar-irods-copy-dav-btn"
        title="Copy WebDAV URL into clipboard"
        v-clipboard="irodsWebdavUrl + irodsPath"
        :disabled="setDisabledState()"
        v-b-tooltip.hover>
      <i class="fa fa-clipboard"></i>
    </b-button>
    <b-button
        variant="secondary"
        class="sodar-list-btn sodar-ss-irods-btn sodar-irods-copy-btn sodar-irods-dav-btn"
        title="Browse Files in WebDAV"
        :href="irodsWebdavUrl + irodsPath"
        :disabled="setDisabledState()"
        v-b-tooltip.hover>
      <i class="fa fa-external-link"></i>
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
    'modalComponent'
  ],
  methods: {
    setDisabledState () {
      if (!this.irodsStatus) {
        return true
      }
      return false
    },
    onDirListClick (event) {
      let modalTitle = 'Files in iRODS: ' + this.irodsPath.split('/').pop()
      this.modalComponent.setTitle(modalTitle)
      this.modalComponent.getDirList(this.irodsPath)
    }
  }
}
</script>

<style scoped>
</style>
