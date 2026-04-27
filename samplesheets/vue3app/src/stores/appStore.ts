import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { type SodarContext } from '@/types.ts'

const windowsPlatforms = /(win32|win64|windows|wince)/i

export const useAppStore = defineStore('app', ()=> {
  // Variables
  const currentAssayUuid = ref<string>('')
  const currentStudyUuid = ref<string>('')
  const editMode = ref<boolean>(false)
  const gridsBusy = ref<boolean>(false)
  const gridsLoaded = ref<boolean>(false)
  const overviewActive = ref<boolean>(false)
  const projectUuid = ref<string | null>(null)
  const sodarContext = ref<SodarContext | null>(null)
  const windowsOs = windowsPlatforms.test(window.navigator.userAgent)

  // Computed
  const sheetsAvailable = computed(
    () => currentStudyUuid.value && sodarContext.value)

  // Functions

  // Get perms value for given key
  function getPerm (permName: string): boolean | undefined {
    if (!sodarContext.value || !('perms' in sodarContext.value)) return false
    return sodarContext.value['perms'][permName]
  }

  // Get sheet_stats value for given key
  function getStat (statName: string): number | undefined {
    if (!sodarContext.value || !('sheet_stats' in sodarContext.value)) {
      return undefined
    }
    return sodarContext.value['sheet_stats'][statName]
  }

  return {
    // Variables
    currentAssayUuid,
    currentStudyUuid,
    editMode,
    gridsBusy,
    gridsLoaded,
    overviewActive,
    projectUuid,
    sodarContext,
    windowsOs,
    // Computed
    sheetsAvailable,
    // Functions
    getPerm,
    getStat
  }
})
