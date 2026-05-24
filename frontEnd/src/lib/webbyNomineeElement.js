/** Port of CodePen webby-nominee (2025 Webby Award Nominee) — easing inlined for Vite. */

const easing = {
  linear: (t) => t,
  easeInExpo: (t) => (t === 0 ? 0 : 2 ** (10 * t - 10)),
  easeOutCubic: (t) => 1 - (1 - t) ** 3,
}

function tweenValue(start, end, p, ease = false) {
  const delta = end - start
  const easeKey = ease
    ? `ease${ease.charAt(0).toUpperCase()}${ease.slice(1)}`
    : 'linear'
  const easeFn = easing[easeKey] || easing.linear
  return start + delta * easeFn(p)
}

export class WebbyNominee extends HTMLElement {
  connectedCallback() {
    this.canvas = this.querySelector('.js-canvas')
    this.ctx = this.canvas.getContext('2d')
    this.badge = this.querySelector('.js-badge')

    this.discs = []
    this.lines = []
    this.particles = []

    this.setSize()
    this.setDiscs()
    this.setLines()
    this.setParticles()
    this.bindEvents()

    this._tick = this.tick.bind(this)
    requestAnimationFrame(this._tick)
  }

  disconnectedCallback() {
    this._unmounted = true
    window.removeEventListener('resize', this._onResize)
  }

  bindEvents() {
    this._onResize = this.onResize.bind(this)
    window.addEventListener('resize', this._onResize)
  }

  onResize() {
    this.setSize()
    this.setDiscs()
    this.setLines()
    this.setParticles()
  }

  setSize() {
    this.rect = this.getBoundingClientRect()
    this.badgeRect = this.badge.getBoundingClientRect()

    this.render = {
      width: this.rect.width,
      height: this.rect.height,
      dpi: window.devicePixelRatio,
    }

    this.canvas.width = this.render.width * this.render.dpi
    this.canvas.height = this.render.height * this.render.dpi
  }

  setDiscs() {
    const { badgeRect } = this
    const { width, height } = this.rect

    this.discs = []
    const diag = Math.hypot(width, height)

    this.startDisc = {
      x: width * 0.5,
      y: height * 0.5,
      w: diag * 0.5,
      h: diag * 0.5,
    }

    this.endDisc = {
      x: width * 0.5,
      y: height * 0.5,
      w: badgeRect.width * 0.5,
      h: badgeRect.height * 0.5,
    }

    const totalDiscs = 20
    for (let i = 0; i < totalDiscs; i++) {
      const p = i / totalDiscs
      this.discs.push(this.tweenDisc({ p }))
    }
  }

  setLines() {
    const { width, height } = this.rect
    this.lines = []

    const totalLines = 100
    const linesAngle = (Math.PI * 2) / totalLines

    for (let i = 0; i < totalLines; i++) {
      const angle = (i * linesAngle + performance.now() * 0.0001) % (Math.PI * 2)

      const p0 = {
        x: width * 0.5 + Math.cos(angle) * this.startDisc.w,
        y: height * 0.5 + Math.sin(angle) * this.startDisc.h,
      }

      const p1 = {
        x: width * 0.5 + Math.cos(angle) * this.endDisc.w,
        y: height * 0.5 + Math.sin(angle) * this.endDisc.h,
      }

      this.lines.push({
        p0,
        p1,
        l: { x: p1.x - p0.x, y: p1.y - p0.y },
      })
    }
  }

  setParticles() {
    this.particles = []
    for (let i = 0; i < 500; i++) {
      this.particles.push(this.initParticle())
    }
  }

  initParticle() {
    return {
      lineIndex: Math.round((this.lines.length - 1) * Math.random()),
      p: Math.random(),
      v: 0.005 + Math.random() * 0.005,
      l: 0.01 + Math.random() * 0.1,
      a: 0.05 + Math.random() * 0.15,
    }
  }

  drawDiscs() {
    const { ctx } = this
    ctx.strokeStyle = '#444'
    ctx.lineWidth = 2

    const outerDisc = this.startDisc
    ctx.beginPath()
    ctx.ellipse(outerDisc.x, outerDisc.y, outerDisc.w, outerDisc.h, 0, 0, Math.PI * 2)
    ctx.stroke()
    ctx.closePath()

    this.discs.forEach((disc) => {
      ctx.beginPath()
      ctx.ellipse(disc.x, disc.y, disc.w, disc.h, 0, 0, Math.PI * 2)
      ctx.stroke()
      ctx.closePath()
    })
  }

  drawLines() {
    const { ctx, lines } = this
    ctx.beginPath()
    lines.forEach(({ p0, p1 }) => {
      ctx.moveTo(p0.x, p0.y)
      ctx.lineTo(p1.x, p1.y)
    })
    ctx.strokeStyle = '#4449'
    ctx.lineWidth = 2
    ctx.stroke()
    ctx.closePath()
  }

  drawParticles() {
    const { ctx, particles } = this
    particles.forEach((particle) => {
      const line = this.lines[particle.lineIndex]
      const start = {
        x: line.p0.x + line.l.x * particle.p,
        y: line.p0.y + line.l.y * particle.p,
      }
      const p1 = {
        x: start.x + line.l.x * particle.l,
        y: start.y + line.l.y * particle.l,
      }
      ctx.beginPath()
      ctx.moveTo(start.x, start.y)
      ctx.lineTo(p1.x, p1.y)
      ctx.strokeStyle = `rgba(255, 255, 255, ${particle.a})`
      ctx.lineWidth = 2
      ctx.stroke()
      ctx.closePath()
    })
  }

  moveDiscs() {
    this.discs.forEach((disc) => {
      disc.p = (disc.p + 0.001) % 1
      this.tweenDisc(disc)
    })
  }

  moveParticles() {
    this.particles.forEach((particle) => {
      if (particle.p < 1) {
        particle.p += particle.v
      } else {
        particle.p = 0
      }
    })
  }

  tweenDisc(disc) {
    disc.x = tweenValue(this.startDisc.x, this.endDisc.x, disc.p)
    disc.y = tweenValue(this.startDisc.y, this.endDisc.y, disc.p, 'inExpo')
    disc.w = tweenValue(this.startDisc.w, this.endDisc.w, disc.p, 'outCubic')
    disc.h = tweenValue(this.startDisc.h, this.endDisc.h, disc.p, 'outCubic')
    return disc
  }

  tick() {
    if (this._unmounted) return

    const { ctx } = this
    ctx.clearRect(0, 0, this.canvas.width, this.canvas.height)

    ctx.save()
    ctx.scale(this.render.dpi, this.render.dpi)

    this.moveDiscs()
    this.moveParticles()
    this.setLines()

    this.drawDiscs()
    this.drawLines()
    this.drawParticles()

    ctx.restore()
    requestAnimationFrame(this._tick)
  }
}

let defined = false

export function ensureWebbyNomineeElement() {
  if (defined || typeof customElements === 'undefined') return
  if (!customElements.get('webby-nominee')) {
    customElements.define('webby-nominee', WebbyNominee)
  }
  defined = true
}
