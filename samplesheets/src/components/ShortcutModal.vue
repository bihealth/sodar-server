<template>
  <b-modal id="sodar-vue-shortcut-modal" ref="shortcutModal"
           centered no-fade hide-footer
           size="md"
           :title="title">
    <div v-if="modalData"
         id="sodar-vue-shortcut-modal-content">
      <div v-for="(cat, index) in modalData"
           :key="index"
           class="pb-3">
        <h5>{{ cat['title'] }}</h5>
        <div v-if="cat['links'].length > 0">
          <div v-for="(link, index) in cat['links']" :key="index">
            <a :href="link['url']" target="_blank">{{ link['label'] }}</a>
          </div>
        </div>
        <div v-else class="text-muted">N/A</div>
      </div>
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

      let listUrl = '/samplesheets/api/study/links/get/' +
        this.studyUuid + '?' + query['key'] + '=' + query['value']

      fetch(listUrl)
        .then(response => response.json())
        .then(
          response => {
            if ('data' in response && 'title' in response) {
              this.title = response['title']
              let filesFound = false

              for (let cat in response['data']) {
                if (response['data'][cat]['links'].length > 0) {
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
