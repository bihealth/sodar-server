<script setup lang="ts">
import { type TemplateRef } from 'vue'
import IrodsButtons from '@/components/IrodsButtons.vue'
import type {AssayIrodsPath} from "@/types.ts"

interface IrodsButtonsRendererParams {
  assayIrodsPath: string,
  irodsBackendEnabled: boolean,
  irodsStatus: boolean,
  irodsWebdavUrl: string,
  modalRef: TemplateRef,
  value: AssayIrodsPath
}

defineProps({ params: Object })

function getIrodsPath (params: IrodsButtonsRendererParams) {
  if (params.value) return params.value.path
  return params.assayIrodsPath
}

function getEnabledState (params: IrodsButtonsRendererParams) {
  if (!params.value) return true
  if (!params.value.path) return false // Disable buttons if path=null
  return params.value.enabled
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
      :show-file-list="true">
  </IrodsButtons>
</template>

<style scoped>
</style>
