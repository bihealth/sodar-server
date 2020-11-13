<template>
  <b-modal
      id="sodar-vue-shortcut-modal"
      ref="shortcutModal"
      centered no-fade hide-footer
      size="md"
      :title="title"
      :static="true">
    <div v-if="modalData" id="sodar-vue-shortcut-modal-content">
      <table
          v-for="(cat, index) in modalData"
          :key="index"
          class="table sodar-card-table pb-3 sodar-ss-vue-shortcut-table">
        <thead>
          <tr>
            <th colspan="2">{{ cat.title }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(file, fileIdx) in cat.files"
              :key="fileIdx"
              class="sodar-ss-vue-shortcut-item">
            <td>
              <a :href="file.url"
                 target="_blank"
                 :title="file.title"
                 class="sodar-ss-vue-shortcut-link"
                 v-b-tooltip.hover>
                {{ file.label }}
              </a>
            </td>
            <td class="text-right text-nowrap">
              <b-button
                  v-for="(extraLink, extraIdx) in file.extra_links"
                  :key="extraIdx"
                  variant="secondary"
                  class="sodar-list-btn sodar-ss-irods-btn sodar-ss-vue-shortcut-extra ml-1"
                  :title="extraLink.label"
                  :href="extraLink.url"
                  v-b-tooltip.hover>
                <i :class="'fa fa-' + extraLink.icon"></i>
              </b-button>
            </td>
          </tr>
          <tr v-if="!cat.files.length">
            <td class="text-muted" colspan="2">N/A</td>
          </tr>
        </tbody>
      </table>
    </div>
    <!-- Message/error -->
    <div v-else-if="message"
         class="text-danger font-italic"
         id="sodar-ss-vue-shortcuts-message">
      {{ this.message }}
    </div>
    <!-- Waiting -->
    <div v-else
         class="text-center"
         id="sodar-ss-vue-shortcuts-wait">
      <i class="fa fa-spin fa-circle-o-notch fa-3x text-muted"></i>
    </div>
  </b-modal>
</template>

<script>
export default {
  name: 'StudyShortcutModal',
  props: [
    'irodsWebdavUrl',
    'projectUuid',
    'studyUuid'
  ],
  data () {
    return {
      title: null,
      modalData: null,
      message: null
    }
  },
  methods: {
    setTitle (title) {
      this.title = title
    },
    handleShortcutResponse (response) {
      if ('data' in response && 'title' in response) {
        this.title = response.title
        let filesFound = false
        for (const cat in response.data) {
          if (response.data[cat].files.length > 0) {
            filesFound = true
            break
          }
        }
        if (filesFound) this.modalData = response.data
        else this.message = 'No files found'
      } else if ('message' in response) {
        this.message = response.message
      }
    },
    getShortcuts (query) {
      const listUrl = '/samplesheets/ajax/study/links/' +
        this.studyUuid + '?' + query.key + '=' + query.value

      fetch(listUrl, { credentials: 'same-origin' })
        .then(response => response.json())
        .then(response => {
          this.handleShortcutResponse(response)
        }).catch(function (error) {
          this.message = 'Error fetching data: ' + error.message
        })
    },
    showModal (query) {
      const modalElement = this.$refs.shortcutModal

      // Clear previous data
      this.title = 'Loading..'
      this.message = null
      this.modalData = null

      this.getShortcuts(query)
      modalElement.show()
    }
  }
}
</script>

<style scoped>
</style>
