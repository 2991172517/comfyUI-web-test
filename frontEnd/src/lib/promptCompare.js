import { displayPromptComma } from '@/lib/promptDisplay.js'

/** 拆成对比用语义片段（与逗号展示一致：先按行再按逗号） */
export function splitPromptSegments(text) {
  if (!text) return []
  const normalized = String(text).replace(/\r\n/g, '\n')
  const lines = normalized.split('\n').map((p) => p.trim()).filter(Boolean)
  const parts = []
  for (const line of lines) {
    for (const piece of line.split(/,\s*/)) {
      const t = piece.trim()
      if (t) parts.push(t)
    }
  }
  return parts
}

function segmentsForItem(meta, side) {
  const full = displayPromptComma(meta, side)
  return { full, segments: splitPromptSegments(full) }
}

function intersectSegments(lists) {
  if (!lists.length) return []
  const [first, ...rest] = lists
  const set = new Set(first)
  for (const seg of [...set]) {
    if (!rest.every((arr) => arr.includes(seg))) set.delete(seg)
  }
  return [...set]
}

function compareSide(items, side) {
  const keyed = items.map((it) => ({
    key: it.key,
    label: it.label,
    ...segmentsForItem(it.meta, side),
  }))

  const segmentLists = keyed.map((k) => k.segments)
  const sameSegments = intersectSegments(segmentLists)

  const union = new Set()
  for (const list of segmentLists) {
    for (const s of list) union.add(s)
  }

  const differentSegments = [...union]
    .filter((s) => !sameSegments.includes(s))
    .map((text) => ({
      text,
      labels: keyed.filter((k) => k.segments.includes(text)).map((k) => k.label),
    }))
    .sort((a, b) => b.labels.length - a.labels.length)

  const allFullSame =
    keyed.length > 0 && keyed.every((k) => k.full === keyed[0].full)

  return {
    allFullSame,
    sameSegments,
    differentSegments,
    perItem: keyed.map((k) => ({
      key: k.key,
      label: k.label,
      full: k.full,
      uniqueSegments: k.segments.filter((s) => !sameSegments.includes(s)),
    })),
  }
}

/**
 * @param {Array<{ key: string, label: string, meta: object }>} items 至少 2 项
 */
export function comparePromptItems(items) {
  if (!items?.length) {
    return { count: 0, positive: null, negative: null }
  }
  return {
    count: items.length,
    positive: compareSide(items, 'positive'),
    negative: compareSide(items, 'negative'),
  }
}

export function cellSelectionKey(cell, ia, ib) {
  if (cell?.index != null) return `i-${cell.index}`
  return `${ia}-${ib}`
}

export function cellSelectionLabel(cell, ia, ib, matrixCols = 0) {
  if (cell?.label) return cell.label
  if (ia != null && ib != null) return `A${ia}×B${ib}`
  const idx = cell?.index ?? (matrixCols ? ia * matrixCols + ib : ia * 99 + ib)
  return `#${idx}`
}
