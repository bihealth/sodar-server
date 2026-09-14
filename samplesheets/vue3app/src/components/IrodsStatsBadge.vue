<script setup lang="ts">
import { ref } from 'vue'
import prettyBytes from 'pretty-bytes'

import { getAjaxRequestInit } from '@/utils/appUtils.ts'
import { URL_IRODS_STATS_PREFIX } from '@/constants.ts'

// External Data ---------------------------------------------------------------

const props = defineProps(['irodsPath', 'irodsStatus', 'projectUuid'])

// Refs ------------------------------------------------------------------------

const fileCount = ref<number | null>(null)
const totalSize = ref<number | null>(null)
const badgeClass = ref<string>('badge-info')
const error = ref<boolean>(false)

// Helpers ---------------------------------------------------------------------

function setStats (stats: { file_count: number, total_size: number }) {
  fileCount.value = stats.file_count
  totalSize.value = stats.total_size
}

function updateStats () {
  const statsUrl = URL_IRODS_STATS_PREFIX +
    props.projectUuid + '?path=' + encodeURIComponent(props.irodsPath)
  fetch(statsUrl, getAjaxRequestInit())
    .then(response => response.json().then(
      data => ({
        status: response.status,
        statusText: response.statusText,
        body: data
      })))
    .then(obj => {
      if (obj.status === 200) setStats(obj.body)
      else {
        error.value = true
        badgeClass.value = 'badge-danger'
        console.error(
          'irodsStatsBadge query failed: ' + obj.statusText +
          ' (' + obj.status + ')')
          // TODO: Display error toast
      }
    })
    .catch(function (error) {
      console.error('irodsStatsBadge error: ' + error.message)
      // TODO: Display error toast
    })
}

// Setup -----------------------------------------------------------------------

if (props.irodsStatus) {
  updateStats()
} // TODO: Set periodic update
</script>

<template>
  <span v-if="irodsStatus"
        :class="'badge badge-pill sodar-ss-irods-stats ' + badgeClass">
    <span v-if="fileCount !== null && totalSize !== null">
      {{ fileCount }} file<span v-if="fileCount !== 1">s</span>
      ({{ prettyBytes(totalSize) }})
    </span>
    <span v-else-if="error">
      Error
    </span>
    <span v-else
          class="sodar-ss-irods-stats-loading">
      <i class="iconify spin" data-icon="mdi:loading"></i>
      Updating..
    </span>
  </span>
</template>

<style scoped>
</style>
