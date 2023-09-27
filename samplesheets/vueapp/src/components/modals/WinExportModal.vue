<template>
  <b-modal
      id="sodar-ss-win-export-modal" ref="winExportModal"
      centered no-fade hide-footer
      size="m"
      title="Windows ISA-Tab Export Note"
      :static="true">
    <div id="sodar-ss-irods-modal-content">
      <p>
        Please note that built-in zip archive handling in Windows may
        <strong>not</strong> unarchive all files in this export correctly.
      </p>
      <p>
        To ensure access to all files, please use third party software such as
        <a href="https://apps.microsoft.com/store/detail/nanazip/9N8G7TSCL18R" target="_blank">NanaZip</a>
        to unarchive the export.
      </p>
      <b-button
          variant="primary"
          class="pull-right"
          id="sodar-ss-win-export-btn"
          @click="onExport">
        <i class="iconify" data-icon="mdi:download"></i> Export ISA-Tab
      </b-button>
    </div>
  </b-modal>
</template>

<script>
export default {
  name: 'WinExportModal',
  props: ['app'],
  methods: {
    onExport () {
      window.location.href = 'export/isa/' + this.app.projectUuid
      this.hideModal()
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
