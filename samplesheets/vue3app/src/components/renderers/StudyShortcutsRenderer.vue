<script setup lang="ts">
import { BButton } from 'bootstrap-vue-next'

defineProps({ params: Object })

const btnClasses: string = 'sodar-list-btn sodar-ss-irods-btn mr-1'
</script>

<template>
  <span class="text-nowrap sodar-ss-study-shortcuts">
    <span v-for="(schemaItem, schemaId) in params?.schema"
          :key="schemaId">
      <BButton
          v-if="schemaItem.type === 'link'"
          variant="secondary"
          :class="btnClasses"
          :title="schemaItem.title"
          :disabled="!params?.value[schemaId].enabled"
          :href="params?.value[schemaId].url">
        <i class="iconify" :data-icon="schemaItem.icon"></i>
      </BButton>
      <!-- TODO: Pass args to modal -->
      <BButton
          v-else-if="schemaItem.type === 'modal'"
          variant="secondary"
          :class="btnClasses + ' sodar-ss-popup-list-btn'"
          :title="schemaItem.title"
          :disabled="!params?.value[schemaId].enabled"
          @click="params?.modalRef.show(params?.value)">
        <i class="iconify" :data-icon="schemaItem.icon"></i>
      </BButton>
    </span>
  </span>
</template>

<style scoped>
</style>
