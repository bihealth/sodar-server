<script setup lang="ts">
import IrodsButtons from '@/components/IrodsButtons.vue'
import { type IrodsButtonsRendererParams } from '@/types.ts'

// External Data ---------------------------------------------------------------

defineProps({ params: Object })

// Helpers ---------------------------------------------------------------------

function getEnabledState (params: IrodsButtonsRendererParams) {
  if (!params.value) return true
  if (!params.value.path) return false // Disable buttons if path=null
  return params.value.enabled
}

function getIrodsPath (params: IrodsButtonsRendererParams) {
  if (params.value) return params.value.path
  return params.assayIrodsPath
}
</script>

<template>
  <IrodsButtons
      :edit-mode="false"
      :enabled="getEnabledState(params as IrodsButtonsRendererParams)"
      :irods-backend-enabled="params?.irodsBackendEnabled"
      :irods-dir-modal-ref="params?.modalRef"
      :irods-path="getIrodsPath(params as IrodsButtonsRendererParams)"
      :irods-status="params?.irodsStatus"
      :irods-webdav-url="params?.irodsWebdavUrl"
      :notify-cb="params?.notifyCb"
      :show-file-list="true">
  </IrodsButtons>
</template>

<style scoped>
</style>
