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
      </dd>
      <dd v-else
          class="col-md-9 sodar-ss-table-detail-value
                 sodar-ss-table-detail-value-empty text-muted">
        N/A
      </dd>
    </dl>
</template>

<script>
export default {
  name: 'TableDetailListRow',
  props: [
    'legend',
    'value',
    'icon',
    'iconClass',
    'title',
    'rowClass'
  ]
}
</script>

<style scoped>
.sodar-ss-table-detail-legend-content {
  margin-left: 20px;
  text-indent: -20px;
}
dd {
  word-break: break-word;
}
</style>
