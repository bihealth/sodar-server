<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { type GridApi } from 'ag-grid-community'
import { useClipboard } from '@vueuse/core'

import { useAppStore } from '@/stores/appStore.ts'
import { useTableStore } from '@/stores/tableStore.ts'
import {
  type SheetTableCellDataValue,
  type SheetTableOntologyRef,
} from '@/types.ts'
import {
  SEL_APP_CONTAINER,
  SEL_APP_CONTENT,
  SEL_CONTENT_LEFT,
  VARIANT_SUCCESS
} from '@/constants.ts'

// Interfaces ------------------------------------------------------------------

interface CopyCell {
  rectLeft: number
  rectTop: number
  value: string
}
// TODO: Standard interfaces for coords?
interface XYCoordinate {
  x: number
  y: number
}
interface RectCoordinate {
  left: number
  top: number
  width: number
  height: number
}

// External Data ---------------------------------------------------------------

const props = defineProps(['assayMode', 'notifyCb', 'tableUuid'])
const appStore = useAppStore()
const tableStore = useTableStore()
const clipboard = useClipboard()

// Refs ------------------------------------------------------------------------

const mouseDown = ref<boolean>(false)
const pointEnd = ref<XYCoordinate | null>(null)
const pointStart = ref<XYCoordinate | null>(null)
const rootRef = ref<HTMLElement | null>(null)
const selectedItems = ref<Array<HTMLElement>>([])

// Internal Vars ---------------------------------------------------------------

let appScroll: number = 0
// Content elements
const leftContent: HTMLElement = document.querySelector(SEL_CONTENT_LEFT)!
const appContent: HTMLElement = document.querySelector(SEL_APP_CONTENT)!
let gridLeft: number = 0 // Left padding for grid

// Computed Vars ---------------------------------------------------------------

const selectionRect = computed<RectCoordinate | null>(() => {
  if (!rootRef.value ||
      !mouseDown.value ||
      !pointStart.value ||
      !pointEnd.value) {
    return null
  }

  let scroll: XYCoordinate
  if (typeof document === 'undefined') {
    scroll = { x: 0, y: 0 }
  } else {
    const scrollEl = document.querySelector(SEL_APP_CONTAINER)
    scroll = { x: scrollEl!.scrollLeft, y: scrollEl!.scrollTop }
  }
  const clientRect = rootRef.value!.getBoundingClientRect()
  const topOffset = document.querySelector<HTMLElement>(
    'div#sodar-top-container')!.offsetHeight

  // Calculate position and dimensions
  return {
    left: Math.min(
      pointStart.value.x, pointEnd.value.x) - clientRect.left - scroll.x,
    top: Math.min(pointStart.value.y, pointEnd.value.y) + scroll.y - topOffset,
    width: Math.abs(pointStart.value.x - pointEnd.value.x),
    height: Math.abs(pointStart.value.y - pointEnd.value.y)
  }
})

// Helpers ---------------------------------------------------------------------

function clearSelected () {
  rootRef.value!.querySelectorAll('div.ag-cell').forEach(function (item) {
    item.classList.remove('agds-selected')
  })
}

function getCopyValue (val: SheetTableCellDataValue, unit?: string): string {
  if (!val || val.length === 0) return ''
  let ret = ''
  if (!Array.isArray(val)) {
    ret = val
    if (unit) ret += ' ' + unit
    return ret
  }
  // Convert value if not a string
  for (let i = 0; i < val.length; i++) {
    if (i > 0) ret += ';'
    if (val[i]!.hasOwnProperty('name')) {
      ret += (val[i] as SheetTableOntologyRef).name
    } else ret += val[i]
    if (unit) ret += ' ' + unit
  }
  return ret
}

function isSelected (el: HTMLElement): boolean {
  if (el.classList.contains('sodar-ss-data-unselectable')) return false
  if (el.classList.contains('ag-cell')) {
    const elRect = el.getBoundingClientRect() // Element base rectangle

    const rectA = selectionRect.value!
    const rectB: RectCoordinate = {
      top: elRect.top - rootRef.value!.offsetTop + appScroll,
      left: elRect.left - gridLeft,
      width: el.clientWidth,
      height: el.clientHeight
    }
    return (
      rectA.left <= rectB.left + rectB.width &&
      rectA.left + rectA.width >= rectB.left &&
      rectA.top <= rectB.top + rectB.height &&
      rectA.top + rectA.height >= rectB.top
    )
  }
  return false
}

function updateGridLeft () {
  if (!appContent) return
  const leftPadding = parseFloat(
  window.getComputedStyle(
    appContent as HTMLElement, null).getPropertyValue('padding-left'))
  gridLeft = leftContent!.clientWidth +
    document.querySelector('#agds-' + props.tableUuid)!.clientLeft + leftPadding
}

// Event Handlers --------------------------------------------------------------

function onClickOutside (event: PointerEvent) {
  let el: HTMLElement | null = event.target as HTMLElement
  while (el) {
    if (el === rootRef.value) return
    el = el.parentElement
  }
  clearSelected()
}

function onCopy () {
  if (!appStore.selectEnabled || appStore.editMode) return

  let api: GridApi
  if (!props.assayMode) api = tableStore.gridApi.study!
  else api = tableStore.gridApi.assays[props.tableUuid]!
  let copyData = ''
  const focusedCell = api.getFocusedCell()

  if (selectedItems.value.length > 0) { // Multi-cell copy
    const valObjs: Array<CopyCell> = []

    for (const item of selectedItems.value) {
      const cellRect = item.getBoundingClientRect()
      const d = item.querySelector('.sodar-ss-data')!
      const colId = 'col' + d.getAttribute('data-col-num')
      const rowId = d.getAttribute('data-row-id')
      const cellData = api.getRowNode(rowId!)!.data[colId!]
      valObjs.push({
        rectLeft: cellRect.left,
        rectTop: cellRect.top,
        value: getCopyValue(cellData.value, cellData.unit)
      })
    }

    // Sort by cell coordinates
    valObjs.sort(function (a, b) {
      return a.rectTop - b.rectTop || a.rectLeft - b.rectLeft
    })

    // Build copyData
    let prevTop: number | null = null
    for (let i = 0; i < valObjs.length; i++) {
      const o = valObjs[i]!
      if (prevTop) {
        if (o.rectTop !== prevTop) copyData += '\n'
        else copyData += '\t'
      }
      copyData += o.value
      prevTop = o.rectTop
    }
  } else if (focusedCell) { // Single cell copy
    const rowNode = api.getDisplayedRowAtIndex(focusedCell.rowIndex)
    const cellData = rowNode!.data[focusedCell.column.getColId()]!
    copyData = getCopyValue(cellData.value, cellData.unit)
  }

  clipboard.copy(copyData)
  if (props.notifyCb) {
    props.notifyCb('Cell values copied into clipboard', VARIANT_SUCCESS)
  }
}

function onMouseDown (event: MouseEvent) {
  clearSelected()
  // Cancel if not enabled
  if (!appStore.selectEnabled || appStore.editMode) return
  if (event.button === 2) return // Ignore right clicks
  // Store current top scroll value
  appScroll = document.querySelector(SEL_APP_CONTAINER)!.scrollTop
  // Register start point
  mouseDown.value = true
  pointStart.value = { x: event.pageX, y: event.pageY }
  // Enable listeners
  window.addEventListener('mousemove', onMouseMove)
  window.addEventListener('mouseup', onMouseUp)
}

function onMouseMove (event: MouseEvent) {
  clearSelected() // NOTE: This will break selection with scrolling, known issue
  // Update endpoint
  if (mouseDown.value) {
    pointEnd.value = { x: event.pageX, y: event.pageY }
    const cells = rootRef.value!.querySelectorAll('div.ag-cell')
    if (cells) {
      selectedItems.value = Array.from(cells).filter((el) => {
        return isSelected(el as HTMLElement)
      }) as Array<HTMLElement>
    }
    selectedItems.value.forEach(function (el) {
      el.classList.add('agds-selected')
    })
  }
}

function onMouseUp () {
  // Remove listeners
  window.removeEventListener('mousemove', onMouseMove)
  window.removeEventListener('mouseup', onMouseUp)
  // Reset state
  mouseDown.value = false
  pointStart.value = null
  pointEnd.value = null
}

// Life Cycle ------------------------------------------------------------------

onMounted(() => {
  updateGridLeft()
  document.addEventListener('click', onClickOutside)
  window.addEventListener('resize', updateGridLeft)
})

onUnmounted(() => {
  document.removeEventListener('click', onClickOutside)
  window.removeEventListener('resize', updateGridLeft)
})
</script>

<template>
  <div class="ag-grid-drag-select"
       :id="'agds-' + tableUuid"
       ref="rootRef"
       @mousedown="onMouseDown"
       @keydown.ctrl.c="onCopy"
       @keydown.meta.c="onCopy">
    <slot :selectedItems="selectedItems" />
    <div v-if="mouseDown"
         class="ag-grid-drag-select-box">
    </div>
  </div>
</template>

<style scoped>
</style>
