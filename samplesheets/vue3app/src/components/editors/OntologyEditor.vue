<script setup lang="ts">
// NOTE: Actual editing happens in OntologyEditModal

import { onMounted } from 'vue'
import { type SheetTableCellData } from '@/types.ts'

// Data and initial setup ------------------------------------------------------

const props = defineProps({ params: Object })
// console.dir(props.params)

const cellData = props.params?.value as SheetTableCellData

// API and lifecycle -----------------------------------------------------------

// Return value for ag-grid API
function getValue () {
  return cellData
}
defineExpose({ getValue })

onMounted(() => {
  props.params?.ontologyEditModal.show(props.params)
})
</script>

<template>
  <div class="sodar-ss-data-cell-busy text-muted text-center">
    <i class="iconify spin" data-icon="mdi:loading"></i>
  </div>
</template>

<style scoped>
</style>
