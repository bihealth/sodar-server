<template>
  <irods-buttons
      :irods-status="params.irodsStatus"
      :irods-backend-enabled="params.irodsBackendEnabled"
      :irods-webdav-url="params.irodsWebdavUrl"
      :irods-path="getIrodsPath(params)"
      :show-file-list="params.showFileList"
      :modal-component="params.modalComponent">
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
          return params.value
        } else {
          return params.assayIrodsPath
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
