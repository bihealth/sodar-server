<script setup lang="ts">
import { ref, watch } from 'vue'
import WaitSection from '@/components/WaitSection.vue'
import { useAppStore } from '@/stores/appstore.ts'

const appStore = useAppStore()

interface warningInput { message: string, category: string }
interface warningOutput { source: string, message: string, category: string }
const warnings = ref<Array<warningOutput>>([])
const message = ref<string>('')
const limitReached = ref<boolean>(false)

function buildWarnings (
    warnings: Array<warningInput>, source: string): Array<warningOutput> {
  const ret = []
  for (let i = 0; i < warnings.length; i++) {
    const warning = warnings[i]
    ret.push({
      source: source,
      message: warning!.message.split('\n').join('<br />'),
      category: warning!.category
    })
  }
  return ret
}

function handleWarningsResponse (
    response: {
      warnings: {
        investigation: Array<warningInput>,
        limit_reached: boolean,
        studies: { [key: string]: Array<warningInput> },
        assays: { [key: string]: Array<warningInput> }
      }
    }
) {
  if ('warnings' in response) {
    if ('limit_reached' in response.warnings) {
      limitReached.value = response.warnings.limit_reached
    }
    // Investigation
    if (response.warnings.investigation.length > 0) {
      warnings.value.push(
       ...buildWarnings(
          response.warnings.investigation,
          appStore.sodarContext!.inv_file_name as string
        )
      )
    }
    // Studies
    for (const studyFileName in response.warnings.studies) {
      warnings.value.push(
        ...buildWarnings(
          response.warnings.studies[studyFileName]!, studyFileName
        )
      )
    }
    // Assays
    for (const assayFileName in response.warnings.assays) {
      warnings.value.push(
        ...buildWarnings(
          response.warnings.assays[assayFileName]!, assayFileName
        )
      )
    }
  }
}

function getWarnings () {
  const url = '/samplesheets/ajax/warnings/' + appStore.projectUuid
  fetch(url, { credentials: 'same-origin' })
    .then(response => response.json())
    .then(response => {
      console.log('Warnings retrieved')
      handleWarningsResponse(response)
    }).catch(function (error) {
      message.value = 'Error fetching data: ' + error
  })
}

// Get parser warnings once sodarContext is retrieved
if (appStore.sodarContext) { getWarnings() } else {
  watch(() => appStore.sodarContext, (newContext) => {
    if (newContext !== null) { getWarnings() }
  })
}
</script>

<template>
  <div v-if="limitReached"
       id="sodar-ss-warnings-alert-limit"
       class="alert alert-warning">
    Warning limit reached when parsing the sample sheets. All warnings may not
    be visible.
  </div>
  <div v-if="warnings && warnings.length > 0"
       class="card"
       id="sodar-ss-warnings-card">
    <div class="card-header">
      <h4>Parser Warnings</h4>
    </div>
    <div class="card-body p-0">
      <table class="table sodar-card-table"
             id="sodar-ss-warnings-table">
        <thead>
          <tr>
            <th>Source</th>
            <th>Message</th>
            <th>Category</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(warning, index) in warnings"
              :key="index"
              class="sodar-ss-warnings-item">
            <td class="text-monospace">{{ warning.source }}</td>
            <td class="text-monospace">
              <span v-html="warning.message"></span>
            </td>
            <td class="text-monospace">{{ warning.category }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
  <div v-else-if="message"
       id="sodar-ss-warnings-message">
    {{ message }}
  </div>
  <WaitSection v-else></WaitSection>
</template>

<style scoped>
table#sodar-ss-warnings-table tbody tr td {
  word-break: break-word;
}
table#sodar-ss-warnings-table thead tr th:first-child,
table#sodar-ss-warnings-table tbody tr td:first-child {
  min-width: 200px;
  max-width: 350px;
}
table#sodar-ss-warnings-table thead tr th:last-child,
table#sodar-ss-warnings-table tbody tr td:last-child {
  word-break: normal;
}
@media (max-width: 1200px) {
  table#sodar-ss-warnings-table thead tr th:nth-child(3),
  table#sodar-ss-warnings-table tbody tr td:nth-child(3) {
    display: none;
  }
}
</style>
