<script setup lang="ts">
import { ref } from 'vue'
import { BButton } from 'bootstrap-vue-next'
import { useClipboard } from '@vueuse/core'
import {
  type SheetTableCellData,
  type SheetTableOntologyRef
} from '@/types.ts'
import { CELL_EMPTY_VAL } from '@/constants.ts'

interface ContactValue {
  name: string,
  email: string | null
}
interface ExternalLink {
  label: string,
  id: string | number,
  url: string | null
}
interface FileLink {
  label: string,
  url: string | null
}

const props = defineProps({ params: Object })
const clipboard = useClipboard()

const contactRegex = /(.+?)[<[](.+?)(?=[>\]])/
const simpleLinkRegex = /([^<>]+)\s*<(https?:\/\/[^<>]+)>/
const extLinkId = '{id}'

const cellData = props.params!.value as SheetTableCellData
const enableHover = (props.params!.enableHover === undefined)
  ? true
  : props.params!.enableHover

const colType = ref<string | null>(props.params?.colType)
const displayValue = ref<
  string | Array<string> | Array<ContactValue> | Array<ExternalLink> | FileLink
>('')

// Return header name normalized into lower case
function getHeaderName(): string {
  return props.params!.colDef.headerName.toLowerCase()
}

// Return contact name(s) and email(s)
function getContact (): Array<ContactValue> {
  const ret = []
  if (cellData.value) {
    let splitVal: Array<string>
    if (typeof cellData.value === 'string') {
      splitVal = cellData.value.split(';')
    } else {
      splitVal = cellData.value as Array<string>
    }
    for (let i = 0; i < splitVal.length; i++) {
      if (contactRegex.test(splitVal[i] as string)) {
        const contactGroup = contactRegex.exec(splitVal[i] as string)
        ret.push({
          name: (contactGroup![1] as string).trim(),
          email: contactGroup![2] as string })
      } else {
        ret.push({ name: (splitVal![i] as string).trim(), email: null })
      }
    }
  }
  if (ret.length === 0) colType.value = null // Fallback to plain field
  return ret
}

// Return external links
function getExternalLinks (): Array<ExternalLink> {
  const ret = []
  const labels = props.params!.linkLabels
  let v
  if (!Array.isArray(cellData.value)) v = [cellData.value]
  else v = cellData.value
  for (let i = 0; i < v.length; i++) {
    const splitId = (v[i] as string)?.split(':')
    if (splitId.length > 1 && splitId[1]) {
      const key = splitId[0] as string
      let label = key
      let url = null
      if (key in labels) {
        label = labels[key].label
        if (labels[key].hasOwnProperty('url') &&
            labels[key].url &&
            labels[key].url.includes(extLinkId)) {
          url = labels[key].url.replace(
            extLinkId, encodeURIComponent(splitId[1]))
        }
      }
      ret.push({ label: label, id: splitId[1], url: url })
    }
  }
  return ret
}

// Return file link data
function getFileLink(): FileLink {
  let url = null
  if ('link' in cellData) url = cellData.link
  return { label: cellData.value, url: url } as FileLink
}

// Return file link tooltip
function getFileLinkToolTip (): string {
  if ('tooltip' in cellData) return cellData.tooltip as string
  return ''
}

// Test for simple link regex in value
// NOTE: This currently only works for non-list values, see #2414
function testSimpleLink (): boolean {
  if (Array.isArray(cellData.value)) return false
  const ret = simpleLinkRegex.test(cellData.value)
  // TODO: Set up simpleLink in displayValue instead?
  if (ret) {
    displayValue.value = cellData.value.match(simpleLinkRegex) as Array<string>
  }
  return ret
}

// Return simple link legend
// NOTE: This currently only works for non-list values, see #2414
function getSimpleLinkLegend (): string {
  return (displayValue.value as Array<string>)[1]!.trim()
}

// Return file link no url cell class
function getNoUrlFileClass (): string {
  if (!props.params?.editMode) return 'text-muted'
  return ''
}

// Return ontology terms as string for clipboard copying
function getOntologyTermString (): string {
  const ret = []
  for (let i = 0; i < cellData.value.length; i++) {
    const term = cellData.value[i] as SheetTableOntologyRef
    const idx = term.accession.indexOf('HP_')
    ret.push(term.accession.substring(idx).replace('_', ':'))
  }
  return ret.join(';')
}

// Handle mouseover and mouseout events for cell
function onMouseOver (event: MouseEvent) {
  const target = event.currentTarget as HTMLElement
  if (enableHover && target.scrollWidth > target.clientWidth) {
    target.className += ' sodar-ss-data-hover'
  }
}
function onMouseOut (event: MouseEvent) {
  (event.currentTarget as HTMLElement).className = 'sodar-ss-data'
}

// Setup cell data
if (cellData && cellData.value && cellData.value.length > 0) {
  // TODO: Enabled/disable hover overflow
  if (colType.value === 'CONTACT') {
    displayValue.value = getContact()
  } else if (colType.value === 'EXTERNAL_LINKS') {
    displayValue.value = getExternalLinks()
  } else if (colType.value == 'LINK_FILE') {
    displayValue.value = getFileLink()
  } else if (Array.isArray(cellData.value) &&
      typeof cellData.value[0] === 'string') {
    // Join list of strings
    displayValue.value = cellData.value.join('; ')
  }
} else {
  // Add empty value placeholder for displaying
  displayValue.value = cellData.newInit ? '' : CELL_EMPTY_VAL
}
</script>

<template>
  <div class="sodar-ss-data"
       :data-col-num="params?.colDef.field.substring(3)"
       :data-row-id="params?.node.id"
       @mouseover="onMouseOver"
       @mouseout="onMouseOut">
    <!-- Ontology term(s) -->
    <span v-if="colType === 'ONTOLOGY' && cellData.value.length > 0"
          class="sodar-ss-data-val-ontology">
      <span v-if="!params?.editMode && getHeaderName() === 'hpo terms'">
        <BButton
            class="btn sodar-list-btn mr-1 sodar-ss-hpo-copy-btn"
            title="Copy HPO term IDs to clipboard"
            @click="clipboard.copy(getOntologyTermString())">
          <i class="iconify" data-icon="mdi:clipboard-text-multiple"></i>
        </BButton>
      </span>
      <span v-for="(term, termIdx) in cellData.value"
            :key="termIdx">
        <span v-if="!params?.editMode">
          <a :href="(term as SheetTableOntologyRef).accession"
             :title="(term as SheetTableOntologyRef).ontology_name as string"
             target="_blank">
            {{ (term as SheetTableOntologyRef).name }}
          </a><span v-if="termIdx < cellData.value.length - 1">; </span>
        </span>
        <span v-else>
          {{ (term as SheetTableOntologyRef).name }}<span
            v-if="termIdx < cellData.value.length - 1">; </span>
        </span>
      </span>
    </span>
    <!-- Contacts with email -->
    <span v-else-if="colType === 'CONTACT' && displayValue"
          class="sodar-ss-data-val-contact">
      <span v-for="(contact, contactIdx) in displayValue"
            :key="contactIdx">
        <a :href="'mailto:' + (contact as ContactValue).email">
          {{ (contact as ContactValue).name }}
        </a><span v-if="(contactIdx as number) < (
                          displayValue as Array<ContactValue>
                        ).length - 1">; </span>
      </span>
    </span>
    <!-- External links -->
    <span v-else-if="colType == 'EXTERNAL_LINKS' &&
                     displayValue &&
                     displayValue != CELL_EMPTY_VAL"
          class="sodar-ss-data-val-ext">
      <span v-for="(idRef, idx) in displayValue"
            :key="idx"
            class="badge-group"
            :title="(idRef as ExternalLink).label">
        <span class="badge badge-secondary">ID</span>
        <span v-if="(idRef as ExternalLink).url"
              class="badge badge-info">
          <a :href="(idRef as ExternalLink).url as string"
             target="_blank"
             class="sodar-ss-data-ext-link">
            {{ (idRef as ExternalLink).id }}
          </a>
        </span>
        <span v-else class="badge badge-info">
          {{ (idRef as ExternalLink).id }}
        </span>
      </span>
    </span>
    <!-- File link -->
    <span v-else-if="colType === 'LINK_FILE' &&
                     displayValue &&
                     displayValue !== CELL_EMPTY_VAL"
          class="sodar-ss-data-val-file">
      <span v-if="(displayValue as FileLink).url">
        <a :href="(displayValue as FileLink).url as string"
           :title="getFileLinkToolTip()"
           target="_blank">
          {{ (displayValue as FileLink).label }}
        </a>
      </span>
      <span v-else
            :class="getNoUrlFileClass()">
        {{ (displayValue as FileLink).label }}
      </span>
    </span>
    <!-- Simple links for string columns -->
    <span v-else-if="testSimpleLink()"
          class="sodar-ss-data-val-link">
      <a :href="(displayValue as Array<string>)![2]" target="_blank">
        {{ getSimpleLinkLegend() }}
      </a>
    </span>
    <!-- Special cases -->
    <span v-else-if="displayValue"
          class="sodar-ss-data-val-special">
      {{ displayValue }}
    </span>
    <!-- Plain/numeric/empty/undetected value -->
    <span v-else
          class="sodar-ss-data-val-plain">
      {{ cellData.value }}
    </span>
    <!-- Unit -->
    <span v-if="cellData.value && 'unit' in cellData && cellData.unit"
          class="text-muted ml-1 sodar-ss-data-unit">
      {{ cellData.unit }}
    </span>
  </div>
</template>

<style scoped>
</style>
