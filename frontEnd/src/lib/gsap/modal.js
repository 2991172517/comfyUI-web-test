import { gsap, prefersReducedMotion } from '@/lib/gsap/motion.js'

/**
 * @param {HTMLElement | null} backdrop
 * @param {HTMLElement | null} panel
 */
export function animateModalIn(backdrop, panel) {
  if (!backdrop || !panel) return gsap.timeline()
  if (prefersReducedMotion()) {
    gsap.set([backdrop, panel], { clearProps: 'all' })
    return gsap.timeline()
  }
  gsap.set(backdrop, { opacity: 0 })
  gsap.set(panel, { opacity: 0, y: 24, scale: 0.94 })
  const tl = gsap.timeline()
  tl.to(backdrop, { opacity: 1, duration: 0.22, ease: 'power2.out' }, 0)
  tl.to(panel, { opacity: 1, y: 0, scale: 1, duration: 0.32, ease: 'power3.out' }, 0.04)
  return tl
}

/**
 * @param {HTMLElement | null} backdrop
 * @param {HTMLElement | null} panel
 * @returns {Promise<void>}
 */
export function animateModalOut(backdrop, panel) {
  if (!backdrop || !panel) return Promise.resolve()
  if (prefersReducedMotion()) return Promise.resolve()
  return gsap
    .timeline()
    .to(panel, { opacity: 0, y: 16, scale: 0.96, duration: 0.2, ease: 'power2.in' }, 0)
    .to(backdrop, { opacity: 0, duration: 0.18, ease: 'power2.in' }, 0.06)
    .then()
}
