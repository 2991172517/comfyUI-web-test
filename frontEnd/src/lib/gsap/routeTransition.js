import { gsap, prefersReducedMotion } from '@/lib/gsap/motion.js'

let activeTween = null

/**
 * @param {HTMLElement | null} el
 */
export function animateRouteEnter(el) {
  if (!el) return
  if (prefersReducedMotion()) return
  activeTween?.kill()
  gsap.set(el, { opacity: 0, y: 16 })
  activeTween = gsap.to(el, {
    opacity: 1,
    y: 0,
    duration: 0.38,
    ease: 'power2.out',
    clearProps: 'transform',
  })
  const inner = el.querySelector('[data-route-stagger]')
  if (inner) {
    const kids = gsap.utils.toArray(inner.children).slice(0, 24)
    if (kids.length) {
      gsap.fromTo(
        kids,
        { opacity: 0, y: 10 },
        {
          opacity: 1,
          y: 0,
          duration: 0.32,
          stagger: 0.03,
          delay: 0.08,
          ease: 'power2.out',
          clearProps: 'transform',
        },
      )
    }
  }
}

/**
 * @param {HTMLElement | null} el
 * @returns {Promise<void>}
 */
export function animateRouteLeave(el) {
  if (!el || prefersReducedMotion()) return Promise.resolve()
  activeTween?.kill()
  return gsap
    .to(el, {
      opacity: 0,
      y: -10,
      scale: 0.99,
      duration: 0.22,
      ease: 'power2.in',
    })
    .then()
}
