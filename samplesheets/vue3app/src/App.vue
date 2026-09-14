<script setup lang="ts">
import { BApp } from 'bootstrap-vue-next'
import { RouterView, useRouter } from 'vue-router'

import ServerAlerts from './components/ServerAlerts.vue'
import ViewHeader from './components/ViewHeader.vue'
import { useAppStore } from '@/stores/appStore.ts'

import { getAjaxRequestInit } from '@/utils/appUtils.ts'
import { VIEW_STUDY } from '@/constants.ts'

const appStore = useAppStore()

// Get initial context from template
const initialContext = JSON.parse(
  document.getElementById(
    'sodar-ss-app-context')!.getAttribute('data-app-context') || '{}')
appStore.projectUuid = initialContext.project_uuid
appStore.currentStudyUuid = initialContext.initial_study

// Set up navigation
const router = useRouter()
const baseRe = /^\/samplesheets\/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}#\/$/
const loc = location.pathname + location.search + location.hash
// Update URL if entering with default
if (baseRe.test(loc)) {
  appStore.viewActive = VIEW_STUDY
  router.push({
    name: 'study',
    params: { studyUuid: appStore.currentStudyUuid },
    replace: true
  })
}

// Retrieve sodarContext
const getSodarContext = async () => {
  // TODO: Add error handling
  const response = await fetch(
    initialContext.context_url, getAjaxRequestInit())
  const jsonData = await response.json()
  appStore.sodarContext = JSON.parse(jsonData)
}
getSodarContext()
</script>

<template>
  <BApp>
    <ViewHeader></ViewHeader>
    <ServerAlerts></ServerAlerts>
    <RouterView></RouterView>
  </BApp>
</template>

<style scoped>
/*
NOTE: Importing BootstrapVueNext classes here to avoid breaking site CSS.
      Once SODAR Core and SODAR are upgraded to Bootstrap v5, these should be
      moved into main.ts
*/
@import 'bootstrap/dist/css/bootstrap.css';
@import 'bootstrap-vue-next/dist/bootstrap-vue-next.css';

div.card {
  border: 1px solid rgba(0, 0, 0, .125);
  border-radius: 0.25rem;
}
</style>
