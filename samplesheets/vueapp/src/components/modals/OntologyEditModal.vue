<template>
  <b-modal
      id="sodar-ss-ontology-edit-modal" ref="ontologyEditModal"
      centered no-fade hide-footer
      size="xl"
      :static="true"
      no-close-on-backdrop
      no-close-on-esc>
    <template slot="modal-header">
      <div class="w-100">
        <h5 class="modal-title text-nowrap" id="sodar-ss-ontology-title">
          {{ getTitle() }}
          <span class="pull-right">
            <b-input-group class="sodar-header-input-group">
              <b-input-group-prepend>
                <b-button
                    class="sodar-list-btn"
                    title="Copy terms to clipboard"
                    v-clipboard:copy="getCopyData()"
                    v-clipboard:success="onCopySuccess"
                    v-clipboard:error="onCopyError"
                    :disabled="!enableCopy()"
                    v-b-tooltip.hover>
                  <i class="iconify" data-icon="mdi:clipboard-text-multiple"></i>
                </b-button>
              </b-input-group-prepend>
              <b-form-input
                  id="sodar-ss-ontology-input-paste"
                  v-model="pasteData"
                  @input="onPasteInput"
                  placeholder="Paste"
                  title="Paste copied terms here"
                  v-b-tooltip.hover>
              </b-form-input>
            </b-input-group>
          </span>
          <span class="pull-right text-nowrap text-right">
            <notify-badge ref="notifyBadge"></notify-badge>
          </span>
        </h5>
      </div>
    </template>
    <div id="sodar-ss-ontology-modal-content">
      <div class="w-100" id="sodar-ss-ontology-modal-ui">
        <!-- Ontology term search -->
        <div v-if="searchOntologies && searchOntologies.length > 0">
          <b-row>
            <b-col class="col-md-3 pl-0 pr-2">
              <b-input
                  id="sodar-ss-ontology-input-search"
                  v-model="searchValue"
                  placeholder="Search for term"
                  @update="onSearchUpdate()"
                  :disabled="!enableSearch()">
              </b-input>
            </b-col>
            <b-col class="col-md-2 px-0">
              <b-form-select
                  v-model="queryOntologyLimit"
                  id="sodar-ss-ontology-select-limit"
                  @change="onSearchParamUpdate()"
                  :disabled="!enableSearch() || searchOntologies.length === 1"
                  :select-size="1">
                <b-form-select-option
                    v-if="searchOntologies.length > 1"
                    :value="null">
                  {{ getLimitLabel() }}
                </b-form-select-option>
                <b-form-select-option
                    v-for="(o, oIdx) in searchOntologies"
                    :key="oIdx"
                    :value="o">
                  {{ o }}
                </b-form-select-option>
              </b-form-select>
            </b-col>
            <b-col class="col-md-3 pl-3 text-nowrap">
              <div id="sodar-ss-ontology-order">
                <b-form-checkbox
                    v-model="queryOntologyOrder"
                    @change="onSearchParamUpdate()"
                    id="sodar-ss-ontology-order-check"
                    :disabled="queryOntologyLimit !== null">
                  Sort by ontology
                </b-form-checkbox>
              </div>
            </b-col>
            <b-col class="col-md-4 px-0 align-right align-middle">
              <img v-if="querying" src="/icons/mdi/loading.svg?color=%236c757d"
                   class="mt-3 pull-right spin" />
            </b-col>
          </b-row>
          <!-- TODO: Refactor as above -->
          <b-select
              id="sodar-ss-ontology-select-term"
              :disabled="!enableSearch()"
              :select-size="8">
            <option
                v-for="(term, termIdx) in termOptions"
                :key="termIdx"
                @dblclick="onTermOptionClick(term)">
              [{{ term.term_id }}] {{ term.name }} <span v-if="term.is_obsolete">&lt;OBSOLETE&gt;</span>
            </option>
          </b-select>
        </div>
        <div v-else
             class="alert alert-warning"
             id="sodar-ss-ontology-no-imports">
          No valid imported ontologies for this column found! Only manual
          ontology value entry is available. Ontologies can be imported using
          the <code>ontologyaccess</code> app.
        </div>
        <div
            v-if="responseDetail"
            :class="'alert alert-' + responseDetailType + ' sodar-ss-ontology-alert'">
          {{ responseDetail }}
        </div>
        <div
            v-else-if="!enableInsert()"
            class="alert alert-warning sodar-ss-ontology-alert"
            id="sodar-ss-ontology-no-list">
          Multiple terms not allowed in this column, current entry will be
          overwritten.
        </div>
        <div v-else id="sodar-ss-alert-placeholder"></div>
        <!-- List of current values and manual entry -->
        <table class="table sodar-card-table" id="sodar-ss-ontology-term-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Ontology</th>
              <th>Accession</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(term, termIdx) in value"
                :key="termIdx"
                class="sodar-ss-ontology-term-item">
              <!-- Normal term display -->
              <td v-if="!term.editing"
                  :class="getTermNameClass(term)">
                {{ term.name }}
                <i v-if="term.obsolete"
                   class="iconify"
                   data-icon="mdi:alert"
                   title="This term is obsolete!"
                   v-b-tooltip.hover.d300>
                </i>
                <i v-else-if="term.unknown"
                   class="iconify"
                   data-icon="mdi:alert"
                   title="Term name not found in given ontologies!"
                   v-b-tooltip.hover.d300>
                </i>
              </td>
              <td v-if="!term.editing"
                  :class="getOntologyNameClass(term.ontology_name)">
                {{ term.ontology_name }}
                <i v-if="!term.ontology_name"
                   class="iconify"
                   data-icon="mdi:alert"
                   title="No ontology name given!"
                   v-b-tooltip.hover.d300>
                </i>
                <i v-else-if="!sodarOntologies ||
                         !(term.ontology_name in sodarOntologies)"
                   class="iconify"
                   data-icon="mdi:alert"
                   title="Ontology not found in SODAR! Please ask for an
                          administrator to import the ontology for term and
                          URL lookup."
                   v-b-tooltip.hover.d300>
                </i>
              </td>
              <td v-if="!term.editing">
                <div class="sodar-ss-ontology-url">
                  <a :href="term.accession" target="_blank">{{ term.accession }}</a>
                </div>
              </td>
              <!-- Editing display -->
              <td v-if="term.editing">
                <b-input
                    class="sodar-ss-ontology-input-row"
                    v-model="value[termIdx].name">
                </b-input>
              </td>
              <td v-if="term.editing">
                <b-input
                    v-model="value[termIdx].ontology_name"
                    :class="getOntologyNameInputClass(true)"
                    @input="onOntologyNameInput($event, true)">
                </b-input>
              </td>
              <td v-if="term.editing">
                <b-input
                    class="sodar-ss-ontology-input-row"
                    v-model="value[termIdx].accession">
                </b-input>
              </td>
              <!-- Buttons -->
              <td class="text-right">
                <b-button
                    v-if="editConfig && editConfig.allow_list"
                    variant="primary"
                    class="sodar-list-btn sodar-ss-row-btn
                           sodar-ss-btn-up mr-1"
                    title="Move term backwards in list"
                    @click="onTermMoveClick(termIdx, true)"
                    :disabled="!enableMove(termIdx, true)"
                    v-b-tooltip.hover.d300>
                  <i class="iconify" data-icon="mdi:arrow-up-thick"></i>
                </b-button>
                <b-button
                    v-if="editConfig && editConfig.allow_list"
                    variant="primary"
                    class="sodar-list-btn sodar-ss-row-btn
                           sodar-ss-btn-down mr-1"
                    title="Move term forward in list"
                    @click="onTermMoveClick(termIdx, false)"
                    :disabled="!enableMove(termIdx, false)"
                    v-b-tooltip.hover.d300>
                  <i class="iconify" data-icon="mdi:arrow-down-thick"></i>
                </b-button>
                <b-button
                    v-if="term.editing"
                    variant="primary"
                    class="sodar-list-btn sodar-ss-row-btn
                           sodar-ss-btn-stop mr-1"
                    title="Stop editing term"
                    @click="onTermEditClick(termIdx)"
                    :disabled="!enableEditSave(termIdx) || !editDataValid"
                    v-b-tooltip.hover.d300>
                  <img :src="'/icons/mdi/check-bold.svg?color=%23fff'" class="mb-1" />
                </b-button>
                <b-button
                    v-else
                    variant="primary"
                    class="sodar-list-btn sodar-ss-row-btn
                           sodar-ss-btn-edit mr-1"
                    title="Edit term"
                    @click="onTermEditClick(termIdx)"
                    :disabled="!enableEdit()"
                    v-b-tooltip.hover.d300>
                  <img :src="'/icons/mdi/lead-pencil.svg?color=%23fff'" class="mb-1" />
                </b-button>
                <b-button
                    variant="danger"
                    class="sodar-list-btn sodar-ss-row-btn
                           sodar-ss-btn-delete"
                    title="Delete term"
                    @click="onTermDeleteClick(termIdx)"
                    :disabled="!enableDelete(termIdx)"
                    v-b-tooltip.hover.d300>
                  <i class="iconify" data-icon="mdi:close-thick"></i>
                </b-button>
              </td>
            </tr>
            <tr v-if="enableInsert() && insertData"
                id="sodar-ss-ontology-free-row">
              <td>
                <b-input
                    class="sodar-ss-ontology-input-row"
                    v-model.trim="insertData.name"
                    :disabled="!enableInsertInputs()">
                </b-input>
              </td>
              <td>
                <b-input
                    v-model.trim="insertData.ontologyName"
                    :class="getOntologyNameInputClass(false)"
                    @input="onOntologyNameInput($event, false)"
                    :disabled="!enableInsertInputs()">
                </b-input>
              </td>
              <td>
                <b-input
                    class="sodar-ss-ontology-input-row"
                    v-model.trim="insertData.accession"
                    :disabled="!enableInsertInputs()">
                </b-input>
              </td>
              <td class="text-right">
                <b-button
                    variant="primary"
                    class="sodar-list-btn sodar-ss-row-btn"
                    id="sodar-ss-btn-insert"
                    title="Insert ontology term"
                    @click="onTermInsertClick()"
                    :disabled="!enableInsertSave() || !insertDataValid"
                    v-b-tooltip.hover.d300>
                  <i class="iconify" data-icon="mdi:plus-thick"></i>
                </b-button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    <div>
      <b-button-group
          class="pull-right"
          id="sodar-ss-ontology-btn-group">
        <b-button
            variant="secondary"
            id="sodar-ss-btn-cancel"
            @click="hideModal(false)">
          <i class="iconify" data-icon="mdi:close-thick"></i> Cancel
        </b-button>
        <b-button
            variant="primary"
            id="sodar-ss-btn-update"
            @click="hideModal(true)"
            :disabled="!enableUpdate()"
            ref="updateBtn">
          <i class="iconify" data-icon="mdi:check-bold"></i> Update
        </b-button>
      </b-button-group>
    </div>
  </b-modal>
</template>

<script>

import NotifyBadge from '../NotifyBadge.vue'
const minSearchLength = 4

export default {
  name: 'OntologyEditModal',
  components: { NotifyBadge },
  props: ['unsavedDataCb'],
  data () {
    return {
      value: null,
      nodeName: null,
      headerName: null,
      editConfig: null,
      columnOntologies: null,
      sodarOntologies: null,
      searchOntologies: null,
      finishEditCb: null,
      pasteData: '',
      querying: false,
      queryOntologyLimit: null,
      queryOntologyOrder: false,
      colOntologyLimit: false,
      searchValue: null,
      prevSearchValue: null,
      termOptions: null,
      responseDetail: null,
      responseDetailType: null,
      insertData: null,
      insertDataValid: null,
      editDataValid: null,
      editIdx: null,
      editTermValue: null,
      updated: false,
      refreshingTerms: false
    }
  },
  methods: {
    /* Event handling ------------------------------------------------------- */
    onCopySuccess () {
      this.$refs.notifyBadge.show('Terms Copied', 'success', 1000)
    },
    onCopyError (event) {
      this.$refs.notifyBadge.show('Copy Error', 'danger', 2000)
      console.log('Copy Error: ' + event)
    },
    onPasteInput (val) {
      let pasteValue
      let pasteOk = true
      try {
        pasteValue = JSON.parse(val)
      } catch (error) {
        this.$refs.notifyBadge.show('Invalid JSON', 'danger', 1000)
        pasteOk = false
      }
      if (pasteValue && this.editConfig.ontologies.length > 0) {
        for (let i = 0; i < pasteValue.length; i++) {
          if (!(this.editConfig.ontologies.includes(
            pasteValue[i].ontology_name))) {
            this.$refs.notifyBadge.show('Invalid Ontology', 'danger', 1000)
            console.error(
              'Invalid ontology for column: ' + pasteValue[i].ontology_name)
            pasteOk = false
          }
        }
      }
      if (pasteValue && !this.editConfig.allow_list && pasteValue.length > 1) {
        this.$refs.notifyBadge.show('List Disllowed', 'danger', 1000)
        pasteOk = false
      }
      if (pasteOk) {
        this.value = pasteValue
        this.$refs.notifyBadge.show('Term Pasted', 'success', 1000)
        this.setUpdateStatus(true)
      }
      this.$nextTick(() => { this.pasteData = '' })
    },
    onSearchUpdate () {
      this.searchValue = this.searchValue.trim()
      if (!this.querying &&
          this.searchValue.length >= minSearchLength &&
          this.searchValue !== this.prevSearchValue) {
        // Set initial delay if typing
        // TODO: Recognize copy paste instead of typing and eliminate delay
        let delay = 350
        if (!this.prevSearchValue) delay = 750
        this.submitTermQuery(delay)
      } else if (this.searchValue.length < minSearchLength) {
        this.prevSearchValue = null
        this.termOptions = []
      }
    },
    onSearchParamUpdate () {
      // Resubmit query if ontology limit or sorting is changed
      if (this.searchValue.length >= minSearchLength) {
        this.submitTermQuery(0)
      }
    },
    onTermOptionClick (term) {
      if (term && this.addTerm(
        term.name, term.ontology_name, term.accession, term.is_obsolete)) {
        this.setUpdateStatus(true)
      }
    },
    onOntologyNameInput (event, edit) {
      let valid = true
      if (this.colOntologyLimit &&
          !this.editConfig.ontologies.includes(event.toUpperCase())) {
        valid = false
      }
      if (edit) this.editDataValid = valid
      else this.insertDataValid = valid
    },
    onTermInsertClick () {
      if (
        this.addTerm(
          this.insertData.name,
          this.insertData.ontologyName,
          this.insertData.accession,
          false)) {
        this.setUpdateStatus(true)
        this.clearInsertData()
        this.insertDataValid = true
      }
      this.$nextTick(() => {
        this.$root.$emit('bv::hide::tooltip')
      })
    },
    onTermMoveClick (idx, up) {
      let otherIdx
      if (up) otherIdx = idx - 1
      else otherIdx = idx + 1
      const tmpVal = Object.assign(this.value[idx])
      this.value[idx] = this.value[otherIdx]
      this.value[otherIdx] = tmpVal
      this.setUpdateStatus(true)
      this.$forceUpdate()
    },
    onTermEditClick (idx) {
      if (this.editIdx === null) {
        this.editTermValue = JSON.stringify(this.value[idx])
        this.value[idx].editing = true
        this.editIdx = idx
      } else {
        this.value[idx].editing = false
        this.editIdx = null
        this.value[idx].name = this.value[idx].name.trim()
        this.value[idx].ontology_name = this.value[idx].ontology_name.trim().toUpperCase()
        this.value[idx].accession = this.value[idx].accession.trim()
        // TODO: Query for new value and set/unset unknown accordingly
        if ('unknown' in this.value[idx]) delete this.value[idx].unknown
        if (JSON.stringify(this.value[idx]) !== this.editTermValue) {
          this.setUpdateStatus(true)
        }
        this.editTermValue = null
      }
      this.editDataValid = true
    },
    onTermDeleteClick (idx) {
      this.value.splice(idx, 1)
      this.setUpdateStatus(true)
      this.editDataValid = true
      this.editIdx = null
      this.editTermValue = null
    },
    /* Helpers -------------------------------------------------------------- */
    getTitle () {
      let title = ''
      if (this.nodeName) title = this.nodeName + ': '
      title += this.headerName
      return title
    },
    enableCopy () {
      return this.value && this.value.length > 0
    },
    getCopyData () {
      if (!this.value || this.value.length === 0) return ''
      const copyVal = []
      for (let i = 0; i < this.value.length; i++) {
        const copyTerm = Object.assign({
          name: this.value[i].name,
          ontology_name: this.value[i].ontology_name,
          accession: this.value[i].accession
        })
        copyVal.push(copyTerm)
      }
      return JSON.stringify(copyVal)
    },
    enableSearch () {
      return this.editIdx === null
    },
    enableUpdate () {
      return this.editIdx === null && this.updated
    },
    getTermNameClass (term) {
      if (term.obsolete || term.unknown) return 'text-danger'
      return ''
    },
    getOntologyNameClass (name) {
      if (!name ||
          !this.sodarOntologies ||
          !(name.toUpperCase() in this.sodarOntologies)) {
        return 'text-danger'
      }
      return ''
    },
    getOntologyNameInputClass (edit) {
      let cls = 'sodar-ss-ontology-input-row'
      if ((edit && !this.editDataValid) || (!edit && !this.insertDataValid)) {
        cls += ' text-danger'
      }
      return cls
    },
    getLimitLabel () {
      if (this.colOntologyLimit) return 'Allowed ontologies'
      return 'All ontologies'
    },
    enableMove (idx, up) {
      return (
        !this.refreshingTerms &&
        this.editIdx === null &&
        this.value.length > 1 &&
        ((idx > 0 && up) ||
        (idx !== this.value.length - 1 && !up)))
    },
    enableEdit () {
      return !this.refreshingTerms && this.editIdx === null
    },
    enableEditSave (idx) {
      if (!this.value || idx > this.value.length - 1) {
        return false
      } else if (!this.value[idx].name ||
          !this.value[idx].ontology_name ||
          !this.value[idx].accession) {
        return false
      } else {
        for (let i = 0; i < this.value.length; i++) {
          if (i !== idx && ((this.value[idx].name === this.value[i].name &&
              this.value[idx].ontology_name === this.value[i].ontology_name) ||
              this.value[idx].accession === this.value[i].accession)) {
            return false
          }
        }
      }
      return true
    },
    enableDelete (termIdx) {
      return (!this.refreshingTerms &&
        (this.editIdx === null || termIdx === this.editIdx))
    },
    enableInsert () {
      return this.editConfig &&
        (this.editConfig.allow_list || this.value.length === 0)
    },
    enableInsertInputs () {
      return this.editIdx === null
    },
    enableInsertSave () {
      if (this.refreshingTerms ||
          !this.insertData ||
          !this.insertData.name ||
          !this.insertData.ontologyName ||
          !this.insertData.accession) {
        return false
      } else if (this.insertData) {
        for (let i = 0; i < this.value.length; i++) {
          if ((this.insertData.name === this.value[i].name &&
              this.insertData.ontologyName === this.value[i].ontology_name) ||
              this.insertData.accession === this.value[i].accession) {
            return false
          }
        }
      }
      return true
    },
    getQueryUrl (searchValue) {
      // TODO: Should get root URL from backend and server
      // TODO: Probably some faster way in Javascript to build querystring?
      let url = '/ontology/ajax/obo/term/query?s=' +
        encodeURIComponent(searchValue)
      if (this.queryOntologyLimit) {
        url += '&o=' + encodeURIComponent(this.queryOntologyLimit)
      } else if (this.editConfig.ontologies.length > 0) {
        for (let i = 0; i < this.searchOntologies.length; i++) {
          url += '&o=' + encodeURIComponent(this.searchOntologies[i])
        }
      }
      if (!this.queryOntologyLimit && this.queryOntologyOrder) {
        url += '&order=1'
      }
      return url
    },
    submitTermQuery (delay) {
      if (delay === undefined) delay = 350
      this.querying = true

      setTimeout(() => {
        const searchValue = this.searchValue
        // console.log('Query for string: ' + searchValue) // DEBUG
        fetch(this.getQueryUrl(searchValue), {
          method: 'GET',
          credentials: 'same-origin',
          headers: {
            Accept: 'application/json',
            'Content-Type': 'application/json'
          }
        }).then(data => data.json())
          .then(data => {
            if ('detail' in data) {
              this.responseDetail = data.detail
              this.responseDetailType = data.detail_type || 'danger'
            } else {
              this.responseDetail = null
              this.responseDetailType = null
            }
            this.termOptions = data.terms

            // If typing was stopped while querying and value has changed..
            const currentValue = this.searchValue
            if (currentValue !== searchValue &&
                currentValue.length >= minSearchLength) {
              this.submitTermQuery()
            } else {
              this.prevSearchValue = searchValue
              this.querying = false
            }
          }).catch() // TODO: Handle errors
      }, delay) // Delay to avoid too many queries to server
    },
    addTerm (name, ontologyName, accession, obsolete) {
      // Insert OR replace term. Returns false if operation was cancelled.
      for (let i = 0; i < this.value.length; i++) {
        if (this.value[i].name === name &&
            this.value[i].ontology_name === ontologyName.toUpperCase()) {
          return false
        }
      }
      if (!this.enableInsert()) {
        this.value = [] // Clear and replace value
      }
      this.value.push({
        name: name,
        ontology_name: ontologyName.toUpperCase(),
        accession: accession,
        obsolete: obsolete // To be wiped out when returning data
      })
      return true
    },
    clearInsertData () {
      this.insertData = {
        name: null,
        ontologyName: null,
        accession: null
      }
    },
    setUpdateStatus (val) {
      this.updated = val
      this.unsavedDataCb(true) // Prevent navigation before saving
    },
    handleRefreshError (error) {
      console.log('Error refreshing terms: ' + error.detail)
      this.refreshingTerms = false
    },
    getInitialTermInfo () {
      let listUrl = '/ontology/ajax/obo/term/list?'
      for (let i = 0; i < this.value.length; i++) {
        if (i > 0) listUrl += '&'
        listUrl += 't=' + encodeURIComponent(this.value[i].name)
      }
      fetch(listUrl, {
        method: 'GET',
        credentials: 'same-origin',
        headers: {
          Accept: 'application/json',
          'Content-Type': 'application/json'
        }
      }).then(response => response.json())
        .then(response => {
          this.handleInitialTermResponse(response)
        }).catch(this.handleRefreshError)
    },
    handleInitialTermResponse (data) {
      for (let i = 0; i < this.value.length; i++) {
        if (!(data.terms.map(x => x.name.toLowerCase()).includes(
          this.value[i].name.toLowerCase()))) {
          this.value[i].unknown = true
        }
        for (let j = 0; j < data.terms.length; j++) {
          if (this.value[i].name.toLowerCase() === data.terms[j].name.toLowerCase() &&
              this.value[i].ontology_name === data.terms[j].ontology_name) {
            // console.log('Updating term ' + this.value[i].name) // DEBUG
            if (data.terms[j].is_obsolete) {
              this.value[i].obsolete = data.terms[j].is_obsolete
            }
            break
          }
        }
      }
      this.$forceUpdate()
      this.refreshingTerms = false
    },
    /* Modal showing and hiding --------------------------------------------- */
    showModal (params, finishEditCb) {
      // console.log(JSON.stringify(params))

      // Copy value into a local array
      if (Array.isArray(params.value)) {
        this.value = []
        for (let i = 0; i < params.value.length; i++) {
          this.value.push(Object.assign(params.value[i], { editing: false }))
        }
      } else this.value = [Object.assign(params.value, { editing: false })]

      // Clear empty value if it exists
      if (this.value.length === 1 && !this.value[0].name) this.value = []

      this.nodeName = params.nodeName
      this.headerName = params.headerName
      this.editConfig = params.editConfig
      this.sodarOntologies = params.sodarOntologies
      this.querying = false
      this.queryOntologyLimit = null
      this.queryOntologyOrder = false
      this.searchValue = ''
      this.prevSearchValue = ''
      this.termOptions = []
      this.responseDetail = null
      this.responseDetailType = null
      this.clearInsertData()
      this.editDataValid = true
      this.insertDataValid = true
      this.editIdx = null
      this.editTermValue = null
      this.updated = false
      this.refreshingTerms = true
      this.finishEditCb = finishEditCb

      // Set up ontologies available to the column
      const sodarOntologyKeys = Object.keys(this.sodarOntologies)
      if ('ontologies' in this.editConfig &&
          this.editConfig.ontologies.length > 0) {
        this.colOntologyLimit = true
        this.columnOntologies = this.editConfig.ontologies
      } else {
        this.colOntologyLimit = false
        this.columnOntologies = sodarOntologyKeys
      }
      this.searchOntologies = []
      for (let i = 0; i < this.columnOntologies.length; i++) {
        if (sodarOntologyKeys.includes(this.columnOntologies[i])) {
          this.searchOntologies.push(this.columnOntologies[i])
        }
      }
      if (this.searchOntologies.length === 1) {
        this.queryOntologyLimit = this.searchOntologies[0]
      }

      // Show modal
      this.$refs.ontologyEditModal.show()

      // Get full term data from database, update obsolete status
      if (this.value.length > 0) {
        this.getInitialTermInfo()
      } else {
        this.refreshingTerms = false
      }
    },
    hideModal (save) {
      let editValue = null
      if (save && this.updated) {
        editValue = this.value
        for (let i = 0; i < editValue.length; i++) {
          delete editValue[i].editing
          delete editValue[i].obsolete
          delete editValue[i].unknown
        }
      }
      this.finishEditCb(editValue)
      this.$refs.ontologyEditModal.hide()
    }
  }
}
</script>

<style scoped>

div#sodar-ss-ontology-modal-ui {
  min-height: 550px !important;
}

#sodar-ss-ontology-input-paste {
  width: 70px;
}

div#sodar-ss-ontology-order {
  white-space: nowrap !important;
  padding-top: 7px;
}

table#sodar-ss-ontology-term-table {
}

table#sodar-ss-ontology-term-table tbody tr td:not(:last-child) {
  padding-top: 14px; /* Hack for padding vs button */
}

table#sodar-ss-ontology-term-table tbody tr td:nth-child(1) {
  width: 450px;
}

table#sodar-ss-ontology-term-table tbody tr td:nth-child(2) {
  width: 150px;
}

table#sodar-ss-ontology-term-table tbody tr td:nth-child(3) {
  max-width: 275px;
}

table#sodar-ss-ontology-term-table tbody tr td:nth-child(4) {
  white-space: nowrap !important;
  width: 150px;
}

div.sodar-ss-ontology-url {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  word-wrap: anywhere;
  min-width: 75px;
}

tr#sodar-ss-ontology-free-row td {
  vertical-align: middle;
}

input.sodar-ss-ontology-input-row {
  height: 23px;
}

input#sodar-ss-ontology-input-search,
select#sodar-ss-ontology-select-limit,
select#sodar-ss-ontology-select-term {
  margin-bottom: 8px;
}

select#sodar-ss-ontology-select-term {
  height: 155px;
}

div.sodar-ss-ontology-alert {
  margin-bottom: 0;
}

div#sodar-ss-alert-placeholder {
  height: 50px;
}

tr#sodar-ss-ontology-free-row td:last-child {
    padding-top: 14px;
}

div#sodar-ss-ontology-btn-group {
  margin-top: 16px;
}

.sodar-ss-row-btn {
  padding-top: 1px !important;
  padding-left: 4px !important;
}

</style>
