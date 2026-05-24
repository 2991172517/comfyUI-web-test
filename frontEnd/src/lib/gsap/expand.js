import { gsap, prefersReducedMotion } from '@/lib/gsap/motion.js'

/**
 * @param {HTMLElement | null} el
 */
export function expandIn(el) {
  if (!el) return Promise.resolve()
  if (prefersReducedMotion()) {
    gsap.set(el, { height: 'auto', opacity: 1, display: '' })
    return Promise.resolve()
  }

  gsap.killTweensOf(el)
  gsap.set(el, { display: 'block', height: 'auto', overflow: 'hidden', opacity: 0 })
  const targetHeight = el.offsetHeight
  gsap.set(el, { height: 0, opacity: 0 })

  return new Promise((resolve) => {
    gsap.to(el, {
      height: Math.max(targetHeight, 1),
      opacity: 1,
      duration: 0.36,
      ease: 'power2.out',
      onComplete: () => {
        gsap.set(el, { height: 'auto', overflow: '', clearProps: 'opacity' })
        resolve()
      },
    })
  })
}

/**
 * @param {HTMLElement | null} el
 */
export function expandOut(el) {
  if (!el) return Promise.resolve()
  if (prefersReducedMotion()) {
    gsap.set(el, { clearProps: 'all', display: 'none' })
    return Promise.resolve()
  }

  gsap.killTweensOf(el)
  const currentHeight = el.offsetHeight
  gsap.set(el, { overflow: 'hidden', height: currentHeight, opacity: 1 })

  return new Promise((resolve) => {
    gsap.to(el, {
      height: 0,
      opacity: 0,
      duration: 0.28,
      ease: 'power2.in',
      onComplete: () => {
        gsap.set(el, { clearProps: 'all' })
        resolve()
      },
    })
  })
}

/**
 * @param {HTMLElement | null} el
 * @param {boolean} open
 */
export async function setExpanded(el, open) {
  if (!el) return
  if (open) await expandIn(el)
  else await expandOut(el)
}
