import { ref } from 'vue'
import { defineStore } from 'pinia'

import { type EditUnsavedRow, type StudyEditContext } from '@/types.ts'

export const useEditStore = defineStore('edit', () => {
  // TODO: Review if all Vue2 app values are needed once implementing edit mode
  const editContext = ref<StudyEditContext | null>(null)
  const editDataUpdated = ref<boolean>(false)
  const editStudyData = ref<boolean>(false)
  const unsavedData = ref<boolean>(false)
  const unsavedRow = ref<EditUnsavedRow | null>(null)
  const updatingRow = ref<boolean>(false)
  const versionSaved = ref<boolean>(true) // NOTE: Should be true by default

  function $reset () {
    editContext.value = null
    editDataUpdated.value = false
    editStudyData.value = false
    unsavedData.value = false
    unsavedRow.value = null
    updatingRow.value = false
    versionSaved.value = true
  }

  return {
    // Variables
    editContext,
    editDataUpdated,
    editStudyData,
    unsavedData,
    unsavedRow,
    updatingRow,
    versionSaved,
    // Functions
    $reset
  }
})
