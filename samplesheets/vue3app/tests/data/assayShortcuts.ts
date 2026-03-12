import { type AssayShortcut, type AssayShortcuts } from '@/types.ts'
import { ASSAY_PATH_PREFIX } from '../testConstants.ts'

// TODO: Add extra link for ticket once supported (see #2403)
export const assayShortcuts: AssayShortcuts = {
  results_reports: {
    id: 'results_reports',
    label: 'Results and Reports',
    path: ASSAY_PATH_PREFIX + 'ResultsReports',
    enabled: true
  } as AssayShortcut,
  misc_files: {
    id: 'misc_files',
    label: 'Misc Files',
    path: ASSAY_PATH_PREFIX + 'MiscFiles',
    enabled: false
  } as AssayShortcut,
  track_hub_0: {
    id: 'track_hub_0',
    label: 'TrackHubX',
    path: ASSAY_PATH_PREFIX + 'TrackHubX',
    enabled: true,
    icon: 'mdi:road',
    title: 'Track hub X',
    assay_plugin: false
  } as AssayShortcut,
  plugin_coll: {
    id: 'plugin_coll',
    label: 'PluginCollection',
    path: ASSAY_PATH_PREFIX + 'PluginCollection',
    enabled: true,
    icon: 'mdi:info',
    title: 'Plugin collection',
    assay_plugin: true
  } as AssayShortcut
}
