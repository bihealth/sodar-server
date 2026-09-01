import { type TemplateRef } from 'vue'
import { beforeEach, describe, expect, test } from 'vitest'
import { type ColDef, type ColGroupDef } from 'ag-grid-community'

import { getAssayIrodsHeaderGroup } from '@/utils/gridUtils.ts'
import { type SodarContext, type SodarContextAssay } from '@/types.ts'

import { copy } from '../testUtils.ts'
import { sodarContext } from '../data/sodarContext.ts'
import { ASSAY_PATH, ASSAY_UUID, STUDY_UUID } from '../testConstants.ts'

// Tests -----------------------------------------------------------------------

describe('getAssayIrodsHeaderGroup()', () => {
  let context: SodarContext
  let assayContext: SodarContextAssay
  const mockModal = {} as TemplateRef

  beforeEach(() => {
    context = copy(sodarContext) as SodarContext
    assayContext = copy(
      context.studies[STUDY_UUID]!.assays[ASSAY_UUID] as SodarContextAssay
    ) as SodarContextAssay
  })

  test('get assay iRODS header group with default params', async () => {
    expect(context.irods_backend_enabled).toBe(true)
    expect(context.irods_webdav_url).toBe('https://davrods.local')
    expect(assayContext.irods_path).toBe(ASSAY_PATH)
    expect(context.irods_status).toBe(true)

    const res: ColGroupDef = getAssayIrodsHeaderGroup(
      context, assayContext, mockModal)
    const field = res.children[0] as ColDef
    expect(field.cellRendererParams.irodsBackendEnabled).toBe(true)
    expect(field.cellRendererParams.irodsWebdavUrl).toBe(
      'https://davrods.local')
    expect(field.cellRendererParams.assayIrodsPath).toBe(ASSAY_PATH)
    expect(field.cellRendererParams.irodsStatus).toBe(true)
  })

  test('get assay iRODS header group with modified params', async () => {
    context.irods_backend_enabled = false
    context.irods_webdav_url = 'https://sodar.example.org'
    assayContext.irods_path = ASSAY_PATH + '/xxx'
    context.irods_status = false

    const res: ColGroupDef = getAssayIrodsHeaderGroup(
      context, assayContext, mockModal)
    const field = res.children[0] as ColDef
    expect(field.cellRendererParams.irodsBackendEnabled).toBe(false)
    expect(field.cellRendererParams.irodsWebdavUrl).toBe(
      'https://sodar.example.org')
    expect(field.cellRendererParams.assayIrodsPath).toBe(ASSAY_PATH + '/xxx')
    expect(field.cellRendererParams.irodsStatus).toBe(false)
  })
})
