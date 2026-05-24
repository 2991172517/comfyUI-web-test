import { nextTick, watch } from 'vue'
import { animateModalIn, animateModalOut } from '@/lib/gsap/modal.js'

/**
 * @param {import('vue').Ref<boolean>} openRef
 * @param {import('vue').Ref<HTMLElement | null>} backdropRef
 * @param {import('vue').Ref<HTMLElement | null>} panelRef
 */
export function useModalMotion(openRef, backdropRef, panelRef) {
  watch(openRef, async (open, wasOpen) => {
    if (open) {
      await nextTick()
      animateModalIn(backdropRef.value, panelRef.value)
      return
    }
    if (wasOpen && backdropRef.value && panelRef.value) {
      await animateModalOut(backdropRef.value, panelRef.value)
    }
  })
}
