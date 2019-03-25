<template>
  <span>
    <div class="card">
      <div class="card-header">
        <h4>Investigation Details</h4>
      </div>
      <div class="card-body">
        <dl class="row pb-0">
          <dt class="col-md-3">Identifier</dt>
          <dd class="col-md-9">{{ app.sodarContext['investigation']['identifier'] }}</dd>
        </dl>
        <dl class="row pb-0">
          <dt class="col-md-3">Title</dt>
          <dd class="col-md-9">{{ app.sodarContext['investigation']['title'] }}</dd>
        </dl>
        <dl v-if="app.sodarContext['investigation']['description']"
            class="row pb-0">
          <dt class="col-md-3">Description</dt>
          <dd class="col-md-9">{{ app.sodarContext['investigation']['description'] }}</dd>
        </dl>
        <dl class="row pb-0">
          <dt class="col-md-3">iRODS Repository</dt>
          <dd class="col-md-9">
            <span v-if="app.sodarContext['irods_status']"
                  class="badge badge-pill badge-success">
              Available
            </span>
            <span v-else
                  class="badge badge-pill badge-danger">
              Not Created
            </span>
            <!-- iRODS stats badge here -->
          </dd>
        </dl>
        <span v-for="(data, key, index) in
                   app.sodarContext['investigation']['comments']"
            :key="index">
          <dl class="row pb-0">
            <dt class="col-md-3">{{ key }}</dt>
            <dd class="col-md-9">{{ data['value'] }}</dd>
          </dl>
        </span>
      </div>
    </div>

    <div v-for="(studyInfo, studyUuid, index) in app.sodarContext['studies']"
         :key="index"
         class="card">
      <div class="card-header">
        <h4>Study Details: {{ studyInfo['display_name'] }}</h4>
      </div>
      <div class="card-body">
        <dl class="row pb-0">
          <dt class="col-md-3">Title</dt>
          <dd class="col-md-9">{{ studyInfo['display_name']}}</dd>
        </dl>
        <dl v-if="studyInfo['description']"
            class="row pb-0">
          <dt class="col-md-3">Description</dt>
          <dd class="col-md-9">{{ studyInfo['description']}}</dd>
        </dl>
        <dl class="row pb-0">
          <dt class="col-md-3">Configuration</dt>
          <dd class="col-md-9">{{ studyInfo['configuration']}}</dd>
        </dl>
        <span v-for="(data, key, index) in studyInfo['comments']"
              :key="index">
          <dl v-if="data['value']"
              class="row pb-0">
            <dt class="col-md-3">{{ key }}</dt>
            <dd class="col-md-9">{{ data['value'] }}</dd>
          </dl>
        </span>
      </div>
    </div>

    <div class="card">
      <div class="card-header">
        <h4>Statistics</h4>
      </div>
      <div class="card-body p-0">
        <div class="table-responsive">
          <table class="table sodar-card-table">
            <thead>
              <tr>
                <th>Studies</th>
                <th>Assays</th>
                <th>Protocols</th>
                <th>Processes</th>
                <th>Sources</th>
                <th>Materials</th>
                <th>Samples</th>
                <th>Data&nbsp;Files</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>{{ app.sodarContext['sheet_stats']['study_count'] }}</td>
                <td>{{ app.sodarContext['sheet_stats']['assay_count'] }}</td>
                <td>{{ app.sodarContext['sheet_stats']['protocol_count'] }}</td>
                <td>{{ app.sodarContext['sheet_stats']['process_count'] }}</td>
                <td>{{ app.sodarContext['sheet_stats']['source_count'] }}</td>
                <td>{{ app.sodarContext['sheet_stats']['material_count'] }}</td>
                <td>{{ app.sodarContext['sheet_stats']['sample_count'] }}</td>
                <td>{{ app.sodarContext['sheet_stats']['data_count'] }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </span>
</template>

<script>
export default {
  name: 'Overview',
  props: [
    'app'
  ],
  methods: {
  }
}
</script>

<style scoped>
</style>
