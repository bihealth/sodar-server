<template>
  <div class="sodar-ss-data"
       @mouseover="onMouseOver"
       @mouseout="onMouseOut">
    <!-- Plain/empty value -->
    <span v-if="!colType">
      {{ value }}
    </span>
    <!-- Value with unit -->
    <span v-else-if="colType === 'UNIT'">
      {{ value }} <span v-if="meta && meta.unit" class="text-muted">{{ meta.unit }}</span>
    </span>
    <!-- Ontology links -->
    <span v-else-if="colType === 'ONTOLOGY'">
      <!-- TODO: File link -->
      <span v-for="(link, index) in links = renderData.links" :key="index">
        <a :href="link.url"
           :title="meta.tooltip"
           v-b-tooltip.hover
           target="_blank">{{ link.value }}</a><span v-if="index + 1 < links.length">, </span>
      </span>
    </span>
    <!-- Contacts with email -->
    <span v-else-if="colType === 'CONTACT'">
      <a :href="'mailto:' + renderData.email">{{ renderData.name }}</a>
    </span>
    <!-- External links -->
    <span v-else-if="colType === 'EXTERNAL_LINKS'">
      <span v-for="(idRef, index) in renderData.extIds"
            class="badge-group"
            :key="index"
            v-b-tooltip.hover
            :title="idRef.key">
        <span class="badge badge-secondary">ID</span><span class="badge badge-info">{{ idRef.id }}</span>
      </span>
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
        // headerName: null,
        meta: null,
        colType: null,
        renderData: null
      }
    },
    methods: {
      onMouseOver (event) {
        if (event.currentTarget.scrollWidth > event.currentTarget.clientWidth) {
          event.currentTarget.className += ' sodar-ss-data-hover'
        }
      },

      onMouseOut (event) {
        event.currentTarget.className = 'sodar-ss-data'
      },

      // Update this.meta
      getMeta () {
        if (this.params.colMeta && !this.meta) {
          this.meta = this.params.colMeta[this.params.node.data.rowNum - 1]
        }
      },

      // Return one or more ontology links for field as HTML
      getOntologyLinks () {
        this.getMeta()
        let links = []

        if (this.value.indexOf(';') !== -1 &&
            this.meta.link.indexOf(';') !== -1) {
          let values = this.value.split(';')
          let urls = this.meta.link.split(';')

          for (let i = 0; i < values.length; i++) {
            links.push({value: values[i], url: urls[i]})
          }
        } else {
          links.push({value: this.value, url: this.meta.link})
        }
        return {'links': links}
      },

      // Return contact name and email
      getContact () {
        this.getMeta()
        let contactRegex = /(.+?)(?:[<[])(.+?)(?=[>\]])/

        if (contactRegex.test(this.value) === true) {
          let contactGroup = contactRegex.exec(this.value)
          return {name: contactGroup[1], email: contactGroup[2]}
        }
      },

      // Return external links
      getExternalLinks () {
        let linkLabels = this.params.context
          .componentParent.sodarContext['external_link_labels']
        let ret = []
        let extIds = this.value.split(';')

        for (let i = 0; i < extIds.length; i++) {
          let extId = extIds[i]
          let splitId = extId.split(':')

          if (splitId.length > 1 && splitId[1] != null) {
            let key = splitId[0]
            if (key in linkLabels) {
              key = linkLabels[key]
            }
            ret.push({'key': key, 'id': splitId[1]})
          }
        }

        return {'extIds': ret}
      }
    },
    beforeMount () {
      if (this.params.value && this.params.value.length > 0) {
        this.value = this.params.value
        // this.headerName = this.params.colDef.headerName.toLowerCase()

        // Handle special column type
        this.colType = this.params.colType

        if (this.colType === 'UNIT') {
          this.getMeta()
        } else if (this.colType === 'ONTOLOGY') {
          this.renderData = this.getOntologyLinks()
        } else if (this.colType === 'CONTACT') {
          this.renderData = this.getContact()
        } else if (this.colType === 'EXTERNAL_LINKS') {
          this.renderData = this.getExternalLinks()
        }
      } else {
        this.value = '-'
      }
    }
  }
)
</script>

<style scoped>

div.sodar-ss-data {
  width: 100%;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  padding-right: 3px;
  border: 1px solid transparent;
}

div.sodar-ss-data-hover {
  z-index: 1100;
  width: auto;
  position: fixed;
  background-color: #ffffe0;
  border: 1px solid #dfdfdf;
  box-shadow: 0 3px 3px -3px #909090;
}

</style>
