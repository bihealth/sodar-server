import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

const windowsPlatforms = /(win32|win64|windows|wince)/i

// Types
export interface SodarContextLinkLabel {
  label: string,
  url: string | null
}
export interface SodarContextInvestigation {
  identifier: string,
  title: string,
  description: string,
  comments: { [key: string]: string } | null
}
export interface SodarContextAssay {
  name: string,
  display_name: string,
  file_name: string,
  measurement_type: string,
  technology_type: string,
  technology_platform: string,
  comments: { [key: string]: string } | null,
  irods_path: string,
  plugin_name: string | null,
  plugin_title: string | null,
  display_row_links: boolean
}
export interface SodarContextStudy {
  display_name: string,
  file_name: string,
  identifier: string,
  title: string,
  description: string,
  comments: { [key: string]: string } | null
  irods_path: string,
  table_url: string,
  plugin_name: string | null,
  plugin_title: string | null
  assays: { [key: string]: SodarContextAssay }
}
export interface SodarContextAlert {
  html: string,
  level: string
}
export interface SodarContext {
  configuration: string | null, // TODO: Verify type
  inv_file_name: string | null,
  irods_status: boolean | null,
  irods_path?: string,
  irods_backend_enabled: boolean,
  parser_version: string,
  parser_warnings: boolean,
  irods_webdav_enabled: boolean,
  irods_webdav_url: string,
  external_link_labels?: { [key: string]: string | SodarContextLinkLabel }
  ontology_url_template?: string,
  ontology_url_skip?: Array<string>
  min_col_width: number,
  max_col_width: number,
  allow_editing: boolean,
  alerts: Array<SodarContextAlert>,
  csrf_token: string,
  project_uuid: string,
  user_uuid: string,
  sheet_sync_enabled: boolean,
  site_read_only: boolean,
  investigation: SodarContextInvestigation | object,
  studies: { [key: string]: SodarContextStudy },
  perms: { [key: string]: boolean },
  sheet_stats: { [key: string]: number }
}

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
  function getPerm (permName: string): boolean | undefined {
    if (!sodarContext.value || !('perms' in sodarContext.value)) return false
    return sodarContext.value['perms'][permName]
  }
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
