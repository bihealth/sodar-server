<script setup lang="ts">
import { useAppStore } from '@/stores/appstore.ts'
const appStore = useAppStore()
</script>

<template>
  <!-- TODO: Remove this once Vue3 app is finalized -->
  <div class="alert alert-warning"
       id="sodar-ss-version-alert">
    <i class="iconify" data-icon="mdi:alert-octagram"></i>
    This is the new Sample Sheets Vue3 app. Development is ongoing, some
    features may be missing or incomplete. Edit mode is currently disabled.
  </div>
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
