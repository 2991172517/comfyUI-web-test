import { onMounted, onUnmounted, watch } from 'vue'
import { prefersReducedMotion } from '@/lib/gsap/motion.js'

/**
 * @param {import('vue').Ref<HTMLCanvasElement | null>} canvasRef
 * @param {import('vue').Ref<Record<string, unknown>>} themeRef
 */
export function useFireflyEcosystemCanvas(canvasRef, themeRef) {
  let width = 0
  let height = 0
  let ctx = null
  let rafId = 0
  let tendrils = []
  let particles = []
  let reduced = false

  class Tendril {
    constructor(theme) {
      this.x = Math.random() * width
      this.baseX = this.x
      this.segments =
        theme.tendrilStyle === 'straight' ? 3 : Math.floor(Math.random() * 5) + 5
      this.length = Math.random() * height * 0.4 + height * 0.2
      this.segmentLength = this.length / this.segments
      this.swaySpeed =
        theme.tendrilStyle === 'straight'
          ? Math.random() * 0.005 + 0.002
          : Math.random() * 0.002 + 0.001
      this.offset = Math.random() * Math.PI * 2
      this.color = theme.colors[Math.floor(Math.random() * theme.colors.length)]
      this.alpha = Math.random() * 0.3 + 0.1
      this.thickness =
        theme.tendrilStyle === 'thick' ? Math.random() * 3 + 1.5 : Math.random() * 1 + 1
      this.theme = theme
    }

    draw(time) {
      const theme = this.theme
      ctx.beginPath()
      ctx.moveTo(this.baseX, height)

      let currentX = this.baseX
      let currentY = height

      for (let i = 1; i <= this.segments; i++) {
        const sway = Math.sin(time * this.swaySpeed + this.offset + i * 0.5) * (i * 5)
        const windEffect = (i / this.segments) * (theme.wind || 0)
        const targetX = this.baseX + sway + windEffect
        const targetY = height - i * this.segmentLength

        ctx.quadraticCurveTo(currentX, currentY, targetX, targetY)
        currentX = targetX
        currentY = targetY
      }

      if (theme.tendrilStyle === 'thick') {
        ctx.lineCap = 'round'
        ctx.strokeStyle = `${this.color}${this.alpha * 0.5})`
        ctx.lineWidth = this.thickness * 2.5
        ctx.stroke()
      }

      ctx.strokeStyle = `${this.color}${this.alpha})`
      ctx.lineWidth = this.thickness
      ctx.stroke()

      if (theme.tendrilStyle !== 'straight') {
        ctx.beginPath()
        ctx.arc(currentX, currentY, this.thickness * 1.5 + 1, 0, Math.PI * 2)
        ctx.fillStyle = `${this.color}${this.alpha + 0.5})`
        ctx.fill()
      }
    }
  }

  class Particle {
    constructor(theme) {
      this.theme = theme
      this.reset(true)
    }

    reset(randomY = false) {
      const theme = this.theme
      this.x = Math.random() * width
      this.size = Math.random() * 2 + 0.5

      if (theme.particleType === 'bubble') {
        this.size = Math.random() * 4 + 2
        this.y = randomY ? Math.random() * height : height + 50
        this.speedY = Math.random() * 1 + 0.5
        this.speedX = (Math.random() - 0.5) * 0.5
      } else if (theme.particleType === 'sparks') {
        this.y = randomY ? Math.random() * height : height + 50
        this.speedY = Math.random() * -3 - 2
        this.speedX = Math.random() * 3 + 2
      } else {
        this.y = randomY ? Math.random() * height : -50
        this.speedY = Math.random() * 0.5 + 0.1
        this.speedX = (Math.random() - 0.5) * 0.5
      }

      this.color = theme.colors[Math.floor(Math.random() * theme.colors.length)]
      this.alpha = Math.random() * 0.8
      this.pulseSpeed = Math.random() * 0.05 + 0.01
    }

    draw(time) {
      const theme = this.theme
      this.y += theme.particleType === 'bubble' ? -this.speedY : this.speedY

      if (theme.particleType === 'bubble') {
        this.x += Math.sin(time * 0.001 + this.y * 0.01) * 0.5
      } else if (theme.particleType === 'sparks') {
        this.x += this.speedX
      } else {
        this.x += this.speedX + Math.sin(time * 0.001 + this.y * 0.01) * 0.2
      }

      if (
        (theme.particleType === 'bubble' || theme.particleType === 'sparks') &&
        this.y < -50
      ) {
        this.reset()
      } else if (theme.particleType === 'spore' && this.y > height + 50) {
        this.reset()
      }

      if (this.x < -50) this.x = width + 50
      if (this.x > width + 50) this.x = -50

      let currentAlpha = this.alpha + Math.sin(time * this.pulseSpeed) * 0.2
      currentAlpha = Math.max(0, Math.min(1, currentAlpha))

      if (theme.particleType === 'bubble') {
        ctx.beginPath()
        ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2)
        ctx.strokeStyle = `${this.color}${currentAlpha + 0.2})`
        ctx.lineWidth = 1.5
        ctx.stroke()
        ctx.beginPath()
        ctx.arc(
          this.x - this.size * 0.3,
          this.y - this.size * 0.3,
          this.size * 0.2,
          0,
          Math.PI * 2,
        )
        ctx.fillStyle = `rgba(255, 255, 255, ${currentAlpha * 0.6})`
        ctx.fill()
      } else if (theme.particleType === 'sparks') {
        ctx.beginPath()
        ctx.moveTo(this.x, this.y)
        ctx.lineTo(this.x - this.speedX * 2, this.y - this.speedY * 2)
        ctx.strokeStyle = `${this.color}${currentAlpha})`
        ctx.lineWidth = this.size > 1 ? 2 : 1
        ctx.stroke()
      } else {
        ctx.beginPath()
        ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2)
        ctx.fillStyle = `${this.color}${currentAlpha})`
        ctx.shadowBlur = 10
        ctx.shadowColor = `${this.color}1)`
        ctx.fill()
        ctx.shadowBlur = 0
      }
    }
  }

  function drawDome(theme) {
    if (!theme.drawDome) return
    const cx = width / 2
    const cy = height
    const r = Math.min(width, height) * 0.5
    const grad = ctx.createRadialGradient(cx, cy, r * 0.3, cx, cy, r)
    grad.addColorStop(0, 'rgba(255, 100, 200, 0.15)')
    grad.addColorStop(0.5, 'rgba(150, 50, 255, 0.05)')
    grad.addColorStop(1, 'rgba(0, 0, 0, 0)')
    ctx.beginPath()
    ctx.arc(cx, cy, r, Math.PI, 0)
    ctx.fillStyle = grad
    ctx.fill()
  }

  function drawWaterRipples(time, theme) {
    if (!theme.waterRipples) return
    ctx.fillStyle = 'rgba(0, 20, 50, 0.5)'
    ctx.fillRect(0, height - 25, width, 25)
    const grad = ctx.createLinearGradient(0, height - 25, 0, height)
    grad.addColorStop(0, 'rgba(0, 150, 255, 0.3)')
    grad.addColorStop(1, 'rgba(0, 50, 150, 0.8)')
    ctx.beginPath()
    for (let x = 0; x <= width; x += 20) {
      const y = height - 25 + Math.sin(time * 0.002 + x * 0.02) * 6
      if (x === 0) ctx.moveTo(x, y)
      else ctx.lineTo(x, y)
    }
    ctx.lineTo(width, height)
    ctx.lineTo(0, height)
    ctx.fillStyle = grad
    ctx.fill()
  }

  function initEcosystem(theme) {
    if (!ctx || reduced) return
    tendrils = []
    particles = []
    const numTendrils = Math.max(8, Math.floor(width / 30))
    const numParticles = Math.max(20, Math.floor(width / 10))
    for (let i = 0; i < numTendrils; i++) tendrils.push(new Tendril(theme))
    for (let i = 0; i < numParticles; i++) particles.push(new Particle(theme))
  }

  function animate(time) {
    if (!ctx || reduced) return
    const theme = themeRef.value
    const trail = theme.trailAlpha ?? 0.2
    ctx.fillStyle = `rgba(${theme.fadeRgb || '5,5,5'}, ${trail})`
    ctx.fillRect(0, 0, width, height)

    drawDome(theme)
    drawWaterRipples(time, theme)

    tendrils.forEach((t) => {
      t.theme = theme
      t.draw(time)
    })
    particles.forEach((p) => {
      p.theme = theme
      p.draw(time)
    })

    if (!theme.waterRipples && Math.random() > 0.95) {
      ctx.beginPath()
      const rx = Math.random() * width
      ctx.moveTo(rx, Math.random() * height)
      ctx.lineTo(rx, height)
      ctx.strokeStyle = `rgba(255,255,255,${theme.id === 2 ? 0.08 : 0.03})`
      ctx.lineWidth = 1
      ctx.stroke()
    }

    rafId = requestAnimationFrame(animate)
  }

  function resize() {
    const canvas = canvasRef.value
    if (!canvas) return
    width = canvas.width = window.innerWidth
    height = canvas.height = window.innerHeight
    initEcosystem(themeRef.value)
  }

  function start() {
    reduced = prefersReducedMotion()
    const canvas = canvasRef.value
    if (!canvas) return
    ctx = canvas.getContext('2d')
    if (!ctx || reduced) return
    resize()
    cancelAnimationFrame(rafId)
    rafId = requestAnimationFrame(animate)
  }

  function stop() {
    cancelAnimationFrame(rafId)
    rafId = 0
    tendrils = []
    particles = []
  }

  onMounted(() => {
    start()
    window.addEventListener('resize', resize)
  })

  onUnmounted(() => {
    window.removeEventListener('resize', resize)
    stop()
  })

  watch(
    themeRef,
    (theme) => {
      if (!reduced && ctx) initEcosystem(theme)
    },
    { deep: true },
  )

  return { resize, restart: start }
}
