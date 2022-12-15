<template>
  <b-modal
      id="sodar-ss-irods-modal" ref="irodsDirModal"
      no-fade hide-footer
      size="xl"
      :static="true">
    <template slot="modal-header">
      <h5 class="modal-title text-nowrap mr-5">{{ title }}</h5>
      <span v-if="fileCount > 0"
            class="badge badge-pill badge-info sodar-ss-irods-stats mr-3 mt-2">
        {{ fileCount }} file<span v-if="fileCount !== 1">s</span>
        ({{ fileSize | prettyBytes }})
      </span>
      <b-input
          id="sodar-ss-irods-filter"
          size="sm"
          placeholder="Filter"
          class="ml-auto"
          v-model="filterInput"
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
            <th>iRODS</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(objInfo, index) in objectList"
              :key="index"
              v-show="objInfo.visibleInList"
              class="sodar-ss-irods-obj">
            <td :class="strikeActiveRequest(objInfo)">
              <a :href="irodsWebdavUrl + objInfo.path">
                <span class="text-muted">{{ getRelativePath(objInfo.path) }}/</span>{{ objInfo.name }}
              </a>
            </td>
            <td :class="strikeActiveRequest(objInfo)">
              {{ objInfo.size | prettyBytes }}
            </td>
            <td :class="strikeActiveRequest(objInfo)">
              {{ objInfo.modify_time }}
            </td>
            <td>
              <b-button
                  v-if="objInfo.irods_request_status === 'ACTIVE'"
                  variant="primary"
                  class="sodar-list-btn sodar-ss-popup-list-btn sodar-ss-req-btn
                         sodar-ss-request-cancel-btn"
                  :title="getRequestCancelTitle(objInfo)"
                  :disabled="!allowRequestCancel(objInfo)"
                  @click="cancelRequest(index)"
                  v-b-tooltip.hover.d300>
                <img src="/icons/mdi/cancel.svg?color=%23fff" class="mt-0" />
              </b-button>
              <b-button
                  v-else
                  variant="danger"
                  class="sodar-list-btn sodar-ss-popup-list-btn sodar-ss-req-btn
                         sodar-ss-request-delete-btn"
                  :title="getRequestIssueTitle(objInfo)"
                  :disabled="!allowRequestIssue(objInfo)"
                  @click="issueRequest(index)"
                  v-b-tooltip.hover.d300>
                <img src="/icons/mdi/delete.svg?color=%23fff" />
              </b-button>
            </td>
          </tr>
          <tr v-if="objectList.length > 0 && visCount === 0"
              id="sodar-ss-irods-filter-empty">
            <td colspan="4"
                class="text-muted text-center font-italic">
              No files found with current filter.
            </td>
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
      <img src="/icons/mdi/loading.svg?color=%236c757d&height=64"
           class="spin" />
    </div>
  </b-modal>
</template>

<script>

const objListUrl = '/samplesheets/ajax/irods/objects/'
const issueDeleteRequestUrl = '/samplesheets/ajax/irods/request/create/'
const cancelDeleteRequestUrl = '/samplesheets/ajax/irods/request/delete/'

export default {
  name: 'IrodsDirModal',
  props: [
    'irodsWebdavUrl',
    'projectUuid',
    'app'
  ],
  data () {
    return {
      title: 'Modal title',
      objectList: null,
      empty: false,
      message: null,
      dirPath: null,
      dirPathLength: null,
      fileCount: 0,
      fileSize: 0,
      filterInput: null,
      visCount: null
    }
  },
  methods: {
    onFilterUpdate (event) {
      let visCount = 0
      for (let i = 0; i < this.objectList.length; i++) {
        const vis = event === '' ||
          this.objectList[i].displayPath.toLowerCase().includes(event)
        this.$set(this.objectList[i], 'visibleInList', vis)
        if (vis === true) visCount += 1
      }
      this.visCount = visCount
      this.$forceUpdate()
    },
    setTitle (title) {
      this.title = title
    },
    getRelativePath (path) {
      const pathSplit = path.split('/')
      return pathSplit.slice(this.dirPathLength, pathSplit.length - 1).join('/')
    },
    strikeActiveRequest (objInfo) {
      return { 'text-strikethrough': objInfo.irods_request_status === 'ACTIVE' }
    },
    allowRequestCancel (objInfo) {
      return this.app.sodarContext.perms.is_superuser ||
        objInfo.irods_request_user === this.app.sodarContext.user_uuid
    },
    allowRequestIssue (objInfo) {
      return this.app.sodarContext.perms.edit_sheet &&
        objInfo.irods_request_status === null
    },
    getRequestCancelTitle (objInfo) {
      return this.allowRequestCancel(objInfo)
        ? 'Cancel Delete Request'
        : 'Already requested by another user'
    },
    getRequestIssueTitle (objInfo) {
      return this.allowRequestIssue(objInfo)
        ? 'Issue Delete Request'
        : 'User not allowed to issue request'
    },
    handleObjListResponse (response) {
      if ('irods_data' in response) {
        if (response.irods_data.length > 0) {
          this.objectList = response.irods_data
          this.fileCount = response.irods_data.length
          for (let i = 0; i < this.objectList.length; i++) {
            this.objectList[i].visibleInList = true
            this.objectList[i].displayPath =
              this.getRelativePath(this.objectList[i].path) +
                this.objectList[i].name
            this.fileSize += this.objectList[i].size
          }
          this.visCount = this.fileCount
        } else {
          this.message = 'Empty collection'
          this.empty = true
        }
      } else if ('detail' in response) {
        this.message = response.detail
      }
    },
    getObjList (path) {
      const listUrl = objListUrl + this.projectUuid + '?path=' +
          encodeURIComponent(path)

      fetch(listUrl, { credentials: 'same-origin' })
        .then(response => response.json())
        .then(response => {
          this.handleObjListResponse(response)
        }).catch(function (error) {
          this.message = 'Error fetching data: ' + error.detail
        })
    },
    handleDeleteRequestResponse (response, index) {
      if (response.detail === 'ok') {
        this.objectList[index].irods_request_status = response.status
        this.objectList[index].irods_request_user = response.user
      }
    },
    issueRequest (index) {
      if (confirm(
        'Do you really want to request deletion for "' +
          this.objectList[index].name + '"?')) {
        fetch(issueDeleteRequestUrl + this.projectUuid, {
          method: 'POST',
          body: JSON.stringify({ path: this.objectList[index].path }),
          credentials: 'same-origin',
          headers: {
            Accept: 'application/json',
            'Content-Type': 'application/json',
            'X-CSRFToken': this.app.sodarContext.csrf_token
          }
        }).then(response => response.json())
          .then(response => {
            this.handleDeleteRequestResponse(response, index)
          }).catch(function (error) {
            this.message = 'Error issuing iRODS delete request: ' + error.detail
          })
      }
    },
    cancelRequest (index) {
      fetch(cancelDeleteRequestUrl + this.projectUuid, {
        method: 'POST',
        body: JSON.stringify({ path: this.objectList[index].path }),
        credentials: 'same-origin',
        headers: {
          Accept: 'application/json',
          'Content-Type': 'application/json',
          'X-CSRFToken': this.app.sodarContext.csrf_token
        }
      }).then(response => response.json())
        .then(response => {
          this.handleDeleteRequestResponse(response, index)
        }).catch(function (error) {
          this.message = 'Error canceling iRODS delete request: ' + error.detail
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
      this.fileCount = 0
      this.fileSize = 0
      this.filterInput = ''
      this.visCount = null
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

table.sodar-irods-obj-table thead tr th:nth-child(1),
table.sodar-irods-obj-table tbody tr td:nth-child(1) {
  width: 100%;
}

table.sodar-irods-obj-table thead tr th:nth-child(2),
table.sodar-irods-obj-table tbody tr td:nth-child(2) {
  width: 60px;
  text-align: right;
}

table.sodar-irods-obj-table tbody tr td:nth-child(2) {
  text-align: right;
  white-space: nowrap;
}

table.sodar-irods-obj-table thead tr th:nth-child(3),
table.sodar-irods-obj-table tbody tr td:nth-child(3) {
  min-width: 160px;
  white-space: nowrap;
}

table.sodar-irods-obj-table thead tr th:nth-child(4),
table.sodar-irods-obj-table tbody tr td:nth-child(4) {
  width: 60px;
  text-align: right;
}

h5 {
  width: 100%;
}

input#sodar-ss-irods-filter {
  max-width: 200px;
}

.sodar-ss-req-btn {
  padding-top: 0 !important;
}
</style>
