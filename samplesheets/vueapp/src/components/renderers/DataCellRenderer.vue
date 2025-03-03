<template>
  <div class="sodar-ss-data"
       :data-col-num="params.colDef.field.substring(3)"
       :data-row-id="params.node.id"
       @mouseover="onMouseOver"
       @mouseout="onMouseOut">
    <!-- Ontology term(s) -->
    <span v-if="colType === 'ONTOLOGY' && value.value.length > 0">
      <span v-if="!params.app.editMode && headerName === 'hpo terms'">
        <b-button
            class="btn sodar-list-btn mr-1 sodar-ss-hpo-copy-btn"
            title="Copy HPO term IDs to clipboard"
            @click="onCopyHpoTerms">
          <i class="iconify" data-icon="mdi:clipboard-text-multiple"></i>
        </b-button>
      </span>
      <span v-for="(term, termIndex) in value.value" :key="termIndex">
        <span v-if="!params.app.editMode">
          <a :href="term.accession"
             :title="term.ontology_name"
             target="_blank">{{ term.name }}</a><span v-if="termIndex < value.value.length - 1">; </span>
        </span>
        <span v-else>
          {{ term.name }}<span v-if="termIndex < value.value.length - 1">; </span>
        </span>
      </span>
    </span>
    <!-- Contacts with email -->
    <span v-else-if="colType === 'CONTACT' && renderData">
      <span v-for="(contact, index) in renderData" :key="index">
        <span v-if="contact.email !== null">
          <a :href="'mailto:' + contact.email">{{ contact.name }}</a><span v-if="index < renderData.length - 1">; </span>
        </span>
        <span v-else>
          {{ contact.name }}<span v-if="index < renderData.length - 1">; </span>
        </span>
      </span>
    </span>
    <!-- External links -->
    <span v-else-if="colType === 'EXTERNAL_LINKS' && renderData">
      <span v-for="(idRef, index) in renderData.extIds"
            class="badge-group"
            :key="index"
            :title="idRef.label">
        <span class="badge badge-secondary">ID</span>
        <span v-if="idRef.url" class="badge badge-info">
          <a :href="idRef.url" target="_blank" class="sodar-ss-data-ext-link">{{ idRef.id }}</a>
        </span>
        <span v-else class="badge badge-info">{{ idRef.id }}</span>
      </span>
    </span>
    <!-- File link -->
    <span v-else-if="colType === 'LINK_FILE' && renderData">
      <span v-if="renderData.url">
        <a :href="renderData.url"
           :title="getTooltip()"
           target="_blank">{{ renderData.value }}</a>
      </span>
      <span v-else :class="getEmptyFileClass()">
        {{ renderData.value }}
      </span>
    </span>
    <!-- Special cases -->
    <span v-else-if="useDisplayValue">
      {{ displayValue }}
    </span>
    <!-- Simple links for string columns -->
    <span v-else-if="testSimpleLink()">
      <a :href="simpleLink[2]" target="_blank">{{ simpleLink[1].trim() }}</a>
    </span>
    <!-- Plain/numeric/empty/undetected value -->
    <span v-else>
      {{ value.value }}
    </span>
    <!-- Unit -->
    <span v-if="value && value.value && 'unit' in value && value.unit">
      <span class="text-muted">{{ value.unit }}</span>
    </span>
  </div>
</template>

<script>
import Vue from 'vue'

const contactRegex = /(.+?)(?:[<[])(.+?)(?=[>\]])/
const simpleLinkRegex = /([^<>]+)\s*<(https?:\/\/[^<>]+)>/
const extLinkId = '{id}'

export default Vue.extend({
  data () {
    return {
      value: null,
      displayValue: null,
      useDisplayValue: false,
      headerName: null,
      colType: null,
      renderData: null,
      enableHover: null,
      newInit: false,
      newRow: false,
      simpleLink: null
    }
  },
  methods: {
    /* Event handling ----------------------------------------------------- */
    onMouseOver (event) {
      if (this.enableHover &&
          event.currentTarget.scrollWidth > event.currentTarget.clientWidth) {
        event.currentTarget.className += ' sodar-ss-data-hover'
      }
    },
    onMouseOut (event) {
      event.currentTarget.className = 'sodar-ss-data'
    },
    onCopyHpoTerms () {
      const hpoIds = []
      for (let i = 0; i < this.value.value.length; i++) {
        const term = this.value.value[i]
        const splitUrl = term.accession.split('/')
        hpoIds.push(splitUrl[splitUrl.length - 1].replace('_', ':'))
      }
      this.$copyText(hpoIds.join(';'))
      this.params.app.showNotification('Copied', 'success', 1000)
    },
    /* Helpers ------------------------------------------------------------ */
    getHeaderName () {
      // Get header name and place in this.headerName
      return this.params.colDef.headerName.toLowerCase()
    },
    getContact () {
      // Return contact name(s) and email(s)
      const ret = []
      if (this.value.value) {
        // console.debug('value type = ' + typeof this.value.value)
        let splitVal
        if (typeof this.value.value === 'string') {
          splitVal = this.value.value.split(';')
        } else {
          splitVal = this.value.value
        }
        for (let i = 0; i < splitVal.length; i++) {
          if (contactRegex.test(splitVal[i]) === true) {
            const contactGroup = contactRegex.exec(splitVal[i])
            ret.push({ name: contactGroup[1].trim(), email: contactGroup[2] })
          } else ret.push({ name: splitVal[i].trim(), email: null })
        }
      }
      if (ret.length === 0) this.colType = null // Fall back to standard field
      return ret
    },
    getExternalLinks () {
      // Return external links
      const linkLabels = this.params.app.sodarContext.external_link_labels
      const ret = []
      if (!Array.isArray(this.value.value)) {
        this.value.value = [this.value.value]
      }
      for (let i = 0; i < this.value.value.length; i++) {
        const extId = this.value.value[i]
        const splitId = extId.split(':')
        if (splitId.length > 1 && splitId[1] != null) {
          const key = splitId[0]
          let label = key
          let url = null
          if (key in linkLabels) {
            label = linkLabels[key].label
            if ('url' in linkLabels[key] &&
                linkLabels[key].url !== null &&
                linkLabels[key].url.includes(extLinkId)) {
              url = linkLabels[key].url.replace(
                extLinkId, encodeURIComponent(splitId[1]))
            }
          }
          ret.push({ label: label, id: splitId[1], url: url })
        }
      }
      return { extIds: ret }
    },
    getFileLink () {
      // Get file link
      let url = null
      if ('link' in this.value) url = this.value.link
      return {
        value: this.value.value,
        url: url
      }
    },
    getEmptyFileClass () {
      if (!this.params.app.editMode) return 'text-muted'
      return ''
    },
    getTooltip () {
      if ('tooltip' in this.value) return this.value.tooltip
      return ''
    },
    testSimpleLink () {
      const ret = simpleLinkRegex.test(this.value.value)
      if (ret === true) this.simpleLink = this.value.value.match(simpleLinkRegex)
      return ret
    }
  },
  beforeMount () {
    this.value = this.params.value
    if (this.value && 'newInit' in this.value) this.newInit = this.value.newInit
    if (this.value && 'newRow' in this.value) this.newRow = this.value.newRow

    if (
      this.value &&
      this.value.value &&
      this.value.value.length > 0
    ) {
      // Handle special column type
      this.colType = this.params.colType

      // Enable/disable hover overflow
      this.enableHover = (this.params.enableHover === undefined)
        ? true
        : this.params.enableHover

      if (this.colType === 'ONTOLOGY') {
        this.headerName = this.getHeaderName()
      } else if (this.colType === 'CONTACT') {
        this.renderData = this.getContact()
      } else if (this.colType === 'EXTERNAL_LINKS') {
        this.renderData = this.getExternalLinks()
      } else if (this.colType === 'LINK_FILE') {
        this.renderData = this.getFileLink()
      }

      // Special case: List of strings
      if (Array.isArray(this.value.value) &&
          !(typeof this.value.value[0] === 'object')) {
        this.displayValue = this.value.value.join('; ')
        this.useDisplayValue = true
      }
    } else if (this.newInit) {
      this.value.value = ''
    } else {
      this.value = { value: '-' }
    }
  }
})
</script>

<style scoped>
</style>
