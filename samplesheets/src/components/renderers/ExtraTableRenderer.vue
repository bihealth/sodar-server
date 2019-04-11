<template>
  <div v-if="colType === 'label'">
    {{ value }}
  </div>
  <div v-else-if="colType === 'links'">
    <span v-for="(link, index) in value['links']"
          :key="index"
          class="mr-3">
      <a :href="link['url']">{{ link['label'] }}</a>
    </span>
  </div>
  <div v-else>
    -
  </div>
</template>

<script>
import Vue from 'vue'
export default Vue.extend(
  {
    data: function () {
      return {
        value: null,
        colType: null
      }
    },
    methods: {
    },
    beforeMount () {
      this.colType = this.params.colType
      this.value = this.params.value
    }
  }
)
</script>

<style scoped>
</style>
