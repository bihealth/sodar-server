<template>
  <b-modal
      id="sodar-ss-sams-modal"
      ref="samsModal"
      size="xl"
      centered no-fade hide-footer
      :static="true"
      title="SAMS iFrame Test">
    <div id="sodar-ss-saml-modal-content" class="mb-4">
      <p>
        <iframe
          src="https://www.genecascade.org/sams-cgi/enter_phenotype.cgi?onthefly=1"
          style="width: 100%; border: none; margin: auto padding: 0;
                 overflow: hidden; z-index: 999999; height: 600px;
                 transparency: 0%; background-color: white" />
      </p>
    </div>
  </b-modal>
</template>

<script>
export default {
  name: 'SamsModal',
  methods: {
    showModal () {
      // Show element
      this.$refs.samsModal.show()
    },
    hideModal () {
      this.$refs.samsModal.hide()
    }
  }
}
</script>

<style scoped>
</style>
