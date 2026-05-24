import { nextTick, watch } from 'vue'
import { staggerReveal } from '@/lib/gsap/motion.js'

/**
 * @param {import('vue').Ref<unknown[]>} listRef
 * @param {import('vue').Ref<HTMLElement | null>} rootRef
 * @param {string} [itemSelector]
 */
export function useListStagger(listRef, rootRef, itemSelector = '[data-stagger-item]') {
  watch(
    () => listRef.value?.length,
    async () => {
      await nextTick()
      const root = rootRef.value
      if (!root) return
      const items = root.querySelectorAll(itemSelector)
      if (items.length) staggerReveal(items)
    },
  )
}
