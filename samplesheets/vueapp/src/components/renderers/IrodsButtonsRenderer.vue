<template>
  <irods-buttons
      :app="params.app"
      :irods-status="params.irodsStatus"
      :irods-backend-enabled="params.irodsBackendEnabled"
      :irods-webdav-url="params.irodsWebdavUrl"
      :irods-path="getIrodsPath(params)"
      :show-file-list="params.showFileList"
      :modal-component="params.modalComponent"
      :enabled="getEnabledState(params)">
  </irods-buttons>
</template>

<script>
import Vue from 'vue'
import IrodsButtons from '../IrodsButtons.vue'

export default Vue.extend(
  {
    components: {
      IrodsButtons
    },
    methods: {
      getIrodsPath (params) {
        if (params.value) {
          return params.value.path
        } else {
          return params.assayIrodsPath
        }
      },
      getEnabledState (params) {
        if (params.value) {
          return params.value.enabled
        } else {
          return 1 // TODO: Store assay path file count somewhere instead?
        }
      }
    },
    beforeMount () {
    }
  }
)
</script>

<style scoped>

</style>
