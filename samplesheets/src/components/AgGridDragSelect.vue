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
 */

export default {
  name: 'AgGridDragSelect',
  props: [
    'app',
    'gridOptions'
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
      const topOffset = 50 // TODO: What causes this? Temporary HACK

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

    onCopy () {
      let copyData = ''
      let gridApi = this.gridOptions.api
      const focusedCell = gridApi.getFocusedCell()
      // let rowNum = null

      // Multi-select copy
      let selectedElems = this.$el.querySelectorAll('div.agds-selected')

      if (selectedElems.length > 0) {
        let selectedObjs = []

        // Get relevant data from each cell
        selectedElems.forEach(function (cell) {
          selectedObjs.push({
            'value': cell.textContent.trim(),
            'row': parseInt(cell.querySelector(
              '.sodar-ss-data').getAttribute('row-num')),
            'col': parseInt(cell.querySelector(
              '.sodar-ss-data').getAttribute('col-num'))
          })
        })

        // Sort by row and column
        selectedObjs.sort(function (a, b) {
          return a['row'] - b['row'] || a['col'] - b['col']
        })

        let previousRow = null

        // Build copyData
        for (let i = 0; i < selectedObjs.length; i++) {
          let o = selectedObjs[i]

          if (previousRow) {
            if (o['row'] !== previousRow) {
              copyData += '\n'
            } else {
              copyData += '\t'
            }
          }
          copyData += o['value']
          previousRow = o['row']
        }
      } else if (focusedCell) { // Single cell copy
        const row = gridApi.getDisplayedRowAtIndex(focusedCell.rowIndex)
        copyData = gridApi.getValue(focusedCell.column.colId, row)
      }
      this.$clipboard(copyData) // Use v-clipboard
      this.clearSelected()
      this.app.showNotification('Copied!', 'success', 1000)
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
