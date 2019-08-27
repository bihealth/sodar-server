<template>
  <dl class="row pb-0">
    <dt class="col-md-3">{{ legend }}</dt>
    <dd v-if="value" class="col-md-9">{{ value }}</dd>
    <dd v-else class="col-md-9 text-muted">N/A</dd>
  </dl>
</template>

<script>
export default {
  name: 'ListRow',
  props: [
    'legend',
    'value'
  ]
}
</script>

<style scoped>
</style>
