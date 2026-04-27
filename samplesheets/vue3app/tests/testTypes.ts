import { type Mock } from 'vitest'
import { type SodarContextAssay, type SodarContextStudy } from '@/types.ts'

export interface IrodsButtonsProps {
  editMode: boolean
  enabled: boolean
  extraLinks: Array<object> // TODO: Improve
  irodsBackendEnabled: boolean
  irodsDirModalRef: { show: Mock } | null
  irodsPath: string
  irodsStatus: boolean
  irodsWebdavUrl: string
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
  rowClass: string
  title: string
  value: string
}
