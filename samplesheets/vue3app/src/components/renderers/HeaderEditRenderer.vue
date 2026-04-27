<script setup lang="ts">
import { BButton } from 'bootstrap-vue-next'

defineProps({ params: Object })
</script>

<template>
  <div class="ag-header-group-cell-label sodar-ss-header-edit">
    <span class="ag-header-group-text">
      {{ params?.displayName }}
    </span>
    <span class="ml-auto">
      <!-- TODO: Add button logic once editor is implemented -->
      <BButton
          variant="secondary"
          class="sodar-list-btn sodar-ss-col-config-btn"
          title="Configure Column"
          :disabled="true">
        <i class="iconify" data-icon="mdi:lead-pencil"></i>
      </BButton>
    </span>
  </div>
</template>

<style scoped>
</style>
