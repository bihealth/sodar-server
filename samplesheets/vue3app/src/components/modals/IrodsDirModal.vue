<script setup lang="ts">
import { ref, useTemplateRef } from 'vue'
import { BButton, BFormInput, BModal } from 'bootstrap-vue-next'
import prettyBytes from 'pretty-bytes'

import ModalHeader from '@/components/modals/ModalHeader.vue'
import WaitSection from '@/components/WaitSection.vue'
import { useAppStore } from '@/stores/appstore.ts'

interface IrodsDirFile {
  displayPath?: string, // Added by this component
  irods_request_status: string | null,
  irods_request_user: string | null,
  modify_time: string,
  name: string,
  path: string,
  size: number,
  type: string,
  visibleInList?: boolean // Added by this component
}
interface IrodsDirResponse {
  detail?: string
  irods_data?: Array<IrodsDirFile>
}
interface IrodsDataRequestResponse {
  detail: string,
  status: string | null,
  user: string | null
}

const appStore = useAppStore()

// Modal setup
const modalRef = useTemplateRef('irodsDirModal')
const showModal = ref<boolean>(false)

// Actual constants
const fileListUrl: string = '/samplesheets/ajax/irods/objects/'
const dataRequestUrls = {
  issue: '/samplesheets/ajax/irods/request/create/',
  cancel: '/samplesheets/ajax/irods/request/delete/'
}
const modalTitlePrefix = 'Files in iRODS'

// Reactive vars
const emptyList = ref<boolean>(false)
const fileCount = ref<number>(0)
const fileList = ref<Array<IrodsDirFile>>([])
const fileSize = ref<number>(0)
const filterInput = ref<string>('')
const irodsPath = ref<string>('')
const message = ref<string>('')
const modalTitle = ref<string>(modalTitlePrefix)
const visCount = ref<number>(0)

// Return cell class with strikethrough if delete request is active
function getCellClass (fileEntry: IrodsDirFile) {
  return { 'text-strikethrough': fileEntry.irods_request_status === 'ACTIVE' }
}

// Return relative path for file
function getRelativePath (path: string): string {
  const pathSplit = path.split('/')
  return pathSplit.slice(
    irodsPath.value.split('/').length, pathSplit.length - 1).join('/')
}

// Update file list for filter input
function updateFilter () {
  let vc = 0
  for (let i = 0; i < fileList.value.length; i++) {
    const vis = filterInput.value === '' ||
      fileList.value[i]?.displayPath?.toLowerCase().includes(
        filterInput.value.toLowerCase())
    fileList.value[i]!.visibleInList = vis
    if (vis === true) vc += 1
  }
  visCount.value = vc
}

// Handle data received from file list Ajax call
function handleFileListResponse (response: IrodsDirResponse) {
  if ('irods_data' in response) {
    if (response.irods_data!.length > 0) {
      fileList.value = response.irods_data as Array<IrodsDirFile>
      fileCount.value = fileList.value.length
      for (let i = 0; i < fileList.value.length; i++) {
        fileList.value[i]!.visibleInList = true
        fileList.value[i]!.displayPath = getRelativePath(
          fileList.value[i]!.path + '/' + fileList.value[i]!.name)
        fileSize.value += fileList.value[i]!.size
      }
      visCount.value = fileCount.value
    } else {
      message.value = 'Empty collection'
      emptyList.value = true
    }
  } else if ('detail' in response) {
    message.value = response.detail as string
  }
}

// Get file list with Ajax call
function getFileList (path: string) {
  const listUrl: string = fileListUrl + appStore.projectUuid + '?path=' +
    encodeURIComponent(path)
  fetch(listUrl, { credentials: 'same-origin' })
    .then(response => response.json())
    .then(response => {
      handleFileListResponse(response)
    }).catch(function (error) {
      message.value = 'Error fetching data: ' + error.detail
  })
}

// Return true if user is allowed to issue iRODS data request for deletion
function allowDataRequestIssue (file: IrodsDirFile): boolean {
  return appStore.getPerm('edit_sheet') as boolean && !file.irods_request_status
}

// Return true if user is allowed to delete iRODS data request
function allowDataRequestCancel (file: IrodsDirFile): boolean {
  return appStore.getPerm('is_superuser') as boolean ||
    file.irods_request_user === appStore.sodarContext?.user_uuid
}

// Return button title for data request issuing
function getDataRequestIssueTitle (file: IrodsDirFile): string {
  return allowDataRequestIssue(file)
    ? 'Issue iRODS delete request'
    : 'User not allowed to issue request'
}

// Return button title for data request cancelling
function getDataRequestCancelTitle (file: IrodsDirFile): string {
  return allowDataRequestCancel(file)
    ? 'Cancel iRODS delete request'
    : 'Already requested by another user'
}

// Get parameters for iRODS data request Ajax view request
function getDataRequestParams (file: IrodsDirFile): RequestInit {
  return {
    method: 'POST',
      body: JSON.stringify({ path: file.path }),
      credentials: 'same-origin',
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
        'X-CSRFToken': appStore.sodarContext!['csrf_token'] as string
      }
  } as RequestInit
}

// Handle iRODS delete issue/cancel request response
function handleDataRequestResponse (
    response: IrodsDataRequestResponse,
    file: IrodsDirFile) {
  if (response.detail === 'ok') {
    file.irods_request_status = response.status
    file.irods_request_user = response.user
  }
}

// Submit an Ajax request for iRODS data request creation or deletion
function submitDataRequest (file: IrodsDirFile, action: 'issue' | 'cancel') {
  if (action === 'cancel' || confirm(
      'Do you really want to request deletion for "' + file.name + '"?')) {
    const url = dataRequestUrls[action] + appStore.projectUuid
    fetch(url, getDataRequestParams(file))
      .then(response => response.json())
      .then(response => {
        handleDataRequestResponse(response, file)
      }).catch(function (error) {
        message.value = 'Error modifying iRODS delete request: ' + error.detail
      })
  }
}

// Setup data and show modal
function show (path: string) {
  // Reset previous data
  emptyList.value = false
  fileCount.value = 0
  fileList.value = []
  fileSize.value = 0
  filterInput.value = ''
  message.value = ''
  visCount.value = 0

  // Setup data for current modal
  irodsPath.value = path
  modalTitle.value = modalTitlePrefix + ': ' + path.split('/').pop()

  // Show modal and fetch data
  showModal.value = true
  getFileList(path)
}
defineExpose({ show })
</script>

<template>
  <BModal
      id="sodar-ss-irods-dir-modal"
      ref="irodsDirModal"
      v-model="showModal"
      size="xl"
      no-footer no-animation>
    <template #header>
      <ModalHeader
          :modal-ref="modalRef"
          :title="modalTitle">
        <template v-slot:extend>
          <div id="sodar-ss-irods-stats-container">
            <span v-if="fileCount > 0"
                  class="badge badge-pill badge-info sodar-ss-irods-stats mr-3">
              {{ fileCount }} file<span v-if="fileCount !== 1">s</span>
              ({{ prettyBytes(fileSize) }})
            </span>
          </div>
          <BFormInput
            id="sodar-ss-irods-dir-modal-filter"
            size="sm"
            placeholder="Filter"
            v-model="filterInput"
            @keyup="updateFilter">
          </BFormInput>
        </template>
      </ModalHeader>
    </template>
    <!-- File list -->
    <div v-if="fileList.length > 0"
         id="sodar-ss-irods-dir-modal-content">
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
          <tr v-for="(file, fileIdx) in fileList"
              :key="fileIdx"
              v-show="file.visibleInList"
              class="sodar-ss-irods-obj">
            <td :class="getCellClass(file)">
              <a :href="appStore.sodarContext!['irods_webdav_url'] + file.path">
                <span class="text-muted">{{ getRelativePath(file.path) }}/</span>{{ file.name }}
              </a>
            </td>
            <td :class="getCellClass(file)">
              {{ prettyBytes(file.size) }}
            </td>
            <td :class="getCellClass(file)">
              {{ file.modify_time }}
            </td>
            <td :class="getCellClass(file)">
              <BButton
                  v-if="file.irods_request_status === 'ACTIVE'"
                  variant="primary"
                  class="sodar-list-btn sodar-ss-popup-list-btn sodar-ss-req-btn
                         sodar-ss-request-cancel-btn"
                  :title="getDataRequestCancelTitle(file)"
                  :disabled="!allowDataRequestCancel(file)"
                  @click="submitDataRequest(file, 'cancel')">
                <i class="iconify text-white" data-icon="mdi:cancel"></i>
              </BButton>
              <BButton
                  v-else
                  variant="danger"
                  class="sodar-list-btn sodar-ss-popup-list-btn sodar-ss-req-btn
                         sodar-ss-request-delete-btn"
                  :title="getDataRequestIssueTitle(file)"
                  :disabled="!allowDataRequestIssue(file)"
                  @click="submitDataRequest(file, 'issue')">
                <i class="iconify text-white" data-icon="mdi:delete"></i>
              </BButton>
            </td>
          </tr>
          <tr v-if="fileList.length > 0 && visCount === 0"
              id="sodar-ss-irods-filter-empty">
            <td colspan="4"
                class="text-muted text-center font-italic">
              No files found with current filter.
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <!-- Empty list -->
    <div v-else-if="emptyList"
         class="text-muted font-italic"
         id="sodar-ss-irods-dir-modal-empty">
      Empty collection
    </div>
    <!-- Message/error -->
    <div v-else-if="message"
         class="text-danger font-italic"
         id="sodar-ss-irods-dir-modal-message">
      {{ message }}
    </div>
    <WaitSection v-else></WaitSection>
  </BModal>
</template>

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
#sodar-ss-irods-dir-modal-filter {
  max-width: 200px;
  height: 28px;
}
#sodar-ss-irods-stats-container {
  line-height: 28px !important;
}
</style>
