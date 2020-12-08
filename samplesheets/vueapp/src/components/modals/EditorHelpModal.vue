<template>
  <b-modal
      id="sodar-ss-editor-help-modal" ref="editorHelpModal"
      centered no-fade hide-footer
      size="xl"
      title="Sample Sheet Editor Help"
      :static="true">
    <!-- Object list -->
    <div id="sodar-ss-editor-help-modal-content">
      <p>
        The sample sheet editor is under incremental development. Certain
        features are available, while others will be enabled later. Bugs and
        unannounced UI changes are possible. Below you can find the list of
        currently implemented and upcoming features. Make sure to check back
        once a new SODAR version is deployed.
      </p>
      <h5 class="text-success font-weight-bold">Available Features</h5>
      <ul>
        <li>Editing of simple values (text, integer/double, select)</li>
        <li>Editing values as ontology term references</li>
        <li>Special field editing (performer, perform date, contacts, external links)</li>
        <li>Renaming materials and processes</li>
        <li>Protocol selection</li>
        <li>Inserting rows</li>
        <li>Deleting rows</li>
        <li>Saving, browsing and restoring sample sheet versions</li>
        <li>Configuring columns for editing</li>
        <li>Unit support</li>
        <li>Custom regex, optional integer range, automatic filling of default value</li>
        <li>Default suffix and automated filling of node names</li>
        <li>Clipboard copy/paste of column configuration</li>
      </ul>
      <h5 class="text-danger font-weight-bold">Under Development</h5>
      <ul>
        <li>Editing units as ontology term references</li>
        <li>Clipboard paste of value without double-clicking to edit field</li>
        <li>Multi-cell clipboard paste</li>
        <li>Adding, removing and renaming columns</li>
        <li>Adding and removing studies and assays</li>
        <li>Editing meta-data for investigation, studies and assays</li>
        <li>Creating a sample sheet from scratch</li>
        <li>Providing default configurations for sample sheets</li>
        <li>Combo box editing for selectable values</li>
        <li>Full screen table editor</li>
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
        <li><u>Ontology Term Value Editing</u></li>
          <ul>
            <li>
              Editing ontology term values happens in a modal opened by double
              clicking a cell in an ontology value column.
            </li>
            <li>
              Terms are queried from ontologies imported into the local SODAR
              database.
            </li>
            <li>
              It is also possible for free text entry of terms not in the
              SODAR database.
            </li>
            <li>
              In column configuration, valid ontologies for a column can be
              defined along with a boolean flag for allowing multiple terms per
              cell.
            </li>
            <li>
              Obsolete terms and unknown ontologies are flagged in the UI.
            </li>
            <li>
              If you want to copy/paste full ontology term references from one
              cell to another, use the copy-paste function in the ontology term
              editor modal.
            </li>
            <li>
              If an ontology you use is not included in the SODAR database for
              querying, please contact helpdesk and request it to be added.
            </li>
          </ul>
        <li><u>Row Inserting</u></li>
          <ul>
            <li>
              At the moment, you may only insert one row at a time. You will
              need to either save the row or cancel the insertion.
            </li>
            <li>
              Row ordering is not currently guaranteed. New rows will appear
              at the bottom of the table when inserted. They <em>may</em> appear
              with a different placement once exiting edit mode.
            </li>
            <li>Rows are only saved when you click the "Save row" icon.</li>
            <li>
              Currently, you are expected to fill in nodes from left to
              right. New nodes will become available once preceeding nodes are
              filled in.
            </li>
            <li>
              Default protocols will be filled in automatically, as will default
              values for other columns.
            </li>
            <li>
              You can set a <em>default suffix</em> for materials (other than
              sources or data files) which enables automatically creating
              material nodes on row insert.
            </li>
            <li>New sources and samples can only be created in the study table.</li>
            <li>All nodes on a row must be defined to enable saving the row.</li>
            <li>Unnamed data materials are allowed.</li>
            <li>
              <strong>Hint:</strong> It is recommended to first configure the
              editing of columns for desired format and default values, before
              going forward with row insertion.
            </li>
          </ul>
        <li><u>Row Deleting</u></li>
          <ul>
            <li>
              Deleting a study row is not allowed, if its sample is used in one
              or more assays.
            </li>
            <li>Deleting all rows in a table is currently not allowed.</li>
          </ul>
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
