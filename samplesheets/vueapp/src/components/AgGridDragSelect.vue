<template>
  <div class="ag-grid-drag-select"
       :id="'agds-' + _uid"
       @mousedown="onMouseDown"
       @keyup.ctrl.67="onCopy">
    <slot :selectedItems="selectedItems" />
    <div v-if="mouseDown" class="ag-grid-drag-select-box"></div>
  </div>
</template>

<script>
/*
 Modified from vue-drag-select to work with ag-grid
 TODO: Refactor and cleanup
 TODO: Reorder functions
 TODO: Make this work with scrolling
 */

export default {
  name: 'AgGridDragSelect',
  props: [
    'app',
    'uuid'
  ],
  data () {
    return {
      mouseDown: false,
      startPoint: null,
      endPoint: null,
      gridTop: null,
      selectedItems: []
    }
  },
  computed: {
    selectionBox () {
      if (!this.mouseDown || !this.startPoint || !this.endPoint) return {}

      const clientRect = this.$el.getBoundingClientRect()
      const scroll = this.getScroll()
      const topOffset = document.querySelector('div#sodar-top-container').offsetHeight

      // Calculate position and dimensions of the selection box
      const left = Math.min(this.startPoint.x, this.endPoint.x) - clientRect.left - scroll.x
      const top = Math.min(this.startPoint.y, this.endPoint.y) + scroll.y - topOffset
      const width = Math.abs(this.startPoint.x - this.endPoint.x)
      const height = Math.abs(this.startPoint.y - this.endPoint.y)

      // Return the styles to be applied
      return {
        left,
        top,
        width,
        height
      }
    }
  },
  watch: {
    selectedItems (val) {
      this.$emit('change', val)
    }
  },
  methods: {
    clearSelected () {
      this.$el.querySelectorAll('div.ag-cell').forEach(function (item) {
        item.classList.remove('agds-selected')
      })
    },

    getScroll () {
      // If we're on the server, default to 0,0
      if (typeof document === 'undefined') {
        return {
          x: 0,
          y: 0
        }
      }

      // const scrollEl = this.$el
      const scrollEl = document.querySelector('div#sodar-app-container')

      return {
        x: scrollEl.scrollLeft,
        y: scrollEl.scrollTop
      }
    },

    isItemSelected (el) {
      if (el.classList.contains('sodar-ss-data-unselectable')) return false

      if (el.classList.contains('ag-cell')) {
        const boxA = this.selectionBox

        // Get element base rectangle
        const elRect = el.getBoundingClientRect()

        // Get current top scroll value
        const appScroll = document.querySelector(
          '.sodar-app-container').scrollTop

        // Get left padding
        // TODO: Only calculate this when viewport is resized
        const leftContent = document.querySelector('.sodar-content-left')
        const appContent = document.querySelector('.sodar-app-content')
        const leftContentPadding = parseFloat(
          window.getComputedStyle(appContent, null).getPropertyValue(
            'padding-left'))
        const gridLeft = leftContent.clientWidth + document.querySelector(
          '#agds-' + this._uid).clientLeft + leftContentPadding

        const boxB = {
          top: elRect.top - this.gridTop + appScroll,
          left: elRect.left - gridLeft,
          width: el.clientWidth,
          height: el.clientHeight
        }

        return !!(
          boxA.left <= boxB.left + boxB.width &&
          boxA.left + boxA.width >= boxB.left &&
          boxA.top <= boxB.top + boxB.height &&
          boxA.top + boxA.height >= boxB.top
        )
      }

      return false
    },

    onMouseDown (event) {
      // Disable and clear all if selecting is disabled by app
      if (!this.app.selectEnabled) {
        this.clearSelected()
        return
      }

      // Ignore right clicks
      if (event.button === 2) return

      // Register begin point
      this.mouseDown = true
      this.startPoint = {
        x: event.pageX,
        y: event.pageY
      }

      this.clearSelected()

      // Start listening for mouse move and up events
      window.addEventListener('mousemove', this.onMouseMove)
      window.addEventListener('mouseup', this.onMouseUp)
    },

    onMouseMove (event) {
      // Clear existing selection
      // TODO: This does not work with scrolling, disabled for now
      // this.clearSelected()

      // Update the end point position
      if (this.mouseDown) {
        this.endPoint = {
          x: event.pageX,
          y: event.pageY
        }

        const dataCells = this.$el.querySelectorAll('div.ag-cell')

        if (dataCells) {
          this.selectedItems = Array.from(dataCells).filter((item) => {
            return this.isItemSelected(item.$el || item)
          })
        }

        this.selectedItems.forEach(function (item) {
          item.classList.add('agds-selected')
        })
      }
    },

    onMouseUp (event) {
      // Clean up event listeners
      window.removeEventListener('mousemove', this.onMouseMove)
      window.removeEventListener('mouseup', this.onMouseUp)

      // Reset state
      this.mouseDown = false
      this.startPoint = null
      this.endPoint = null
    },

    convertCopyValue (value) {
      // Convert value if not a string
      if (Array.isArray(value)) {
        if (value.length === 0) return ''
        let retVal = ''
        for (let i = 0; i < value.length; i++) {
          if (i > 0) retVal += ';'
          if (typeof value[i] === 'object' && 'name' in value[i]) {
            retVal += value[i].name
          } else {
            retVal += value[i]
          }
        }
        return retVal
      }
      return value
    },

    onCopy () {
      // Cancel copy if cell editing is active
      if (!this.app.selectEnabled) return

      let copyData = ''
      const gridApi = this.app.getGridOptionsByUuid(this.uuid).api
      const focusedCell = gridApi.getFocusedCell()
      // let rowNum = null

      // Multi-select copy
      const selectedElems = this.$el.querySelectorAll('div.agds-selected')

      if (selectedElems.length > 0) {
        const selectedObjs = []

        // Get relevant data from each cell
        selectedElems.forEach(function (cell) {
          const cellRect = cell.getBoundingClientRect()
          const rowId = parseInt(cell.querySelector(
            '.sodar-ss-data').getAttribute('row-id')
          )
          const colId = 'col' + cell.querySelector(
            '.sodar-ss-data').getAttribute('col-num')

          selectedObjs.push({
            value: gridApi.getValue(colId, gridApi.getRowNode(rowId)).value,
            top: cellRect.top,
            left: cellRect.left
          })
        })

        // Sort by cell coordinates (to ensure this works with sorting)
        selectedObjs.sort(function (a, b) {
          return a.top - b.top || a.left - b.left
        })

        let prevTop = null

        // Build copyData
        for (let i = 0; i < selectedObjs.length; i++) {
          const o = selectedObjs[i]

          if (prevTop) {
            if (o.top !== prevTop) {
              copyData += '\n'
            } else {
              copyData += '\t'
            }
          }
          copyData += this.convertCopyValue(o.value)
          prevTop = o.top
        }
      } else if (focusedCell) { // Single cell copy
        const row = gridApi.getDisplayedRowAtIndex(focusedCell.rowIndex)
        copyData = this.convertCopyValue(
          gridApi.getValue(focusedCell.column.colId, row).value)
      }
      this.$copyText(copyData) // Use vue-clipboard2
      this.clearSelected()
      this.app.showNotification('Copied', 'success', 1000)
    }
  },
  mounted () {
    this.gridTop = document.querySelector('.ag-grid-drag-select').offsetTop
  },
  beforeDestroy () {
    // Remove event listeners
    window.removeEventListener('mousemove', this.onMouseMove)
    window.removeEventListener('mouseup', this.onMouseUp)

    this.$children.forEach((child) => {
      child.$off('click')
    })
  }
}
</script>

<style>
  .ag-grid-drag-select {
    position: relative;
    user-select: none;
  }

  .ag-grid-drag-select-box {
    position: absolute;
    background: rgba(0, 162, 255, .4);
    z-index: 99;
  }
</style>
