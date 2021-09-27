<template>
  <b-modal
      id="sodar-ss-version-modal"
      ref="versionSaveModal"
      size="md"
      centered no-fade hide-footer
      :static="true"
      title="Save Sheet Version">
    <div id="sodar-ss-version-modal-content" class="mb-4">
      <p>
        Save the current sheet version as backup. You can add an
        optional description to be deplayed in the version list.
      </p>
      <b-form-textarea
          no-resize
          placeholder="Description (max. 128 characters)"
          rows="3"
          v-model="description"
          :state="description.length <= 128">
      </b-form-textarea>
    </div>
    <div>
      <b-button-group
          class="pull-right"
          id="sodar-ss-version-btn-group">
        <b-button
            variant="secondary"
            id="sodar-ss-btn-cancel"
            @click="hideModal(false)">
          <i class="iconify" data-icon="mdi:close-thick"></i> Cancel
        </b-button>
        <b-button
            variant="primary"
            id="sodar-ss-btn-save"
            @click="hideModal(true)"
            ref="updateBtn">
          <i class="iconify" data-icon="mdi:check-bold"></i> Save
        </b-button>
      </b-button-group>
    </div>
  </b-modal>
</template>

<script>
export default {
  name: 'VersionSaveModal',
  props: ['app'],
  data () {
    return {
      description: ''
    }
  },
  methods: {
    onDescriptionUpdate () {

    },
    postSave () {
      fetch('/samplesheets/ajax/version/save/' + this.app.projectUuid, {
        method: 'POST',
        body: JSON.stringify({ save: true, description: this.description }),
        credentials: 'same-origin',
        headers: {
          Accept: 'application/json',
          'Content-Type': 'application/json',
          'X-CSRFToken': this.app.sodarContext.csrf_token
        }
      }).then(data => data.json())
        .then(data => {
          if (data.detail === 'ok') {
            this.app.setVersionSaved(true)
            this.app.showNotification('Version Saved', 'success', 1000)
          }
        }).catch(function (error) {
          console.error('Error saving version: ' + error.detail)
        })
    },
    showModal () {
      // Show element
      this.$refs.versionSaveModal.show()
    },
    hideModal (save) {
      this.postSave()
      this.$refs.versionSaveModal.hide()
    }
  }
}
</script>

<style scoped>
</style>
