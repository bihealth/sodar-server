<script setup lang="ts">
import { BButton } from 'bootstrap-vue-next'

import { useEditStore } from '@/stores/editStore.ts'

const props = defineProps({ params: Object })
const editStore = useEditStore()

function isEnabled (): boolean {
  return !(editStore.unsavedRow &&
    ['NAME', 'PROTOCOL', 'FILE_LINK'].includes(props.params?.colType))
}
</script>

<template>
  <div class="ag-header-group-cell-label sodar-ss-header-edit">
    <span class="ag-header-group-text">
      {{ params?.displayName }}
    </span>
    <span class="ml-auto">
      <BButton
          variant="secondary"
          class="sodar-list-btn sodar-ss-col-config-btn"
          title="Configure Column"
          :disabled="!isEnabled()"
          @click="params?.modalRef.show(params)">
        <i class="iconify" data-icon="mdi:lead-pencil"></i>
      </BButton>
    </span>
  </div>
</template>

<style scoped>
</style>
