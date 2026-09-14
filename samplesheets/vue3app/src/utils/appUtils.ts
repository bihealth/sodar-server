// General app utilities

import { useAppStore } from '@/stores/appStore.ts'
import { REQ_GET } from '@/constants.ts'

// Return standard Ajax request init parameters for fetch()
export function getAjaxRequestInit (
    method?: string,
    body?: object
): RequestInit {
  const appStore = useAppStore()
  if (!method) method = REQ_GET
  const headers: HeadersInit = {
    Accept: 'application/json',
    'Content-Type': 'application/json',
  }
  if (![REQ_GET, 'HEAD', 'OPTIONS'].includes(method.toUpperCase())) {
    headers['X-CSRFToken'] = appStore.sodarContext?.csrf_token || ''
  }
  const ret: RequestInit = {
    method: method,
    credentials: 'same-origin',
    headers: headers
  }
  if (body) ret.body = JSON.stringify(body)
  return ret
}
