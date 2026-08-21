<script setup lang="ts">
import { useAppStore } from '@/stores/appStore.ts'
const appStore = useAppStore()
</script>

<template>
  <div v-if="appStore.sodarContext &&
             appStore.getPerm('edit_sheet') &&
             appStore.sodarContext.alerts.length"
       class="pb-2"
       id="sodar-ss-alert-container">
    <div v-for="(alertData, alertIdx) in appStore.sodarContext.alerts"
         :key="alertIdx"
         :class="'alert sodar-ss-server-alert alert-' + alertData.level">
      <i class="iconify" data-icon="mdi:alert"></i>
      <span class="ml-1" v-html="alertData.html"></span>
    </div>
  </div>
</template>

<style scoped>
</style>
