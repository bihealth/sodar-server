// General app utilities

import { useAppStore } from '@/stores/appStore.ts'

// Return standard Ajax request init parameters for fetch()
export function getAjaxRequestInit (
    method: string,
    body: object
): RequestInit {
  const appStore = useAppStore()
  return {
    method: method,
    body: JSON.stringify(body),
    credentials: 'same-origin',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      'X-CSRFToken': appStore.sodarContext?.csrf_token || ''
    }
  }
}
