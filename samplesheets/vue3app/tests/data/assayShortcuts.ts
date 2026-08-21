import {
  type AssayShortcut,
  type AssayShortcutExtraLink,
  type AssayShortcuts
} from '@/types.ts'
import { ASSAY_PATH_PREFIX } from '../testConstants.ts'

export const ticketLink: AssayShortcutExtraLink = {
  url: 'https://ticket:xzy123@0.0.0.0' + ASSAY_PATH_PREFIX + 'TrackHubs/track1',
  icon: 'mdi:ticket',
  id: 'ticket_access_1',
  class: 'sodar-irods-ticket-access-1-btn',
  title: 'Latest Access Ticket for track1',
  enabled: true
}

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
    assay_plugin: false,
    extra_links: [ticketLink]
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
