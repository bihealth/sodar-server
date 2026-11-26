<script setup lang="ts">
import { ref } from 'vue'
import { BFormInput } from 'bootstrap-vue-next'

import { useAppStore } from '@/stores/appStore.ts'
import { useEditStore } from '@/stores/editStore.ts'
import {
  type SheetOntologyRef,
  type SodarContextInvestigation
} from '@/types.ts'

// Constants -------------------------------------------------------------------

const ACC_FIELD_SUFFIX = 'Accession'
const NAME_FIELD_SUFFIX = 'Name'
const OBO_FIELD_SUFFIX = 'Ontology'
const INVALID_CLASS = 'text-danger'

// External Data ---------------------------------------------------------------

const props = defineProps(['className', 'fieldName', 'term', 'title'])
const appStore = useAppStore()
const editStore = useEditStore()

// Refs ------------------------------------------------------------------------

const accExtraClass = ref<string>('')
const oboExtraClass = ref<string>('')
const term = ref<SheetOntologyRef>(props.term)

// Internal Vars ---------------------------------------------------------------

// TODO: Map these in appStore on app init
const ontologyLookup = (
  appStore.sodarContext!.investigation as SodarContextInvestigation
).ontology_source_refs.map(r => r.name)

// Helpers ---------------------------------------------------------------------

function onNameInput () {
  editStore.modalEditStatus[
    props.fieldName + NAME_FIELD_SUFFIX] = term.value.name.trim() !== ''
}

function onRefInput (ontology: boolean) {
  const accFieldName = props.fieldName + ACC_FIELD_SUFFIX
  const oboFieldName = props.fieldName + OBO_FIELD_SUFFIX
  const refValid = !term.value.ontology_name?.trim() ===
    !term.value.accession?.trim()
  const sourceValid: boolean = !ontology || ontologyLookup.includes(
    term.value.ontology_name!.trim())
  if (!sourceValid || !refValid) {
    editStore.modalEditStatus[accFieldName] = false
    editStore.modalEditStatus[oboFieldName] = false
    accExtraClass.value = INVALID_CLASS
    oboExtraClass.value = INVALID_CLASS
  } else {
    editStore.modalEditStatus[accFieldName] = true
    editStore.modalEditStatus[oboFieldName] = true
    accExtraClass.value = ''
    oboExtraClass.value = ''
  }
}
</script>

<template>
  <tr>
    <td>{{ title }}</td>
    <td>
      <BFormInput
          v-model="term.name"
          placeholder="Name"
          :class="className"
          :id="className + '-name'"
          @update:model-value="onNameInput()">
      </BFormInput>
    </td>
  </tr>
  <tr>
    <td>{{ title }} Source REF</td>
    <td>
      <BFormInput
          v-model="term.ontology_name"
          :class="className + ' ' + oboExtraClass"
          :id="className + '-obo'"
          @update:model-value="onRefInput(true)">
      </BFormInput>
    </td>
  </tr>
  <tr>
    <td>{{ title }} Accession</td>
    <td>
      <BFormInput
          v-model="term.accession"
          :class="className + ' ' + accExtraClass"
          :id="className + '-acc'"
          @update:model-value="onRefInput(false)">
      </BFormInput>
    </td>
  </tr>
</template>

<style scoped>
</style>
