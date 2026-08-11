<script setup lang="ts">
import { BButton } from 'bootstrap-vue-next'
import { useClipboard } from '@vueuse/core'
import { COPY_MSG_SUFFIX, VARIANT_INFO } from '@/constants.ts'

const props = defineProps([
  'legend',
  'value',
  'icon',
  'iconClass',
  'notifyCb',
  'title',
  'rowClass',
  'copyButton'
])
const clipboard = useClipboard()

// Copy value to clipboard and display toast
function onCopy (legend: string, value: string) {
  clipboard.copy(value)
  if (props.notifyCb) props.notifyCb(legend + COPY_MSG_SUFFIX, VARIANT_INFO)
}
</script>

<template>
  <dl :class="'row pb-0 sodar-ss-table-detail-row ' + rowClass">
    <dt class="col-md-3 sodar-ss-table-detail-legend">
      <div class="sodar-ss-table-detail-legend-content">
        <i :class="'iconify ' + iconClass"
           :data-icon="icon"
           :title="title">
        </i>
        {{ legend }}
      </div>
    </dt>
    <dd v-if="!(['', null].includes(value))"
        class="col-md-9 sodar-ss-table-detail-value">
      {{ value }}
      <span v-if="copyButton"
            class="pull-right">
        <BButton
            variant="secondary"
            class="sodar-list-btn sodar-ss-clip-copy-btn"
            :title="'Copy ' + legend + ' into clipboard'"
            @click="onCopy(legend, value)">
          <i class="iconify" data-icon="mdi:clipboard-text-multiple"></i>
        </BButton>
      </span>
    </dd>
    <dd v-else
        class="col-md-9 sodar-ss-table-detail-value
              sodar-ss-table-detail-value-empty text-muted">
      N/A
    </dd>
  </dl>
</template>

<style scoped>
.sodar-ss-table-detail-legend-content {
  margin-left: 20px;
  text-indent: -20px;
}
dd {
  word-break: break-word;
}
</style>
