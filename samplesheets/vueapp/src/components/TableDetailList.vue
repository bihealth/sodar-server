<template>
  <div v-if="tableContext"
       id="sodar-ss-table-detail-container">
    <table-detail-list-row
        v-for="(val, idx) in tableMetaFields"
        :key="'meta' + idx"
        :legend="val[0]"
        :value="tableContext[val[1]]"
        icon="mdi:file"
        :icon-class="getMetaIconClass()"
        title="ISA-Tab metadata"
        row-class="sodar-ss-table-detail-row-meta">
    </table-detail-list-row>
    <table-detail-list-row
        v-for="(val, key, idx) in tableContext.comments"
        :key="'comment' + idx"
        :legend="key"
        :value="val"
        icon="mdi:comment"
        icon-class="text-primary"
        title="ISA-Tab comment"
        row-class="sodar-ss-table-detail-row-comment">
    </table-detail-list-row>
    <table-detail-list-row
        v-for="(val, idx) in tableSodarFields"
        :key="'sodar' + idx"
        :legend="val[0]"
        :value="tableContext[val[1]]"
        icon="mdi:code-braces"
        icon-class="text-secondary"
        title="SODAR metadata"
        row-class="sodar-ss-table-detail-row-sodar">
    </table-detail-list-row>
  </div>
</template>

<script>
import TableDetailListRow from './TableDetailListRow.vue'

export default {
  name: 'TableDetailList',
  components: { TableDetailListRow },
  props: [
    'assayMode',
    'tableContext',
    'tableMetaFields',
    'tableSodarFields' // NOTE: This has to be in incorrect case to work
  ],
  methods: {
    getMetaIconClass () {
      if (this.assayMode) return 'text-danger'
      return 'text-info'
    }
  }
}
</script>

<style scoped>
</style>
