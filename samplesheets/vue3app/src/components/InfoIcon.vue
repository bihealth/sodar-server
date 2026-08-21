<script setup lang="ts">
import { BLink, BTooltip } from 'bootstrap-vue-next'
defineProps(['body'])
</script>

<template>
  <BTooltip
      click
      placement="top"
      :body="body">
    <template #target>
      <BLink>
        <i class="iconify text-info" data-icon="mdi:information"></i>
      </BLink>
    </template>
  </BTooltip>
</template>

<style scoped>
</style>
