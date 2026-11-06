<script setup lang="ts">

import { ref } from 'vue'

const props = defineProps(['colspan'])
const colSpan = ref<string>(props.colspan || '2')

</script>

<template>
  <tr>
    <td :colspan="colSpan"><hr class="my-1" /></td>
  </tr>
</template>

<style scoped>
</style>
