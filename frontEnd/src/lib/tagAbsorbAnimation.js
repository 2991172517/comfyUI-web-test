import gsap from 'gsap'
import { prefersReducedMotion } from '@/lib/gsap/motion.js'
import { splitPromptTokens } from '@/lib/promptDisplay.js'

const CHIP_IN_EDITOR = '[data-tag-chip]:not([data-tag-muted])'
const MAX_TAGS = 80
const MAX_TEXT_PIECES = 12
const RESTORE_DELAY = 1.45
const RESTORE_DURATION = 0.55

/**
 * @param {HTMLElement} chip
 * @returns {DOMRect}
 */
function getChipStartRect(chip) {
  const r = chip.getBoundingClientRect()
  if (r.width > 2 && r.height > 2) return r

  const editor = chip.closest('[data-prompt-tag-editor]')
  if (!editor) return r

  const editorR = editor.getBoundingClientRect()
  const w = chip.offsetWidth || 120
  const h = chip.offsetHeight || 48

  if (editorR.width > 2 && editorR.height > 2) {
    let x = 0
    let y = 0
    let node = chip
    while (node && node !== editor) {
      x += node.offsetLeft || 0
      y += node.offsetTop || 0
      node = node.offsetParent
    }
    return new DOMRect(editorR.left + x, editorR.top + y, w, h)
  }

  const side = editor.getAttribute('data-prompt-side') || 'positive'
  const chips = Array.from(editor.querySelectorAll(CHIP_IN_EDITOR))
  const idx = chips.indexOf(chip)
  const colLeft = side === 'negative' ? window.innerWidth * 0.52 : window.innerWidth * 0.08
  const rowTop = window.innerHeight * 0.26
  return new DOMRect(colLeft, rowTop + idx * (h + 8), w, h)
}

/** @param {HTMLElement} editor */
function chipsInEditor(editor) {
  return Array.from(editor.querySelectorAll(CHIP_IN_EDITOR))
}

/** @param {DOMRect} rect */
function rectCenter(rect) {
  return {
    x: rect.left + rect.width / 2,
    y: rect.top + rect.height / 2,
  }
}

function truncateText(text, max = 56) {
  const t = String(text || '').trim()
  if (t.length <= max) return t
  return `${t.slice(0, max)}…`
}

/**
 * @param {ParentNode} root
 * @param {string} kind
 * @param {'positive'|'negative'} side
 * @param {number} index
 */
function fallbackAnchorRect(root, kind, side, index) {
  const bar = root.querySelector('[data-global-prompt-bar]')
  if (bar) {
    const r = bar.getBoundingClientRect()
    if (r.width > 2) {
      const yOff = index * 18 + (side === 'negative' ? 10 : 0)
      const xOff = kind === 'random' ? r.width * 0.55 : r.width * 0.12
      return new DOMRect(r.left + xOff, r.top + 24 + yOff, r.width * 0.35, 20)
    }
  }

  const preview = root.querySelector('[data-prompt-merge-preview]')
  const pr = preview?.getBoundingClientRect?.()
  if (pr?.width > 2) {
    const col = side === 'negative' ? pr.left + pr.width * 0.55 : pr.left + pr.width * 0.1
    return new DOMRect(col, pr.top + 36 + index * 24, pr.width * 0.35, 20)
  }

  const colLeft = side === 'negative' ? window.innerWidth * 0.52 : window.innerWidth * 0.08
  return new DOMRect(colLeft, window.innerHeight * 0.2 + index * 24, 140, 20)
}

/**
 * @param {ParentNode} root
 * @param {'positive'|'negative'} side
 */
function workflowInputSources(side, root) {
  const editor = root.querySelector(
    `[data-prompt-tag-editor][data-prompt-side="${side}"]`,
  )
  if (editor) {
    return chipsInEditor(editor)
      .slice(0, MAX_TAGS)
      .map((el) => ({ type: 'tag', el, kind: 'core' }))
  }

  const ta = root.querySelector(
    `[data-prompt-text-source][data-prompt-side="${side}"]`,
  )
  const raw = String(ta?.value || '').trim()
  if (!ta || !raw) return []

  const tokens = splitPromptTokens(raw)
  const pieces = tokens.length > 1 ? tokens.slice(0, MAX_TEXT_PIECES) : [raw]
  const rect = ta.getBoundingClientRect()
  if (rect.width < 4) return []

  return pieces.map((text, i) => ({
    type: 'text',
    text,
    rect,
    kind: 'core',
    highlightEl: ta,
    side,
    stackIndex: i,
    stackTotal: pieces.length,
  }))
}

/**
 * @param {object} seg
 * @param {'positive'|'negative'} side
 * @param {number} index
 * @param {ParentNode} root
 * @param {{ positive: boolean, negative: boolean }} coreDone
 */
function segmentToSources(seg, side, index, root, coreDone) {
  const kind = seg?.kind || 'core'
  const text = String(seg?.text || '').trim()
  if (!text) return []

  if (kind === 'core') {
    if (coreDone[side]) return []
    coreDone[side] = true
    return workflowInputSources(side, root)
  }

  const block = root.querySelector(
    `[data-merge-block][data-merge-side="${side}"][data-merge-index="${index}"]`,
  )
  const rect = block?.getBoundingClientRect?.()
  const anchor =
    rect && rect.width > 2 ? rect : fallbackAnchorRect(root, kind, side, index)

  return [
    {
      type: 'text',
      text,
      rect: anchor,
      kind,
      highlightEl: block || null,
      side,
      segmentIndex: index,
    },
  ]
}

/**
 * @param {{ positive?: object[], negative?: object[] }} mergeSegments
 * @param {ParentNode} root
 */
function collectFromMergePlan(mergeSegments, root) {
  const pos = mergeSegments.positive || []
  const neg = mergeSegments.negative || []
  const maxLen = Math.max(pos.length, neg.length)
  const coreDone = { positive: false, negative: false }
  const merged = []

  for (let i = 0; i < maxLen; i++) {
    if (pos[i]) merged.push(...segmentToSources(pos[i], 'positive', i, root, coreDone))
    if (neg[i]) merged.push(...segmentToSources(neg[i], 'negative', i, root, coreDone))
    if (merged.filter((s) => s.type === 'tag').length >= MAX_TAGS) break
  }

  return capSources(merged)
}

function collectLegacySources(root) {
  const pos = workflowInputSources('positive', root)
  const neg = workflowInputSources('negative', root)
  const merged = []
  const maxLen = Math.max(pos.length, neg.length)
  for (let i = 0; i < maxLen; i++) {
    if (pos[i]) merged.push(pos[i])
    if (neg[i]) merged.push(neg[i])
  }
  return capSources(merged)
}

/** 保持合并顺序，仅做数量上限 */
function capSources(merged) {
  let tagCount = 0
  let textCount = 0
  const out = []
  for (const s of merged) {
    if (s.type === 'tag') {
      if (tagCount >= MAX_TAGS) continue
      tagCount += 1
    } else if (s.type === 'text') {
      if (textCount >= MAX_TEXT_PIECES * 4) continue
      textCount += 1
    }
    out.push(s)
  }
  return out
}

/**
 * 按收集顺序分组：连续 tag 为一组；每条 text 单独一组（串行吸入）。
 * @param {object[]} sources
 */
function groupSourcesForTimeline(sources) {
  /** @type {Array<{ type: 'tagBatch', items: object[] } | { type: 'text', source: object }>} */
  const groups = []
  let tagBatch = null

  for (const s of sources) {
    if (s.type === 'tag') {
      if (!tagBatch) {
        tagBatch = { type: 'tagBatch', items: [] }
        groups.push(tagBatch)
      }
      tagBatch.items.push(s)
    } else if (s.type === 'text') {
      tagBatch = null
      groups.push({ type: 'text', source: s })
    }
  }
  return groups
}

/**
 * @param {{ root?: ParentNode, mergeSegments?: { positive?: object[], negative?: object[] } | null }} opts
 */
export function collectAbsorbSources({ root = document, mergeSegments = null } = {}) {
  const hasPlan =
    mergeSegments &&
    ((mergeSegments.positive?.length || 0) > 0 ||
      (mergeSegments.negative?.length || 0) > 0)

  if (hasPlan) {
    const fromPlan = collectFromMergePlan(mergeSegments, root)
    if (fromPlan.length) return fromPlan
  }

  return collectLegacySources(root)
}

/** @param {string} text @param {string} [kind] */
function createTextFlyer(text, kind = 'core') {
  const el = document.createElement('span')
  el.className = `tag-absorb-flyer tag-absorb-flyer--text is-${kind}`
  el.textContent = truncateText(text)
  el.setAttribute('aria-hidden', 'true')
  return el
}

/** @param {HTMLElement | null | undefined} el @param {string} kind */
function pulseSourceRegion(el, kind) {
  if (!el) return
  const ring =
    kind === 'global'
      ? '0 0 0 2px hsl(38 92% 50% / 0.55)'
      : kind === 'random'
        ? '0 0 0 2px hsl(152 60% 40% / 0.55)'
        : '0 0 0 2px hsl(199 89% 48% / 0.45)'
  gsap.fromTo(
    el,
    { boxShadow: '0 0 0 0px transparent', scale: 1 },
    {
      boxShadow: ring,
      scale: 1.015,
      duration: 0.14,
      yoyo: true,
      repeat: 1,
      ease: 'power2.out',
      clearProps: 'boxShadow,scale',
    },
  )
}

/**
 * @param {gsap.core.Timeline} tl
 * @param {{ el: HTMLElement, startCenter: {x:number,y:number} }} flyer
 * @param {number} targetX
 * @param {number} targetY
 * @param {HTMLElement | null | undefined} targetEl
 */
function appendTextAbsorbStep(tl, flyer, targetX, targetY, targetEl) {
  const { el, startCenter } = flyer
  const dx = targetX - startCenter.x
  const dy = targetY - startCenter.y

  tl.fromTo(
    el,
    { opacity: 0.35, scale: 0.88, x: 0, y: 0, rotation: 0 },
    { opacity: 1, scale: 1, duration: 0.2, ease: 'power2.out' },
  )
  tl.to(el, {
    x: dx,
    y: dy,
    rotation: gsap.utils.random(-10, 10),
    scale: 0.28,
    opacity: 0,
    duration: 0.58,
    ease: 'power3.in',
  })
  if (targetEl) {
    tl.to(
      targetEl,
      {
        scale: 1.1,
        duration: 0.1,
        ease: 'back.out(2)',
        yoyo: true,
        repeat: 1,
      },
      '<0.15',
    )
  }
  tl.to({}, { duration: 0.14 })
}

/**
 * @param {gsap.core.Timeline} tl
 * @param {{ el: HTMLElement, startCenter: {x:number,y:number} }[]} batch
 * @param {number} targetX
 * @param {number} targetY
 * @param {HTMLElement | null | undefined} targetEl
 */
function appendTagBatchAbsorb(tl, batch, targetX, targetY, targetEl) {
  const els = batch.map((f) => f.el)
  const motions = batch.map(({ startCenter }) => ({
    x: targetX - startCenter.x,
    y: targetY - startCenter.y,
  }))

  tl.to(els, {
    x: () => gsap.utils.random(-6, 6),
    y: () => gsap.utils.random(-4, 4),
    rotation: () => gsap.utils.random(-8, 8),
    scale: () => gsap.utils.random(0.97, 1.05),
    duration: 0.05,
    repeat: 8,
    yoyo: true,
    ease: 'sine.inOut',
  })
  tl.set(els, { x: 0, y: 0, rotation: 0, scale: 1 })
  tl.to(els, {
    x: (i) => motions[i].x,
    y: (i) => motions[i].y,
    rotation: () => gsap.utils.random(-90, 90),
    scale: 0.06,
    opacity: 0,
    duration: 0.62,
    stagger: 0.03,
    ease: 'power3.in',
  })
  if (targetEl) {
    tl.to(
      targetEl,
      {
        scale: 1.14,
        duration: 0.12,
        ease: 'back.out(2.2)',
        yoyo: true,
        repeat: 1,
      },
      '-=0.35',
    )
  }
  tl.to({}, { duration: 0.1 })
}

function buildTextFlyer(source) {
  const flyer = createTextFlyer(source.text, source.kind)
  const { x, y } = rectCenter(source.rect)
  const stack = source.stackIndex ?? 0
  const jitterX = (stack - (source.stackTotal ?? 1) / 2) * 5
  const jitterY = gsap.utils.random(-2, 2)
  const cx = x + jitterX
  const cy = y + jitterY

  gsap.set(flyer, {
    position: 'fixed',
    left: cx,
    top: cy,
    xPercent: -50,
    yPercent: -50,
    width: 'auto',
    maxWidth: Math.min(280, source.rect.width * 0.92 || 240),
    margin: 0,
    zIndex: 10049,
    pointerEvents: 'none',
    transformOrigin: '50% 50%',
    willChange: 'transform, opacity',
    opacity: 0,
    x: 0,
    y: 0,
  })

  document.body.appendChild(flyer)
  return { el: flyer, startCenter: { x: cx, y: cy }, source }
}

function buildTagFlyer(source, tagsToRestore) {
  const startRect = getChipStartRect(source.el)
  const flyer = source.el.cloneNode(true)
  flyer.classList.add('tag-absorb-flyer', 'tag-absorb-flyer--chip')
  flyer.setAttribute('aria-hidden', 'true')

  gsap.set(source.el, { opacity: 0 })
  tagsToRestore.push(source.el)

  gsap.set(flyer, {
    position: 'fixed',
    left: startRect.left,
    top: startRect.top,
    width: startRect.width,
    height: startRect.height,
    margin: 0,
    zIndex: 10050,
    pointerEvents: 'none',
    transformOrigin: '50% 50%',
    willChange: 'transform, opacity',
    boxSizing: 'border-box',
  })

  document.body.appendChild(flyer)
  return { el: flyer, startCenter: rectCenter(startRect), source, isTag: true }
}

/** 延迟渐显复原（tag 原位置 / 被压暗区域） */
function scheduleFadeRestore(elements) {
  const list = [...new Set(elements.filter(Boolean))]
  if (!list.length) return
  list.forEach((el) => {
    gsap.to(el, {
      opacity: 1,
      duration: RESTORE_DURATION,
      delay: RESTORE_DELAY,
      ease: 'power2.out',
      overwrite: 'auto',
    })
  })
}

/**
 * @param {{ targetEl?: HTMLElement | null, root?: ParentNode, mergeSegments?: object | null }} opts
 */
export function playTagAbsorbAnimation({
  targetEl,
  root = document,
  mergeSegments = null,
} = {}) {
  if (prefersReducedMotion()) {
    return Promise.resolve({ played: false })
  }

  const sources = collectAbsorbSources({ root, mergeSegments })
  const targetRect = targetEl?.getBoundingClientRect?.()
  if (!sources.length || !targetRect) {
    return Promise.resolve({ played: false })
  }

  const targetX = targetRect.left + targetRect.width / 2
  const targetY = targetRect.top + targetRect.height / 2

  const groups = groupSourcesForTimeline(sources)
  if (!groups.length) {
    return Promise.resolve({ played: false })
  }

  /** @type {HTMLElement[]} */
  const tagsToRestore = []
  /** @type {HTMLElement[]} */
  const flyersToRemove = []

  return new Promise((resolve) => {
    const tl = gsap.timeline({
      defaults: { ease: 'power2.inOut' },
      onComplete: () => {
        flyersToRemove.forEach((el) => el.remove())
        if (targetEl) gsap.set(targetEl, { clearProps: 'transform' })
        resolve({ played: true })
      },
    })

    for (const group of groups) {
      if (group.type === 'text') {
        const src = group.source
        if (!src?.rect) continue

        pulseSourceRegion(src.highlightEl, src.kind)

        const flyer = buildTextFlyer(src)
        flyersToRemove.push(flyer.el)
        appendTextAbsorbStep(tl, flyer, targetX, targetY, targetEl)
        continue
      }

      if (group.type === 'tagBatch' && group.items.length) {
        const batch = group.items
          .filter((s) => s.el)
          .map((s) => buildTagFlyer(s, tagsToRestore))
        if (!batch.length) continue

        const editor = batch[0].source.el?.closest?.('[data-prompt-tag-editor]')
        pulseSourceRegion(editor, 'core')

        batch.forEach((f) => flyersToRemove.push(f.el))
        appendTagBatchAbsorb(tl, batch, targetX, targetY, targetEl)
      }
    }

    scheduleFadeRestore(tagsToRestore)
  })
}
