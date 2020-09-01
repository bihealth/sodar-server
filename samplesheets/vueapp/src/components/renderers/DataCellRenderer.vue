<template>
  <div class="sodar-ss-data"
       :row-num="params.node.data.rowNum"
       :col-num="params.colDef.field.substring(3)"
       :row-id="params.node.id"
       @mouseover="onMouseOver"
       @mouseout="onMouseOut">
    <!-- Value with unit -->
    <span v-if="'unit' in value && value.unit">
      {{ value.value }} <span class="text-muted">{{ value.unit }}</span>
    </span>
    <!-- Ontology links -->
    <span v-else-if="colType === 'ONTOLOGY' &&
                     renderData &&
                     renderData.links.length > 0">
      <span v-if="headerName === 'hpo terms'">
        <b-button
            class="btn sodar-list-btn mr-1"
            title="Copy HPO term IDs to clipboard"
            @click="onCopyHpoTerms"
            v-b-tooltip.hover.d300>
          <i class="fa fa-clipboard"></i>
        </b-button>
      </span>
      <span v-for="(link, index) in links = renderData.links" :key="index">
        <a :href="link.url"
           :title="getTooltip()"
           v-b-tooltip.hover.d300
           target="_blank">{{ link.value }}</a><span v-if="index + 1 < links.length">; </span>
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
export default Vue.extend(
  {
    data: function () {
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

        for (let i = 0; i < this.renderData.links.length; i++) {
          const link = this.renderData.links[i]
          const splitUrl = link.url.split('/')
          hpoIds.push(splitUrl[splitUrl.length - 1])
        }

        this.$copyText(hpoIds.join(';'))
        this.params.app.showNotification('Copied', 'success', 1000)
      },
      /* Helpers ------------------------------------------------------------ */
      getHeaderName () {
        // Get header name and place in this.headerName
        return this.params.colDef.headerName.toLowerCase()
      },
      getOntologyLinks () {
        // Return one or more ontology links for field
        const links = []

        if (Array.isArray(this.value.value)) {
          for (let i = 0; i < this.value.value.length; i++) {
            links.push({
              value: this.value.value[i].name,
              url: this.value.value[i].accession // ,
              // ontologyName: this.value.value[i]['ontology_name'] // TODO: Use this?
            })
          }
        } else if (this.value.value.indexOf(';') !== -1 &&
            'link' in this.value &&
            this.value.link.indexOf(';') !== -1) { // Legacy altamISA implementation
          const values = this.value.value.split(';')
          const urls = this.value.link.split(';')

          for (let i = 0; i < values.length; i++) {
            links.push({ value: values[i], url: urls[i] })
          }
        } else if ('link' in this.value) {
          links.push({ value: this.value.value, url: this.value.link })
        }
        return { links: links }
      },
      getContact () {
        // Return contact name and email
        const contactRegex = /(.+?)(?:[<[])(.+?)(?=[>\]])/

        if (contactRegex.test(this.value.value) === true) {
          const contactGroup = contactRegex.exec(this.value.value)
          return { name: contactGroup[1], email: contactGroup[2] }
        } else {
          this.colType = null // Fall back to standard field
        }
      },
      getExternalLinks () {
        // Return external links
        const linkLabels = this.params.context
          .componentParent.sodarContext.external_link_labels
        const ret = []

        if (!Array.isArray(this.value.value)) {
          this.value.value = [this.value.value]
        }

        for (let i = 0; i < this.value.value.length; i++) {
          const extId = this.value.value[i]
          const splitId = extId.split(':')

          if (splitId.length > 1 && splitId[1] != null) {
            let key = splitId[0]
            if (key in linkLabels) {
              key = linkLabels[key]
            }
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
        if (!this.params.app.editMode) {
          return 'text-muted'
        }
      },
      getTooltip () {
        if ('tooltip' in this.value) {
          return this.value.tooltip
        }
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
        this.colType = this.params.value.colType

        // Enable/disable hover overflow
        this.enableHover = (this.params.enableHover === undefined)
          ? true : this.params.enableHover

        if (this.colType === 'ONTOLOGY') {
          this.headerName = this.getHeaderName()
          this.renderData = this.getOntologyLinks()
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
        this.value.value = '' // TODO: Simplify?
      } else {
        this.value = { value: '-' }
      }
    }
  }
)
</script>

<style scoped>
</style>
