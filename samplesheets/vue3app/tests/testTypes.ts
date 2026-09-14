import { type TemplateRef } from 'vue'
import { type Mock } from 'vitest'
import {
  type NotifyCb,
  type SodarContextAssay,
  type SodarContextStudy
} from '@/types.ts'

export interface IrodsButtonsProps {
  editMode: boolean
  enabled: boolean
  extraLinks: Array<object> // TODO: Improve
  irodsBackendEnabled: boolean
  irodsDirModalRef: { show: Mock } | null
  irodsPath: string
  irodsStatus: boolean
  irodsWebdavUrl: string
  notifyCb?: NotifyCb
  showFileList: boolean
}

export interface IrodsStatsBadgeProps {
  irodsPath: string
  irodsStatus: boolean
  projectUuid: string
}

export interface IrodsStatsResponseBody {
  file_count: number
  total_size: number
}

export interface SheetTableHeaderProps {
  assayMode: boolean
  tableUuid: string
}

export interface SheetTableProps {
  assayMode: boolean,
  colToggleModalRef: TemplateRef,
  tableUuid: string
}

export interface TableDetailListProps {
  assayMode: boolean
  tableContext: SodarContextAssay | SodarContextStudy
  tableMetaFields: Array<Array<string>>
  tableSodarFields: Array<Array<string>>
  tableUuid: string
}

export interface TableDetailListRowProps {
  copyButton: boolean
  icon: string
  iconClass: string
  legend: string
  notifyCb?: NotifyCb
  rowClass: string
  title: string
  value: string
}
