<script setup lang="ts">
import { ref } from 'vue'
import { BFormInput, BFormTextarea } from 'bootstrap-vue-next'

import { useEditStore } from '@/stores/editStore.ts'
import { type InvStudyEditMeta } from '@/types.ts'
import { EDIT_REGEX, EDIT_REGEX_FILE_NAME } from '@/constants.ts'

// Constants -------------------------------------------------------------------

const INVALID_CLASS = 'text-danger'

// Interfaces ------------------------------------------------------------------

interface FieldValidStatus {
  [key: string]: boolean
}

// External Data ---------------------------------------------------------------

const props = defineProps(['fileNames', 'identifiers', 'metadata', 'studyMode'])
const editStore = useEditStore()

// Refs ------------------------------------------------------------------------

const fieldsValid = ref<FieldValidStatus>({
    fileName: true,
    identifier: true,
    publicReleaseDate: true,
    submissionDate: true
})
const metadata = ref<InvStudyEditMeta>(props.metadata)

// Internal Vars ---------------------------------------------------------------

const elPrefix = 'sodar-ss-' + (props.studyMode ? 'study' : 'inv') + '-'
const fnPrefix = props.studyMode? 's' : 'i'

// Helpers ---------------------------------------------------------------------

function getFieldClass (fieldName: string): string {
  if (fieldsValid.value![fieldName]!) return ''
  return INVALID_CLASS
}

function onDateInput (fieldName: string) {
  const v = metadata.value![fieldName as keyof InvStudyEditMeta]!.trim()
  if (v && !EDIT_REGEX['date']!.test(v)) {
    fieldsValid.value![fieldName] = false
    editStore.modalEditValid = false
  } else {
    fieldsValid.value![fieldName] = true
    editStore.modalEditValid = true
  }
}

function onFileNameInput () {
  const f = metadata.value!.fileName.trim()
  if (!f.startsWith(fnPrefix) ||
      !EDIT_REGEX_FILE_NAME.test(f) ||
      (props.fileNames as Array<string>).includes(f)) {
    fieldsValid.value!.fileName = false
    editStore.modalEditValid = false
  } else {
    fieldsValid.value!.fileName = true
    editStore.modalEditValid = true
  }
}

function onIdentifierInput () {
  const v = metadata.value!.identifier.trim()
  if (v === '' || (props.identifiers as Array<string>).includes(v)) {
    fieldsValid.value!.identifier = false
    editStore.modalEditValid = false
  } else {
    fieldsValid.value!.identifier = true
    editStore.modalEditValid = true
  }
}
</script>

<template>
  <tbody class="sodar-ss-inv-study-meta-edit-body">
    <tr>
      <td>Identifier</td>
      <td>
        <BFormInput
            v-model="metadata.identifier"
            :class="getFieldClass('identifier')"
            :id="elPrefix + 'input-meta-id'"
            @update:model-value="onIdentifierInput()">
        </BFormInput>
      </td>
    </tr>
    <tr>
      <td>Title</td>
      <td>
        <BFormInput
            v-model="metadata.title"
            :id="elPrefix + 'input-meta-title'">
        </BFormInput>
      </td>
    </tr>
    <tr>
      <td>File Name</td>
      <td>
        <BFormInput
            v-model="metadata.fileName"
            :class="getFieldClass('fileName')"
            :id="elPrefix + 'input-meta-file'"
            @update:model-value="onFileNameInput()">
        </BFormInput>
      </td>
    </tr>
    <tr>
      <td>Description</td>
      <td>
        <BFormTextarea
            v-model="metadata.description"
            :id="elPrefix + 'input-meta-desc'"
            rows="4">
        </BFormTextarea>
      </td>
    </tr>
    <tr>
      <td>Submission Date</td>
      <td>
        <BFormInput
            v-model="metadata.submissionDate"
            :class="getFieldClass('submissionDate')"
            :id="elPrefix + 'input-meta-sub-date'"
            @update:model-value="onDateInput('submissionDate')">
        </BFormInput>
      </td>
    </tr>
    <tr>
      <td>Public Release Date</td>
      <td>
        <BFormInput
            v-model="metadata.publicReleaseDate"
            :class="getFieldClass('publicReleaseDate')"
            :id="elPrefix + 'input-meta-pub-date'"
            @update:model-value="onDateInput('publicReleaseDate')">
        </BFormInput>
      </td>
    </tr>
  </tbody>
</template>

<style scoped>
</style>
