import gsap from 'gsap'

export const MOTION = {
  fast: 0.2,
  normal: 0.35,
  slow: 0.55,
  stagger: 0.04,
  maxStaggerItems: 32,
}

export function prefersReducedMotion() {
  return (
    typeof window !== 'undefined' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches
  )
}

/** @param {() => void | Promise<void>} fn */
export async function whenMotion(fn) {
  if (prefersReducedMotion()) return
  await fn()
}

/**
 * @param {Element | Element[] | string} target
 * @param {gsap.TweenVars} [vars]
 */
export function staggerReveal(target, vars = {}) {
  if (prefersReducedMotion()) return gsap.timeline()
  const els = gsap.utils.toArray(target).slice(0, MOTION.maxStaggerItems)
  if (!els.length) return gsap.timeline()
  gsap.set(els, { opacity: 0 })
  return gsap.to(els, {
    opacity: 1,
    duration: MOTION.fast,
    stagger: 0.025,
    ease: 'power1.out',
    clearProps: 'opacity',
    ...vars,
  })
}

/**
 * @param {Element} el
 * @param {gsap.TweenVars} [vars]
 */
export function shakeEl(el, vars = {}) {
  if (prefersReducedMotion() || !el) return gsap.timeline()
  return gsap.fromTo(
    el,
    { x: 0 },
    {
      x: 8,
      duration: 0.06,
      repeat: 5,
      yoyo: true,
      ease: 'sine.inOut',
      clearProps: 'x',
      ...vars,
    },
  )
}

/**
 * @param {Element} el
 */
export function collapseOut(el) {
  if (prefersReducedMotion() || !el) return Promise.resolve()
  return gsap
    .to(el, {
      scale: 0.92,
      opacity: 0,
      height: 0,
      marginTop: 0,
      marginBottom: 0,
      paddingTop: 0,
      paddingBottom: 0,
      duration: MOTION.fast,
      ease: 'power2.in',
    })
    .then()
}

/**
 * @param {Element} el
 */
export function popIn(el) {
  if (prefersReducedMotion() || !el) return gsap.timeline()
  gsap.set(el, { scale: 0.85, opacity: 0 })
  return gsap.to(el, {
    scale: 1,
    opacity: 1,
    duration: MOTION.normal,
    ease: 'back.out(2)',
    clearProps: 'transform,opacity',
  })
}

/**
 * @param {Element} el
 * @param {number} value 0-100
 */
export function tweenWidthPercent(el, value) {
  if (!el) return
  if (prefersReducedMotion()) {
    gsap.set(el, { width: `${Math.min(100, Math.max(0, value))}%` })
    return
  }
  gsap.to(el, {
    width: `${Math.min(100, Math.max(0, value))}%`,
    duration: MOTION.normal,
    ease: 'power2.out',
  })
}

export { gsap }
