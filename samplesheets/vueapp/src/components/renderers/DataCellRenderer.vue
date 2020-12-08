<template>
  <div class="sodar-ss-data"
       :data-col-num="params.colDef.field.substring(3)"
       :data-row-id="params.node.id"
       @mouseover="onMouseOver"
       @mouseout="onMouseOut">
    <!-- Value with unit -->
    <span v-if="'unit' in value && value.unit">
      {{ value.value }} <span class="text-muted">{{ value.unit }}</span>
    </span>
    <!-- Ontology term(s) -->
    <span v-else-if="colType === 'ONTOLOGY' && value.value.length > 0">
      <span v-if="!params.app.editMode && headerName === 'hpo terms'">
        <b-button
            class="btn sodar-list-btn mr-1 sodar-ss-hpo-copy-btn"
            title="Copy HPO term IDs to clipboard"
            @click="onCopyHpoTerms"
            v-b-tooltip.hover.d300>
          <i class="fa fa-clipboard"></i>
        </b-button>
      </span>
      <span v-for="(term, termIndex) in value.value" :key="termIndex">
        <span v-if="!params.app.editMode">
          <a :href="term.accession"
             :title="term.ontology_name"
             v-b-tooltip.hover.d300
             target="_blank">{{ term.name }}</a><span v-if="termIndex + 1 < value.value.length">; </span>
        </span>
        <span v-else>
          {{ term.name }}<span v-if="termIndex + 1 < value.value.length">; </span>
        </span>
      </span>
    </span>
    <!-- Contacts with email -->
    <span v-else-if="colType === 'CONTACT' && renderData">
      <a :href="'mailto:' + renderData.email">{{ renderData.name }}</a>
    </span>
    <!-- External links -->
    <span v-else-if="colType === 'EXTERNAL_LINKS' && renderData">
      <span v-for="(idRef, index) in renderData.extIds"
            class="badge-group"
            :key="index"
            v-b-tooltip.hover.d300
            :title="idRef.key">
        <span class="badge badge-secondary">ID</span><span class="badge badge-info">{{ idRef.id }}</span>
      </span>
    </span>
    <!-- File link -->
    <span v-else-if="colType === 'LINK_FILE' && renderData">
      <span v-if="renderData.url">
        <a :href="renderData.url"
           :title="getTooltip()"
           v-b-tooltip.hover.d300
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
    <!-- Plain/numeric/empty/undetected value -->
    <span v-else>
      {{ value.value }}
    </span>
  </div>
</template>

<script>
import Vue from 'vue'

const contactRegex = /(.+?)(?:[<[])(.+?)(?=[>\]])/

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
      newRow: false
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
      // Return contact name and email
      if (contactRegex.test(this.value.value) === true) {
        const contactGroup = contactRegex.exec(this.value.value)
        return { name: contactGroup[1], email: contactGroup[2] }
      } else this.colType = null // Fall back to standard field
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
          let key = splitId[0]
          if (key in linkLabels) key = linkLabels[key]
          ret.push({ key: key, id: splitId[1] })
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
        ? true : this.params.enableHover

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
