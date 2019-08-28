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
              <td class="text-nowrap text-monospace">{{ warning['source'] }}</td>
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
                  this.app.sodarContext['inv_file_name']
                )
              )
            }
            for (let studyFileName in response['warnings']['studies']) {
              this.warnings.push.apply(
                this.warnings,
                buildWarnings(
                  response['warnings']['studies'][studyFileName], studyFileName
                )
              )
            }
            for (let assayFileName in response['warnings']['assays']) {
              this.warnings.push.apply(
                this.warnings,
                buildWarnings(
                  response['warnings']['assays'][assayFileName],
                  assayFileName
                )
              )
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
