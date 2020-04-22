<template>
  <b-modal id="sodar-vue-shortcut-modal" ref="shortcutModal"
           centered no-fade hide-footer
           size="md"
           :title="title">
    <div v-if="modalData"
         id="sodar-vue-shortcut-modal-content">
      <table v-for="(cat, index) in modalData"
             :key="index"
             class="table sodar-card-table sodar-vue-shortcut-table pb-3">
        <thead>
          <tr>
            <th colspan="2">{{ cat['title']}}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(file, fileIdx) in cat['files']" :key="fileIdx">
            <td>
              <a :href="file['url']" target="_blank" :title="file['title']" v-b-tooltip.hover>
                {{ file['label'] }}
              </a>
            </td>
            <td class="text-right text-nowrap">
              <b-button
                  v-for="(extraLink, extraIdx) in file['extra_links']"
                  :key="extraIdx"
                  variant="secondary"
                  class="sodar-list-btn sodar-ss-irods-btn sodar-vue-shortcut-extra-btn ml-1"
                  :title="extraLink['label']"
                  :href="extraLink['url']"
                  v-b-tooltip.hover>
                <i :class="'fa fa-' + extraLink['icon']"></i>
              </b-button>
            </td>
          </tr>
          <tr v-if="!cat['files'].length">
            <td class="text-muted" colspan="2">N/A</td>
          </tr>
        </tbody>
      </table>
    </div>
    <!-- Message/error -->
    <div v-else-if="message" class="text-danger font-italic">
      {{ this.message }}
    </div>
    <!-- Waiting -->
    <div v-else class="text-center">
      <i class="fa fa-spin fa-circle-o-notch fa-3x text-muted"></i>
    </div>
  </b-modal>
</template>

<script>
export default {
  name: 'ShortcutModal',
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
    getLinks (query) {
      let modalElement = this.$refs.shortcutModal // TODO: Make this survive reload

      // Clear previous data
      this.title = 'Loading..'
      this.message = null
      this.modalData = null

      let listUrl = '/samplesheets/ajax/study/links/' +
        this.studyUuid + '?' + query['key'] + '=' + query['value']

      fetch(listUrl, {
        credentials: 'same-origin'
      })
        .then(response => response.json())
        .then(
          response => {
            if ('data' in response && 'title' in response) {
              this.title = response['title']
              let filesFound = false

              for (let cat in response['data']) {
                if (response['data'][cat]['files'].length > 0) {
                  filesFound = true
                  break
                }
              }

              if (filesFound) {
                this.modalData = response['data']
              } else {
                this.message = 'No files found'
              }
            } else if ('message' in response) {
              this.message = response['message']
            }
          }).catch(function (error) {
          this.message = 'Error fetching data: ' + error.message
        })
      modalElement.show()
    }
  }
}
</script>

<style scoped>
</style>
