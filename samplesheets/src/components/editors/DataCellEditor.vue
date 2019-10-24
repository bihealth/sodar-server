<template>
  <input :ref="'input'"
         v-model="editValue"
         class="ag-cell-edit-input"
         @keydown="onKeyDown($event)" />
</template>

<script>
import Vue from 'vue'

const navKeyCodes = [33, 34, 35, 36, 37, 38, 39, 40]

export default Vue.extend({
  data () {
    return {
      app: null,
      headerInfo: null,
      objCls: null,
      headerType: null,
      value: null,
      editValue: '',
      ogEditValue: ''
    }
  },
  methods: {
    /* Implemented ag-grid editor methods ----------------------------------- */
    getValue () {
      return this.value
    },
    isPopup () {
      return false
    },
    isCancelBeforeStart () {
      return false
    },
    isCancelAfterEnd () {
      return true
    },
    /* Event handling ------------------------------------------------------- */
    onKeyDown (event) {
      let keyCode = this.getKeyCode(event)

      // Handle navigation keycodes
      // TODO: Better way to do this? event.stopPropagation() fails (see #690)
      if (navKeyCodes.indexOf(keyCode) !== -1) {
        let caretPos = event.currentTarget.selectionStart

        if (keyCode === 33 || keyCode === 36) { // PgUp/Home
          caretPos = 0
        } else if (keyCode === 34 || keyCode === 35) { // PgDown/End
          caretPos = event.currentTarget.value.length
        } else if (keyCode === 37) { // Left
          if (caretPos >= 1) {
            caretPos = caretPos - 1
          } else {
            caretPos = 0
          }
        } else if (keyCode === 39) { // Right
          caretPos = caretPos + 1
        }

        this.$nextTick(() => {
          event.currentTarget.setSelectionRange(caretPos, caretPos)
        })
      }
    },
    /* Helpers -------------------------------------------------------------- */
    getKeyCode (event) {
      return (typeof event.which === 'undefined') ? event.keyCode : event.which
    }
  },
  created () {
    this.app = this.params.app
    this.headerInfo = this.params.headerInfo
    this.value = this.params.value
    this.editValue = this.params.value['value']
    this.ogEditValue = this.editValue

    // Prevent keyboard navigation in parent when editing
    // See onKeyDown() for manual in-cell editing
    this.params.colDef.suppressKeyboardEvent = function (params) {
      if (params.event.shiftKey) { // Key combinations break event keyCode
        return false
      }
      return navKeyCodes.indexOf(params.event.keyCode) !== -1
    }
  },
  mounted () {
    Vue.nextTick(() => {
      if (this.$refs.input) {
        this.$refs.input.focus()
      }
    })
  },
  updated () {
    this.value['value'] = this.editValue
  },
  beforeDestroy () {
    if (this.ogEditValue !== this.editValue) {
      // TODO: Is copying necessary?
      this.app.handleCellEdit(
        JSON.parse(JSON.stringify(this.value)), // Copying just in case..
        this.ogEditValue,
        this.headerInfo)
    }
  }
})
</script>

<style scoped>
</style>
