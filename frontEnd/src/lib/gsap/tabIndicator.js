import { gsap, prefersReducedMotion } from '@/lib/gsap/motion.js'

/**
 * @param {HTMLElement} indicator
 * @param {HTMLElement} activeTab
 * @param {HTMLElement} container
 */
export function moveTabIndicator(indicator, activeTab, container) {
  if (!indicator || !activeTab || !container) return
  const cRect = container.getBoundingClientRect()
  const tRect = activeTab.getBoundingClientRect()
  const x = tRect.left - cRect.left
  const w = tRect.width
  if (prefersReducedMotion()) {
    gsap.set(indicator, { x, width: w, opacity: 1 })
    return
  }
  gsap.to(indicator, {
    x,
    width: w,
    opacity: 1,
    duration: 0.32,
    ease: 'power3.out',
  })
}
