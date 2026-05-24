import { gsap, prefersReducedMotion, popIn } from '@/lib/gsap/motion.js'

const seen = new Set()

/** @param {string} key */
export function resetBatchCellSeen(key) {
  if (key) seen.delete(key)
  else seen.clear()
}

/**
 * @param {HTMLElement} cellEl
 * @param {string} cellKey
 */
export function animateBatchCellImage(cellEl, cellKey) {
  if (!cellEl || seen.has(cellKey)) return
  seen.add(cellKey)
  if (prefersReducedMotion()) return

  const img = cellEl.querySelector('img')
  const target = img || cellEl

  gsap.fromTo(
    cellEl,
    { boxShadow: '0 0 0 0px hsl(var(--primary) / 0)' },
    {
      boxShadow: '0 0 0 3px hsl(var(--primary) / 0.55)',
      duration: 0.35,
      yoyo: true,
      repeat: 1,
      ease: 'power2.out',
      clearProps: 'boxShadow',
    },
  )

  popIn(target)
}
