<template>
  <b-modal id="sodar-vue-irods-modal" ref="irodsDirModal"
           centered no-fade hide-footer
           size="xl"
           :title="title">
    <!-- Object list -->
    <div v-if="objectList"
         id="sodar-vue-irods-modal-content">
      <table class="table sodar-card-table table-striped sodar-irods-obj-table">
        <thead>
          <tr>
            <th>File</th>
            <th>Size</th>
            <th>Modified</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(objInfo, index) in objectList" :key="index">
            <td>
              <a :href="irodsWebdavUrl + objInfo['path']">
                <span class="text-muted">{{ getRelativePath(objInfo['path']) }}/</span>{{ objInfo['name'] }}
              </a>
            </td>
            <td>{{ objInfo['size'] | prettyBytes }}</td>
            <td>{{ objInfo['modify_time'] }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    <!-- Empty -->
    <div v-else-if="empty" class="text-muted font-italic">
      Empty collection
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
  name: 'IrodsDirModal',
  props: [
    'irodsWebdavUrl',
    'projectUuid'
  ],
  data () {
    return {
      title: 'Modal title',
      objectList: null,
      empty: false,
      message: null,
      dirPath: null,
      dirPathLength: null
    }
  },
  methods: {
    setTitle (title) {
      this.title = title
    },
    getRelativePath (path) {
      let pathSplit = path.split('/')
      return pathSplit.slice(this.dirPathLength, pathSplit.length - 1).join('/')
    },
    getDirList (path) {
      let modalElement = this.$refs.irodsDirModal // TODO: Make this survive reload

      // Clear previous data
      this.empty = false
      this.message = null
      this.objectList = null
      this.dirPath = path
      this.dirPathLength = this.dirPath.split('/').length

      let listUrl = '/irodsbackend/api/list/' +
        this.projectUuid + '?path=' + encodeURIComponent(path) + '&md5=0'

      fetch(listUrl)
        .then(response => response.json())
        .then(
          response => {
            if ('data_objects' in response) {
              if (response['data_objects'].length > 0) {
                this.objectList = response['data_objects']
              } else {
                this.message = 'Empty collection'
                this.empty = true
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
/* Size column */
table.sodar-irods-obj-table thead tr th:nth-child(2) {
  min-width: 60px;
  text-align: right;
}

table.sodar-irods-obj-table tbody tr td:nth-child(2) {
  text-align: right;
  white-space: nowrap;
}

/* Date column */
table.sodar-irods-obj-table tbody tr td:nth-child(3) {
  width: 5%;
  white-space: nowrap;
}

/* MD5 column */
table.sodar-irods-obj-table thead tr th:nth-child(4) {
  width: 40px;
  text-align: center;
}

table.sodar-irods-obj-table tbody tr td:nth-child(4) {
  text-align: center;
}
</style>
