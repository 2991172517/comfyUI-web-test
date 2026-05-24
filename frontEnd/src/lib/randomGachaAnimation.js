import gsap from 'gsap'
import { prefersReducedMotion } from '@/lib/gsap/motion.js'

/** 与 random-gacha.css 中 --gacha-item-gap 保持一致；词条宽度随文字，滚动按实测布局计算 */
const ITEM_GAP = 10

function getStripGap(stripEl) {
  const style = getComputedStyle(stripEl)
  const gap = parseFloat(style.columnGap || style.gap)
  return Number.isFinite(gap) ? gap : ITEM_GAP
}

/**
 * @param {HTMLElement} stripEl
 * @param {number} landingIndex
 * @param {number} viewportWidth
 */
function computeLandingX(stripEl, landingIndex, viewportWidth) {
  const items = stripEl.querySelectorAll('.random-gacha-reel__item')
  const gap = getStripGap(stripEl)
  let offset = 0

  for (let i = 0; i < landingIndex; i++) {
    offset += (items[i]?.offsetWidth || 0) + gap
  }

  const landingWidth = items[landingIndex]?.offsetWidth || 0
  const center = offset + landingWidth / 2
  return center - viewportWidth / 2
}

const LOCK_PAUSE_MS = 500
const MIN_SPIN_MS = 1100
const MAX_SPIN_MS = 2800
/** 每组滚轮启动间隔（毫秒） */
const REEL_STAGGER_MS = 140

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms))
}

/**
 * @param {string[]} candidates
 * @param {string} winner
 */
function buildReelStrip(candidates, winner) {
  const base = candidates.length ? [...candidates] : [winner]
  const minLen = Math.max(base.length * 4, 16)
  const strip = []
  while (strip.length < minLen) {
    strip.push(...base)
  }
  const tailCycles = 2
  const tail = []
  for (let c = 0; c < tailCycles; c++) tail.push(...base)
  const winIdx = strip.length + Math.floor(base.length * 1.5)
  strip.push(...tail, winner)
  return { strip, landingIndex: winIdx }
}

function ensureReelMarker(viewport) {
  let marker = viewport.querySelector('.random-gacha-reel__marker')
  if (!marker) {
    marker = document.createElement('div')
    marker.className = 'random-gacha-reel__marker'
    marker.setAttribute('aria-hidden', 'true')
    viewport.appendChild(marker)
  }
  if (!viewport.querySelector('.random-gacha-reel__shade')) {
    const shade = document.createElement('div')
    shade.className = 'random-gacha-reel__shade'
    shade.setAttribute('aria-hidden', 'true')
    viewport.appendChild(shade)
  }
  return marker
}

/**
 * @param {HTMLElement} viewport
 * @param {{ candidates: string[], winner: string }} row
 */
function mountReelRow(viewport, row) {
  viewport.innerHTML = ''
  ensureReelMarker(viewport)

  const { strip, landingIndex } = buildReelStrip(row.candidates, row.winner)
  const stripEl = document.createElement('div')
  stripEl.className = 'random-gacha-reel__strip'

  for (const text of strip) {
    const item = document.createElement('div')
    item.className = 'random-gacha-reel__item'
    item.textContent = text
    item.title = text
    if (String(text).trim() === String(row.winner).trim()) {
      item.dataset.winner = '1'
    }
    stripEl.appendChild(item)
  }

  viewport.appendChild(stripEl)

  // 强制布局，以便按词条实际宽度计算停位
  void stripEl.offsetWidth

  const viewportWidth =
    viewport.getBoundingClientRect().width || viewport.clientWidth || 380
  const finalX = computeLandingX(stripEl, landingIndex, viewportWidth)

  return { stripEl, finalX, landingIndex }
}

/**
 * @param {HTMLElement} stripEl
 * @param {number} finalX
 * @param {number} landingIndex
 */
function spinReel(stripEl, finalX, landingIndex, startDelayMs = 0) {
  const reel = stripEl.closest('.random-gacha-reel')

  const dist = Math.abs(finalX)
  const duration = Math.min(
    MAX_SPIN_MS / 1000,
    Math.max(MIN_SPIN_MS / 1000, 0.85 + dist / 1200),
  )

  gsap.set(stripEl, { x: 0 })

  return new Promise((resolve) => {
    const run = () => {
      reel?.classList.add('is-spinning')
      gsap.to(stripEl, {
        x: -finalX,
        duration,
        ease: 'power4.out',
        onComplete: () => {
          reel?.classList.remove('is-spinning')
          reel?.classList.add('is-landed')
          const items = stripEl.querySelectorAll('.random-gacha-reel__item')
          const landed = items[landingIndex]
          if (landed) landed.classList.add('is-winner')
          resolve(landed)
        },
      })
    }

    if (startDelayMs > 0) {
      gsap.delayedCall(startDelayMs / 1000, run)
    } else {
      run()
    }
  })
}

/**
 * @param {HTMLElement} winnerEl
 * @param {DOMRect} targetRect
 */
function absorbWinnerEl(winnerEl, targetRect) {
  const r = winnerEl.getBoundingClientRect()
  const flyer = winnerEl.cloneNode(true)
  flyer.classList.add('random-gacha-absorb-flyer')
  flyer.setAttribute('aria-hidden', 'true')

  gsap.set(flyer, {
    position: 'fixed',
    left: r.left,
    top: r.top,
    width: r.width,
    height: r.height,
    margin: 0,
    zIndex: 10060,
    pointerEvents: 'none',
  })

  document.body.appendChild(flyer)
  winnerEl.style.visibility = 'hidden'

  const tx = targetRect.left + targetRect.width / 2
  const ty = targetRect.top + targetRect.height / 2
  const cx = r.left + r.width / 2
  const cy = r.top + r.height / 2

  return gsap
    .timeline()
    .to(flyer, {
      x: tx - cx,
      y: ty - cy,
      scale: 0.15,
      opacity: 0.2,
      duration: 0.42,
      ease: 'power3.in',
    })
    .eventCallback('onComplete', () => flyer.remove())
}

/**
 * @param {{
 *   root: HTMLElement,
 *   rows: { name: string, candidates: string[], winner: string, target?: string }[],
 *   targetEl?: HTMLElement | null,
 * }} opts
 */
export async function playRandomGachaAnimation({ root, rows, targetEl }) {
  if (!rows?.length || !root) {
    return { played: false }
  }

  const listEl = root.querySelector('[data-gacha-rows]')
  if (!listEl) return { played: false }

  const reduced = prefersReducedMotion()
  const targetRect = targetEl?.getBoundingClientRect?.()

  listEl.innerHTML = ''
  /** @type {HTMLElement[]} */
  const rowEls = []

  for (const row of rows) {
    const rowEl = document.createElement('div')
    rowEl.className = 'random-gacha-row'
    rowEl.innerHTML = `
      <div class="random-gacha-row__label" title="${escapeAttr(row.name)}">${escapeHtml(row.name)}</div>
      <div class="random-gacha-row__reel random-gacha-reel" data-gacha-reel></div>
    `
    listEl.appendChild(rowEl)
    rowEls.push(rowEl)
  }

  await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)))

  rowEls.forEach((el) => el.classList.add('is-active'))

  /** @type {(HTMLElement | undefined)[]} */
  let landedItems = []

  if (reduced) {
    rows.forEach((row, i) => {
      const reelHost = rowEls[i]?.querySelector('[data-gacha-reel]')
      if (!reelHost) return
      reelHost.innerHTML = ''
      ensureReelMarker(reelHost)
      const item = document.createElement('div')
      item.className = 'random-gacha-reel__item is-winner'
      item.textContent = row.winner
      const strip = document.createElement('div')
      strip.className = 'random-gacha-reel__strip'
      strip.appendChild(item)
      reelHost.appendChild(strip)
      reelHost.classList.add('is-landed')
    })
    await sleep(220)
    landedItems = rows.map((row, i) => {
      return rowEls[i]?.querySelector('.random-gacha-reel__item.is-winner') ?? undefined
    })
  } else {
    const spinJobs = rows.map((row, i) => {
      const reelHost = rowEls[i]?.querySelector('[data-gacha-reel]')
      if (!reelHost) return Promise.resolve(undefined)
      const { stripEl, finalX, landingIndex } = mountReelRow(reelHost, row)
      return spinReel(stripEl, finalX, landingIndex, i * REEL_STAGGER_MS)
    })
    landedItems = await Promise.all(spinJobs)
    await sleep(LOCK_PAUSE_MS)
  }

  rowEls.forEach((el) => {
    el.classList.remove('is-active')
    el.classList.add('is-done')
  })

  const winners = landedItems.filter(Boolean)

  if (targetRect && winners.length && !reduced) {
    await Promise.all(winners.map((el) => absorbWinnerEl(el, targetRect)))
  } else if (targetRect && rows.length && reduced) {
    await sleep(120)
  }

  return { played: true }
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

function escapeAttr(s) {
  return escapeHtml(s).replace(/'/g, '&#39;')
}
