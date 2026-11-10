import { ref } from 'vue'
import { defineStore } from 'pinia'

import { type EditUnsavedRow, type StudyEditContext } from '@/types.ts'

export const useEditStore = defineStore('edit', () => {
  const editContext = ref<StudyEditContext | null>(null)
  const editDataUpdated = ref<boolean>(false)
  const editStudyData = ref<boolean>(false)
  const enableRowSave = ref<boolean>(false)
  const modalEditValid = ref<boolean>(true)
  const unsavedData = ref<boolean>(false)
  const unsavedRow = ref<EditUnsavedRow | null>(null)
  const updateCache = ref<boolean>(false)
  const updatingRow = ref<boolean>(false)
  const versionSaved = ref<boolean>(true) // NOTE: Should be true by default

  function $reset () {
    editContext.value = null
    editDataUpdated.value = false
    editStudyData.value = false
    enableRowSave.value = false
    unsavedData.value = false
    unsavedRow.value = null
    updateCache.value = false
    updatingRow.value = false
    versionSaved.value = true
  }

  return {
    // Variables
    editContext,
    editDataUpdated,
    editStudyData,
    enableRowSave,
    modalEditValid,
    unsavedData,
    unsavedRow,
    updateCache,
    updatingRow,
    versionSaved,
    // Functions
    $reset
  }
})
