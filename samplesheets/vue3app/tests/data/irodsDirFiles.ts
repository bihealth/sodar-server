import { type IrodsDirFile } from '@/types.ts'
import {
  ASSAY_PATH_PREFIX,
  MISC_FILES_DIR,
  USER_UUID,
  USER_UUID2
} from '../testConstants.ts'

const PATH_PREFIX = ASSAY_PATH_PREFIX + MISC_FILES_DIR + '/'

export const irodsDirFiles: Array<IrodsDirFile> = [
  {
    irods_request_status: null,
    irods_request_user: null,
    modify_time: '2026-03-04 10:20',
    name: 'test.bam',
    path: PATH_PREFIX + 'test.bam',
    size: 170000000,
    type: 'obj'
  } as IrodsDirFile,
  {
    irods_request_status: 'ACTIVE',
    irods_request_user: USER_UUID,
    modify_time: '2026-03-05 11:21',
    name: 'test.vcf.gz',
    path: PATH_PREFIX + 'subcoll/test.vcf.gz',
    size:  64000,
    type: 'obj'
  } as IrodsDirFile,
  {
    irods_request_status: 'ACTIVE',
    irods_request_user: USER_UUID2,
    modify_time: '2026-03-06 12:22',
    name: 'test.txt',
    path: PATH_PREFIX + 'subcoll/subcoll2/test.txt',
    size:  1024,
    type: 'obj'
  } as IrodsDirFile
]
