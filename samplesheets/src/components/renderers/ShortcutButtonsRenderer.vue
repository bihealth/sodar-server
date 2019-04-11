<template>
  <span class="text-nowrap">
   <span v-for="(schemaItem, schemaId, index) in schema"
         :key="index">
     <b-button
        v-if="schemaItem['type'] === 'link'"
        variant="secondary"
        :class="getClasses()"
        :title="schemaItem['title']"
        :disabled="setDisabledState()"
        :href="value[schemaId]['url']"
        v-b-tooltip.hover>
      <i :class="'fa ' + schemaItem['icon']"></i>
    </b-button>
    <b-button
        v-else-if="schemaItem['type'] === 'modal'"
        variant="secondary"
        :class="getClasses() + ' sodar-vue-popup-list-btn'"
        :title="schemaItem['title']"
        :disabled="setDisabledState()"
        @click="onModalClick(schemaId)"
        v-b-tooltip.hover>
      <i :class="'fa ' + schemaItem['icon']"></i>
    </b-button>
   </span>
 </span>
</template>

<script>
import Vue from 'vue'

export default Vue.extend(
  {
    data () {
      return {
        value: null,
        schema: null,
        modalComponent: null
      }
    },
    methods: {
      getClasses () {
        return 'sodar-list-btn sodar-ss-irods-btn mr-1'
      },
      setDisabledState () {
        // TODO
      },
      onModalClick (schemaId) {
        this.modalComponent.getLinks(this.value[schemaId]['query'])
      }
    },
    beforeMount () {
      this.value = this.params.value
      this.schema = this.params.schema
      this.modalComponent = this.params.modalComponent
    }
  }
)
</script>

<style scoped>
</style>
