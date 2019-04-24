<template>
  <span v-if="tableData">
    <div class="card">
      <div class="card-header">
        <h4>{{ tableData['schema']['title'] }}</h4>
      </div>
      <div class="card-body p-0">
        <table v-if="tableData['cols'].length > 0 &&
                    tableData['rows'].length > 0"
               class="table sodar-card-table sodar-ss-extra-table">
          <thead>
            <tr>
              <th v-for="(colItem, index) in tableData['cols']"
                  :key="index">
                {{ colItem.title }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(rowItem, index) in tableData['rows']"
                :key="index">
              <td v-for="(colItem, index) in tableData['cols']"
                  :key="index">
                <span v-if="colItem['type'] === 'label'">
                  {{ rowItem[colItem['field']]['value'] }}
                </span>
                <span v-else-if="colItem['type'] === 'irods_buttons'">
                  <irods-buttons
                      :irods-status="irodsStatus"
                      :irods-backend-enabled="irodsBackendEnabled"
                      :irods-webdav-url="irodsWebdavUrl"
                      :irodsPath="rowItem[colItem['field']]['path']"
                      :showFileList="false">
                  </irods-buttons>
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </span>
</template>

<script>
import IrodsButtons from './IrodsButtons.vue'

export default {
  name: 'ExtraContentTable',
  components: {
    IrodsButtons
  },
  props: [
    'app',
    'tableData',
    'irodsStatus',
    'irodsBackendEnabled',
    'irodsWebdavUrl'
  ]
}
</script>

<style scoped>

table.sodar-ss-extra-table thead tr th:first-child,
table.sodar-ss-extra-table tbody tr td:first-child {
  width: 100%;
}

</style>
