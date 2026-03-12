<script setup lang="ts">
// Common modal header
defineProps(['modalRef', 'title'])
</script>

<template>
  <div class="d-flex w-100 align-top sodar-ss-modal-header">
    <h5 class="modal-title flex-grow-1">{{ title }}</h5>
      <slot name="extend"></slot>
    <button
        class="close modal-close"
        type="button"
        @click="modalRef.hide()">
      <i class="iconify" data-icon="mdi:close-thick" data-height="22"></i>
    </button>
  </div>
</template>

<style scoped>
h5 {
  width: 100%;
}
button.modal-close {
  height: 22px !important;
}
button.modal-close {
  line-height: 28px !important;
}
/* Fix forced outline on modal close buttons in Chrome */
button.modal-close:focus {
  outline: none !important;
}
</style>
