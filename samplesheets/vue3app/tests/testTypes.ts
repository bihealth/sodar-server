import { type Mock } from 'vitest'
import {
  type SodarContextAssay,
  type SodarContextStudy
} from '@/stores/appStore.ts'

export interface IrodsButtonsProps {
  editMode: boolean,
  enabled: boolean,
  extraLinks: Array<object>, // TODO: Improve
  irodsBackendEnabled: boolean,
  irodsDirModalRef: { show: Mock } | null,
  irodsWebdavUrl: string,
  irodsPath: string,
  irodsStatus: boolean,
  showFileList: boolean
}

export interface IrodsStatsBadgeProps {
  irodsPath: string,
  irodsStatus: boolean,
  projectUuid: string
}

export interface IrodsStatsResponseBody {
  file_count: number, total_size: number
}

export interface SheetTableHeaderProps {
  assayMode: boolean,
  tableUuid: string
}

export interface TableDetailListProps {
  assayMode: boolean,
  tableUuid: string,
  tableContext: SodarContextAssay | SodarContextStudy,
  tableMetaFields: Array<Array<string>>,
  tableSodarFields: Array<Array<string>>
}

export interface TableDetailListRowProps {
  legend: string,
  value: string,
  icon: string,
  iconClass: string,
  title: string,
  rowClass: string,
  copyButton: boolean
}
