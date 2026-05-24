import { gsap, prefersReducedMotion } from '@/lib/gsap/motion.js'

/**
 * @param {HTMLElement} anchor
 * @param {{ favorited?: boolean }} [opts]
 */
export function playFavoriteBurst(anchor, { favorited = true } = {}) {
  if (prefersReducedMotion() || !anchor) return gsap.timeline()

  const rect = anchor.getBoundingClientRect()
  const cx = rect.left + rect.width / 2
  const cy = rect.top + rect.height / 2
  const color = favorited ? '#fbbf24' : '#94a3b8'
  const particles = []

  for (let i = 0; i < 8; i++) {
    const dot = document.createElement('span')
    dot.className = 'gsap-fav-particle'
    dot.style.cssText = `
      position:fixed;left:${cx}px;top:${cy}px;width:5px;height:5px;border-radius:999px;
      background:${color};pointer-events:none;z-index:10060;margin:-2.5px 0 0 -2.5px;
    `
    document.body.appendChild(dot)
    particles.push(dot)
  }

  const tl = gsap.timeline({
    onComplete: () => particles.forEach((p) => p.remove()),
  })

  tl.to(anchor, { scale: 1.35, duration: 0.12, ease: 'back.out(3)' }, 0)
  tl.to(anchor, { scale: 1, duration: 0.2, ease: 'power2.out' }, 0.12)

  particles.forEach((dot, i) => {
    const angle = (i / 8) * Math.PI * 2
    const dist = gsap.utils.random(18, 32)
    tl.to(
      dot,
      {
        x: Math.cos(angle) * dist,
        y: Math.sin(angle) * dist,
        opacity: 0,
        scale: 0.2,
        duration: 0.45,
        ease: 'power3.out',
      },
      0,
    )
  })

  return tl
}
