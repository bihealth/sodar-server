<script setup lang="ts">
import { ref } from 'vue'
import { BButton, BFormInput } from 'bootstrap-vue-next'

import { type SodarContextComments } from '@/types.ts'

// Constants -------------------------------------------------------------------

const INVALID_CLASS = 'text-danger'

// External Data ---------------------------------------------------------------

const props = defineProps(['comments', 'mandatory'])

// Refs ------------------------------------------------------------------------

const cFields = ref<SodarContextComments>(props.comments)
const insKey = ref<string>('')
const insKeyClass = ref<string>('')
const insVal = ref<string>('')
const valid = ref<boolean>(true)

// Internal Vars ---------------------------------------------------------------

const lcLookup: Array<string> = []

// Setup -----------------------------------------------------------------------

// Add mandatory comments with empty value if missing
for (const c of props.mandatory) {
  if (!(c in cFields.value)) {
    cFields.value[c] = ''
  }
}

// Add lower case lookup for case-insensitive key validation
for (const k of Object.keys(cFields.value)) {
  lcLookup.push(k.toLowerCase())
}

// Helpers ---------------------------------------------------------------------

function enableInsert () {
  return insKey.value && insVal.value && valid.value
}

function onDeleteClick (cKey: string) {
  delete cFields.value[cKey]
}

function onInsertClick () {
  cFields.value[insKey.value.trim()] = insVal.value.trim()
  lcLookup.push(insVal.value.trim())
}

function onInsertKeyInput () {
  if (lcLookup.includes(insKey.value.trim().toLowerCase())) {
    valid.value = false
    insKeyClass.value = INVALID_CLASS
  } else {
    valid.value = true
    insKeyClass.value = ''
  }
}
</script>

<template>
  <tbody class="sodar-ss-isa-comment-edit-body">
    <tr v-for="(cKey, cIdx) in Object.keys(cFields)"
        :key="cIdx"
        class="sodar-ss-isa-comment-edit-row">
      <td>
        {{ cKey }}
        <i v-if="mandatory.includes(cKey)"
           class="iconify text-muted sodar-ss-isa-comment-mandatory-icon"
           data-icon="mdi:lock">
        </i>
      </td>
      <td>
        <BFormInput
            v-model="cFields[cKey]"
            class="sodar-ss-isa-comment-input">
        </BFormInput>
      </td>
      <td>
        <BButton
            variant="danger"
            class="sodar-list-btn sodar-ss-row-btn
                   sodar-ss-isa-comment-delete-btn"
            :disabled="mandatory.includes(cKey)"
            @click="onDeleteClick(cKey)">
          <i class="iconify" data-icon="mdi:close-thick"></i>
        </BButton>
      </td>
    </tr>
  <tr>
    <td class="sodar-ss-isa-comment-td-insert-key">
      <BFormInput
          v-model="insKey"
          :class="'sodar-ss-isa-comment-insert-key ' + insKeyClass"
          @update:model-value="onInsertKeyInput()">
      </BFormInput>
    </td>
    <td>
      <BFormInput
          v-model="insVal"
          class="sodar-ss-isa-comment-insert-value">
      </BFormInput>
    </td>
    <td>
      <BButton
          variant="primary"
          class="sodar-list-btn sodar-ss-row-btn
                 sodar-ss-isa-comment-insert-btn"
          :disabled="!enableInsert()"
          @click="onInsertClick()">
        <i class="iconify" data-icon="mdi:plus-thick"></i>
      </BButton>
    </td>
  </tr>
  </tbody>
</template>

<style scoped>
.sodar-ss-isa-comment-td-insert-key {
  padding-top: 12px !important;
}
</style>
