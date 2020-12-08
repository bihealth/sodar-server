<template>
  <b-modal
      id="sodar-ss-irods-modal" ref="irodsDirModal"
      no-fade hide-footer
      size="xl"
      :static="true">
    <template slot="modal-header">
      <h5 class="modal-title text-nowrap mr-5">{{ title }}</h5>
      <b-input
          id="sodar-ss-irods-filter"
          size="sm"
          placeholder="Filter"
          class="ml-auto"
          @update="onFilterUpdate">
      </b-input>
      <button
          type="button"
          class="close"
          @click="hideModal">
        ×
      </button>
    </template>
    <!-- Object list -->
    <div v-if="objectList"
         id="sodar-irods-modal-content">
      <table class="table sodar-card-table sodar-irods-obj-table">
        <thead>
          <tr>
            <th>File</th>
            <th>Size</th>
            <th>Modified</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(objInfo, index) in objectList"
              :key="index"
              v-show="objInfo.visibleInList"
              class="sodar-ss-irods-obj">
            <td>
              <a :href="irodsWebdavUrl + objInfo.path">
                <span class="text-muted">{{ getRelativePath(objInfo.path) }}/</span>{{ objInfo.name }}
              </a>
            </td>
            <td>{{ objInfo.size | prettyBytes }}</td>
            <td>{{ objInfo.modify_time }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    <!-- Empty -->
    <div v-else-if="empty"
         class="text-muted font-italic"
         id="sodar-ss-irods-empty">
      Empty collection
    </div>
    <!-- Message/error -->
    <div v-else-if="message"
         class="text-danger font-italic"
         id="sodar-ss-irods-message">
      {{ this.message }}
    </div>
    <!-- Waiting -->
    <div v-else
         class="text-center"
         id="sodar-ss-irods-wait">
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
    onFilterUpdate (event) {
      for (let i = 0; i < this.objectList.length; i++) {
        const vis = event === '' ||
          this.objectList[i].displayPath.toLowerCase().includes(event)
        this.$set(this.objectList[i], 'visibleInList', vis)
      }
      this.$forceUpdate()
    },
    setTitle (title) {
      this.title = title
    },
    getRelativePath (path) {
      const pathSplit = path.split('/')
      return pathSplit.slice(this.dirPathLength, pathSplit.length - 1).join('/')
    },
    handleObjListResponse (response) {
      if ('data_objects' in response) {
        if (response.data_objects.length > 0) {
          this.objectList = response.data_objects

          for (let i = 0; i < this.objectList.length; i++) {
            this.objectList[i].visibleInList = true
            this.objectList[i].displayPath =
              this.getRelativePath(this.objectList[i].path) +
                this.objectList[i].name
          }
        } else {
          this.message = 'Empty collection'
          this.empty = true
        }
      } else if ('message' in response) {
        this.message = response.message
      }
    },
    getObjList (path) {
      const listUrl = '/irodsbackend/api/list/' +
      this.projectUuid + '?path=' + encodeURIComponent(path) + '&md5=0'

      fetch(listUrl, { credentials: 'same-origin' })
        .then(response => response.json())
        .then(response => {
          this.handleObjListResponse(response)
        }).catch(function (error) {
          this.message = 'Error fetching data: ' + error.message
        })
    },
    showModal (path) {
      const modalElement = this.$refs.irodsDirModal

      // Clear previous data
      this.empty = false
      this.message = null
      this.objectList = null
      this.dirPath = path
      this.dirPathLength = this.dirPath.split('/').length

      this.getObjList(path)
      modalElement.show()
    },

    hideModal () {
      this.$refs.irodsDirModal.hide()
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

h5 {
  width: 100%;
}

input#sodar-ss-irods-filter {
  max-width: 200px;
}

</style>
