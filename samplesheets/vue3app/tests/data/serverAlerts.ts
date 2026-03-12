import { type SodarContextAlert } from '@/stores/appStore.ts'

export const serverAlerts: Array<SodarContextAlert> = [
  {
    html: '<p>First alert</p>',
    level: 'info'
  },
  {
    html: '<p><b>Second alert</b></p>',
    level: 'danger'
  }
]

