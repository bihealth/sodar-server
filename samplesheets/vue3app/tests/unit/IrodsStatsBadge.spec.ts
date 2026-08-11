import { beforeEach, describe, expect, test, vi } from 'vitest'
import { mount, type VueWrapper } from '@vue/test-utils'

import IrodsStatsBadge from '@/components/IrodsStatsBadge.vue'
import { copy, waitSelector } from '../testUtils.ts'
import { PROJECT_UUID, STUDY_PATH } from '../testConstants.ts'
import {
  type IrodsStatsBadgeProps,
  type IrodsStatsResponseBody
} from '../testTypes.ts'

const defaultProps: IrodsStatsBadgeProps = {
  irodsPath: STUDY_PATH,
  irodsStatus: true,
  projectUuid: PROJECT_UUID
}
let props: IrodsStatsBadgeProps
const bodySuccess = { file_count: 170, total_size: 170000000 }
const statusTextSuccess = 'ok'
const statusTextError = 'Not found'

describe('IrodsStatsBadge.vue', () => {
  function mountComponent (): VueWrapper {
    return mount(IrodsStatsBadge, { props: props })
  }
  function mockFetch (
      status: number,
      statusText: string,
      body: IrodsStatsResponseBody | object) {
    global.fetch = vi.fn(() =>
      Promise.resolve({
        json: () => Promise.resolve(body),
        status: status,
        statusText: statusText
      } as Response))
  }
  beforeEach(() => {
    props = copy(defaultProps) as IrodsStatsBadgeProps
  })

  test('render component with default properties', async () => {
    mockFetch(200, statusTextSuccess, bodySuccess)
    const wrapper = mountComponent()
    // Wait for loading to not be present
    await waitSelector(wrapper, '.sodar-ss-irods-stats-loading', 0)
    const badge = wrapper.find('.sodar-ss-irods-stats')
    expect(badge.classes()).toContain('badge-info')
    expect(badge.classes()).not.toContain('badge-danger')
    expect(badge.text()).toBe('170 files (170 MB)')
  })

  test('display error message', async () => {
    // Suppress logging as error message is expected
    vi.spyOn(console, 'error').mockImplementation(() => undefined)
    mockFetch(403, statusTextError, {})
    const wrapper = mountComponent()
    await waitSelector(wrapper, '.sodar-ss-irods-stats-loading', 0)
    const badge = wrapper.find('.sodar-ss-irods-stats')
    expect(badge.classes()).not.toContain('badge-info')
    expect(badge.classes()).toContain('badge-danger')
    expect(badge.text()).toBe('Error')
  })

  test('render empty component with irodsStatus=false', async () => {
    props.irodsStatus = false
    const wrapper = mountComponent()
    expect(wrapper.find('.sodar-ss-irods-stats').exists()).toBe(false)
  })
})
