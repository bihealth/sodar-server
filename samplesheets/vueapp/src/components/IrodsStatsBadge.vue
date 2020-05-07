<template>
  <span v-if="irodsStatus"
        class="badge badge-pill badge-info sodar-vue-irods-stats">
    <span v-if="fileCount != null">
      {{ fileCount }} file<span v-if="fileCount !== 1">s</span>
      ({{ totalSize | prettyBytes }})
    </span>
    <span v-else>
      <i class="fa fa-spin fa-circle-o-notch"></i> Updating..
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
      dirStats: null,
      fileCount: null,
      totalSize: null,
      timer: null
    }
  },
  methods: {
    setStats (stats) {
      this.fileCount = stats.file_count
      this.totalSize = stats.total_size
    },
    updateStats () {
      // TODO: Fetch from SODAR project cache first, once implemented
      const statsUrl = '/irodsbackend/api/stats/' +
        this.projectUuid + '?path=' + encodeURIComponent(this.irodsPath)

      fetch(statsUrl, {
        credentials: 'same-origin'
      })
        .then(
          response => response.json())
        .then(response => {
          this.setStats(response)
        })
    }
  }
}
</script>

<style scoped>
</style>
