<template>
  <span class="text-nowrap sodar-ss-study-shortcuts">
    <span v-for="(schemaItem, schemaId, index) in schema"
          :key="index">
      <b-button
         v-if="schemaItem.type === 'link'"
         variant="secondary"
         :class="getClasses()"
         :title="schemaItem.title"
         :disabled="getEnabledState(schemaId)"
         :href="value[schemaId].url">
       <i class="iconify" :data-icon="schemaItem.icon"></i>
     </b-button>
     <b-button
         v-else-if="schemaItem.type === 'modal'"
         variant="secondary"
         :class="getClasses() + ' sodar-ss-popup-list-btn'"
         :title="schemaItem.title"
         :disabled="getEnabledState(schemaId)"
         @click="onModalClick(schemaId)">
       <i class="iconify" :data-icon="schemaItem.icon"></i>
     </b-button>
   </span>
 </span>
</template>

<script>
import Vue from 'vue'

export default Vue.extend({
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
    getEnabledState (schemaId) {
      return 'enabled' in this.value[schemaId] &&
        this.value[schemaId].enabled === false
    },
    onModalClick (schemaId) {
      this.modalComponent.showModal(this.value[schemaId].query)
    }
  },
  beforeMount () {
    this.value = this.params.value
    this.schema = this.params.schema
    this.modalComponent = this.params.modalComponent
  }
})
</script>

<style scoped>
</style>
