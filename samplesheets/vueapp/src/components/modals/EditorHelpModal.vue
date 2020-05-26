<template>
  <b-modal id="sodar-vue-editor-help-modal" ref="editorHelpModal"
           centered no-fade hide-footer
           size="xl"
           title="Sample Sheet Editor Help">

    <!-- Object list -->
    <div id="sodar-vue-irods-modal-content">
      <p>
        The sample sheet editor is under incremental development. Certain
        features are available, while others will be enabled later. Bugs and
        unannounced UI changes are possible. Below you can find the list of
        currently implemented and upcoming features. Make sure to check back
        once a new SODAR version is deployed.
      </p>
      <h5 class="text-success font-weight-bold">Available Features</h5>
      <ul>
        <li>Editing of columns with simple values (text, integer, double, select)</li>
        <li>Renaming materials and processes</li>
        <li>Saving, browsing and restoring sample sheet versions</li>
        <li>Configuring columns for editing (requires owner, delegate or superuser permissions</li>
        <li>Unit support</li>
        <li>Custom regex, optional integer range, automatic filling of default value</li>
        <li>Clipboard copy/paste of column configuration</li>
      </ul>
      <h5 class="text-danger font-weight-bold">Under Development</h5>
      <ul>
        <li>Editing values and units as ontology references</li>
        <li>Editing of other special case columns (contact, external links, dates, etc.)</li>
        <li>Clipboard paste of value without double-clicking to edit field</li>
        <li>Multi-cell clipboard paste</li>
        <li>Adding, removing and renaming columns</li>
        <li>Adding and removing rows</li>
        <li>Adding and removing studies and assays</li>
        <li>Editing meta-data for investigation, studies and assays</li>
        <li>Creating a sample sheet from scratch</li>
        <li>Providing default configurations for sample sheets</li>
        <li>Combo box editing for selectable values</li>
        <li>Full screen table editor</li>
        <li>Tour help for editing</li>
      </ul>
      <h5>Tips for Editing</h5>
      <ul>
        <li>
          You must select "Edit Sheets" from the "Sheet Operations" menu to
          enter edit mode in which values and column configurations can be
          modified.
        </li>
        <li>
          Only superusers, delegates or the project owner can modify column
          configurations and enable/disable columns for editing.
        </li>
        <li>
          Default regular expression patterns are automatically enforced for
          basic column types where appropriate. Adding a regex is not required
          unless you have custom restrictions you need to enforce.
        </li>
        <li>To edit a cell, double-click on it or press enter on the keyboard.</li>
        <li>
          Edit mode displays tables differently from normal sheet browsing by
          design.
          <ul>
            <li>iRODS link columns are hidden.</li>
            <li>Sorting by columns is disabled.</li>
            <li>Non-editable columns appear grayed out.</li>
            <li>
              Columns with no data are visible by default as long as they have
              been set editable.
            </li>
          </ul>
        </li>
        <li>Changes to values are saved as you edit them.</li>
        <li>
          If e.g. the same source appears on multiple rows, changes to one cell
          are automatically propagated to all repeated cells.
        </li>
        <li>
          By clicking "Finish Editing" you will save the current version of the
          sample sheet along with its configuration to "Sheet Versions".
        </li>
        <li>
          In case you get an error message when clicking "Finish Editing",
          please restore a previously saved sheet version and report the issue
          to <a href="mailto:mikko.nieminen@bihealth.de">mikko.nieminen@bihealth.de</a>
          along with the project URL.
        </li>
        <li>A complete manual for editing is forthcoming as development proceeds.</li>
      </ul>
    </div>
  </b-modal>
</template>

<script>
export default {
  name: 'EditorHelpModal',
  data () {
    return {
    }
  },
  methods: {
    showModal () {
      this.$refs.editorHelpModal.show()
    },

    hideModal () {
      this.$refs.editorHelpModal.hide()
    }
  }
}
</script>

<style scoped>
</style>
