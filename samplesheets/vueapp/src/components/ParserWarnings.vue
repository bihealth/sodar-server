<template>
  <span>
    <div v-if="warnings && warnings.length > 0"
         class="card" id="sodar-ss-warnings-card">
      <div class="card-header">
        <h4>Parser Warnings</h4>
      </div>
      <div class="card-body p-0">
        <table class="table sodar-card-table" id="sodar-ss-warnings-table">
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
              <td class="text-monospace">{{ warning.message }}</td>
              <td class="text-monospace">{{ warning.category }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    <div v-else-if="message" id="sodar-ss-warnings-message">
      {{ message }}
    </div>
    <div v-else>
    </div>
  </span>
</template>

<script>
export default {
  name: 'ParserWarnings',
  props: [
    'projectUuid',
    'sodarContext'
  ],
  data () {
    return {
      warnings: null,
      message: null
    }
  },
  methods: {
    buildWarnings (warnings, source) {
      const ret = []
      for (let i = 0; i < warnings.length; i++) {
        const warning = warnings[i]
        ret.push({
          source: source,
          message: warning.message,
          category: warning.category
        })
      }
      return ret
    },
    handleWarningsResponse (response) {
      if ('warnings' in response) {
        if (response.warnings.investigation.length > 0) {
          this.warnings.push.apply(
            this.warnings,
            this.buildWarnings(
              response.warnings.investigation,
              this.sodarContext.inv_file_name
            )
          )
        }
        for (const studyFileName in response.warnings.studies) {
          this.warnings.push.apply(
            this.warnings,
            this.buildWarnings(
              response.warnings.studies[studyFileName], studyFileName
            )
          )
        }
        for (const assayFileName in response.warnings.assays) {
          this.warnings.push.apply(
            this.warnings,
            this.buildWarnings(
              response.warnings.assays[assayFileName],
              assayFileName
            )
          )
        }
      } else if ('message' in response) {
        this.message = response.message
      }
    },
    getWarnings () {
      this.warnings = []
      const apiUrl = '/samplesheets/ajax/warnings/' + this.projectUuid
      fetch(apiUrl, {
        credentials: 'same-origin'
      })
        .then(response => response.json())
        .then(
          response => {
            this.handleWarningsResponse(response)
          }).catch(function (error) {
          this.message = 'Error fetching data: ' + error.message
        })
    }
  },
  beforeMount () {
    // No warnings stated by the context -> don't bother fetching
    if (!this.sodarContext.parser_warnings) return

    // Fetch data
    this.getWarnings()
  }
}
</script>

<style scoped>

table#sodar-ss-warnings-table tbody tr td {
  word-break: break-word;
}

table#sodar-ss-warnings-table thead tr th:last-child,
table#sodar-ss-warnings-table tbody tr td:last-child {
  word-break: normal;
}

table#sodar-ss-warnings-table thead tr th:first-child,
table#sodar-ss-warnings-table tbody tr td:first-child {
  max-width: 350px;
}

@media (max-width: 1200px) {
  table#sodar-ss-warnings-table thead tr th:nth-child(3),
  table#sodar-ss-warnings-table tbody tr td:nth-child(3) {
    display: none;
  }
}

</style>
