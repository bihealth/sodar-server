<template>
  <span v-if="irodsStatus"
        :class="'badge badge-pill sodar-ss-irods-stats ' + badgeClass">
    <span v-if="fileCount !== null">
      {{ fileCount }} file<span v-if="fileCount !== 1">s</span>
      ({{ totalSize | prettyBytes }})
    </span>
    <span v-else-if="error">
      Error
    </span>
    <span v-else>
      <img src="/icons/mdi/loading.svg?color=%23fff&height=10" class="spin" /> Updating..
    </span>
  </span>
</template>

<script>
export default {
  name: 'IrodsStatsBadge',
  props: [
    'projectUuid',
    'irodsStatus',
    'irodsPath'
  ],
  data () {
    return {
      fileCount: null,
      totalSize: null,
      badgeClass: 'badge-info',
      error: false
    }
  },
  methods: {
    setStats (stats) {
      this.fileCount = stats.file_count
      this.totalSize = stats.total_size
    },
    updateStats () {
      // TODO: Fetch from SODAR project cache first, once implemented
      const statsUrl = '/irodsbackend/ajax/stats/' +
        this.projectUuid + '?path=' + encodeURIComponent(this.irodsPath)

      fetch(statsUrl, { credentials: 'same-origin' })
        .then(response => response.json().then(
          data => ({
            status: response.status,
            statusText: response.statusText,
            body: data
          })))
        .then(obj => {
          if (obj.status === 200) this.setStats(obj.body)
          else {
            this.error = true
            this.badgeClass = 'badge-danger'
            console.error(
              'irodsStatsBadge query failed: ' + obj.statusText +
              ' (' + obj.status + ')')
          }
        })
        .catch(function (error) {
          console.error('irodsStatsBadge error: ' + error.message)
        })
    }
  }
}
</script>

<style scoped>
</style>
