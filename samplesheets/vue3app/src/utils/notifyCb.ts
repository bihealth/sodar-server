import {
  BToast,
  type ToastOrchestratorCreateParam,
  type ToastOrchestratorParam,
  type BaseColorVariant,
  type PromiseWithComponent,
} from 'bootstrap-vue-next'

import { type NotifyCb } from '@/types.ts'
import { TOAST_INTERVAL } from '@/constants.ts'

// PromiseWithComponent<typeof BToast, ToastOrchestratorParam>

export function getNotifyCb (
    create: (obj: ToastOrchestratorCreateParam) => void): NotifyCb {
  return function (
    body: string,
    variant: keyof BaseColorVariant,
    interval?: number
  ) {
    if (!interval || interval === 0) interval = TOAST_INTERVAL
    create({
      body: body,
      variant: variant,
      modelValue: interval
    })
  } as NotifyCb
}
