<template>
  <span v-if="irodsStatus"
        class="badge badge-pill badge-info sodar-ss-irods-stats">
    <span v-if="fileCount !== null">
      {{ fileCount }} file<span v-if="fileCount !== 1">s</span>
      ({{ totalSize | prettyBytes }})
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
      totalSize: null
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

      fetch(statsUrl, {
        credentials: 'same-origin'
      })
        .then(response => response.json())
        .then(response => { this.setStats(response) })
        .catch(function (error) {
          console.log('irodsStatsBadge error: ' + error.message)
        })
    }
  }
}
</script>

<style scoped>
</style>
