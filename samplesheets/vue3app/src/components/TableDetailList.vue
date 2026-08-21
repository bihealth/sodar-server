<script setup lang="ts">
import TableDetailListRow from '@/components/TableDetailListRow.vue'

// External Data ---------------------------------------------------------------

const props = defineProps([
    'assayMode',
    'notifyCb',
    'tableUuid',
    'tableContext',
    'tableMetaFields',
    'tableSodarFields'
])

// Helpers ---------------------------------------------------------------------

function getMetaIconClass (): string {
  if (props.assayMode) return 'text-danger'
  return 'text-info'
}
</script>

<template>
  <div v-if="tableContext"
       class="sodar-ss-table-detail-container"
       :id="'sodar-ss-table-detail-container-' + tableUuid">
    <TableDetailListRow
        v-for="(val, idx) in tableMetaFields"
        :key="'meta' + idx"
        :legend="val[0]"
        :value="tableContext[val[1]]"
        icon="mdi:file"
        :icon-class="getMetaIconClass()"
        title="ISA-Tab metadata"
        row-class="sodar-ss-table-detail-row-meta">
    </TableDetailListRow>
    <TableDetailListRow
        v-for="(val, key) in tableContext.comments"
        :key="'comment-' + key"
        :legend="key"
        :value="val"
        icon="mdi:comment"
        icon-class="text-primary"
        title="ISA-Tab comment"
        row-class="sodar-ss-table-detail-row-comment">
    </TableDetailListRow>
    <TableDetailListRow
        v-for="(val, idx) in tableSodarFields"
        :key="'sodar' + idx"
        :legend="val[0]"
        :value="tableContext[val[1]]"
        icon="mdi:code-braces"
        icon-class="text-secondary"
        title="SODAR metadata"
        row-class="sodar-ss-table-detail-row-sodar">
    </TableDetailListRow>
    <TableDetailListRow
        legend="SODAR UUID"
        :value="tableUuid"
        icon="mdi:code-braces"
        icon-class="text-secondary"
        :copy-button="true"
        :notify-cb="props.notifyCb"
        title="SODAR metadata"
        row-class="sodar-ss-table-detail-row-sodar sodar-ss-table-detail-uuid">
    </TableDetailListRow>
  </div>
</template>

<style scoped>
</style>
