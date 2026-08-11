import {
  type BaseColorVariant,
  type ToastOrchestratorCreateParam,
} from 'bootstrap-vue-next'

import { type NotifyCb } from '@/types.ts'
import {
  TOAST_INTERVAL_DANGER,
  TOAST_INTERVAL_DEFAULT,
  VARIANT_DANGER,
} from '@/constants.ts'

export function getNotifyCb (
    create: (obj: ToastOrchestratorCreateParam) => void
): NotifyCb {
  return function (
    body: string,
    variant: keyof BaseColorVariant,
    interval?: number
  ) {
    if (!interval || interval === 0) {
      interval = variant == VARIANT_DANGER ?
        TOAST_INTERVAL_DANGER : TOAST_INTERVAL_DEFAULT
    }
    create({
      body: body,
      variant: variant,
      modelValue: interval
    })
  } as NotifyCb
}
