<template>
  <irods-buttons
      :irods-status="params.irodsStatus"
      :irods-backend-enabled="params.irodsBackendEnabled"
      :irods-webdav-url="params.irodsWebdavUrl"
      :irods-path="getIrodsPath(params)"
      :show-file-list="params.showFileList"
      :modal-component="params.modalComponent"
      :enabled="getEnabledState(params)"
      :edit-mode="params.app.editMode"
      :notify-callback="params.app.showNotification">
  </irods-buttons>
</template>

<script>
import Vue from 'vue'
import IrodsButtons from '../IrodsButtons.vue'

export default Vue.extend({
  components: {
    IrodsButtons
  },
  methods: {
    getIrodsPath (params) {
      if (params.value) return params.value.path
      return params.assayIrodsPath
    },
    getEnabledState (params) {
      if (!params.value) return true
      if (!params.value.path) return false // Disable buttons if path=null
      return params.value.enabled
    }
  }
})
</script>

<style scoped>
</style>
