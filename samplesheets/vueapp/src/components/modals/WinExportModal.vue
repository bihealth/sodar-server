<template>
  <b-modal
      id="sodar-vue-win-export-modal" ref="winExportModal"
      centered no-fade hide-footer
      size="m"
      title="Windows ISAtab Export Note">
    <div id="sodar-vue-irods-modal-content">
      <p>
        Please note that built-in zip archive handling in Windows may
        <strong>not</strong> unarchive all files in this export correctly.
      </p>
      <p>
        To ensure access to all files, please use third party software such as
        <a href="https://www.7-zip.org" target="_blank">7-Zip</a>
        to unarchive the export.
      </p>
      <b-button
          variant="primary"
          class="pull-right"
          @click="onExportClick">
        <i class="fa fa-fw fa-download"></i> Export ISAtab
      </b-button>
    </div>
  </b-modal>
</template>

<script>
export default {
  name: 'WinExportModal',
  props: [
    'app'
  ],
  methods: {
    onExportClick () {
      this.hideModal()
      window.location.href = 'export/isa/' + this.app.projectUuid
    },
    showModal () {
      this.$refs.winExportModal.show()
    },
    hideModal () {
      this.$refs.winExportModal.hide()
    }
  }
}
</script>

<style scoped>
</style>
