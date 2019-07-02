<template>
  <span>
    <div v-if="warnings && warnings.length > 0" class="card" id="sodar-ss-warnings-card">
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
            <tr v-for="(warning, index) in warnings" :key="index">
              <td class="text-nowrap">{{ warning['source'] }}</td>
              <td class="text-monospace">{{ warning['message'] }}</td>
              <td class="text-monospace">{{ warning['category'] }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    <div v-else-if="message">
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
    'app'
  ],
  data () {
    return {
      warnings: null,
      message: null
    }
  },
  beforeMount () {
    // No warnings stated by the context -> don't bother fetching
    if (this.app.sodarContext['parser_warnings'] === false) {
      return
    }

    // Helper function for building table data
    function buildWarnings (warnings, source) {
      let ret = []
      for (let i = 0; i < warnings.length; i++) {
        let warning = warnings[i]
        ret.push({
          source: source,
          message: warning['message'],
          category: warning['category']
        })
      }
      return ret
    }

    // Fetch data
    this.warnings = []
    let apiUrl = '/samplesheets/api/warnings/get/' +
      this.app.projectUuid

    fetch(apiUrl, {
      credentials: 'same-origin'
    })
      .then(response => response.json())
      .then(
        response => {
          if ('warnings' in response) {
            if (response['warnings']['investigation'].length > 0) {
              this.warnings.push.apply(
                this.warnings,
                buildWarnings(
                  response['warnings']['investigation'],
                  'Investigation'
                )
              )
            }
            for (let studyUuid in this.app.sodarContext['studies']) {
              if (response['warnings']['studies'].hasOwnProperty(studyUuid)) {
                this.warnings.push.apply(
                  this.warnings,
                  buildWarnings(
                    response['warnings']['studies'][studyUuid],
                    'Study: ' + this.app.sodarContext['studies'][studyUuid]['display_name']
                  )
                )
              }
              for (let assayUuid in this.app.sodarContext['studies'][studyUuid]['assays']) {
                if (response['warnings']['assays'].hasOwnProperty(assayUuid)) {
                  this.warnings.push.apply(
                    this.warnings,
                    buildWarnings(
                      response['warnings']['assays'][assayUuid],
                      'Assay: ' + this.app.sodarContext['studies'][studyUuid]['assays'][assayUuid]['display_name']
                    )
                  )
                }
              }
            }
          } else if ('message' in response) {
            this.message = response['message']
          }
        }).catch(function (error) {
        this.message = 'Error fetching data: ' + error.message
      })
  }
}
</script>

<style scoped>
</style>
