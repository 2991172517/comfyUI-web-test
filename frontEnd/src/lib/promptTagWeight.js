/**
 * ComfyUI / A1111 提示词权重解析（与社区手册一致）
 * - (tag:1.2) 显式权重
 * - (tag) 等价 (tag:1.1)
 * - 嵌套括号权重相乘，如 ((tag)) → 1.21
 * - [tag] 降权，每层 ×0.9（粘贴常见；调节时规范为 (tag:weight)）
 */

const WEIGHT_MIN = 0.05
const WEIGHT_MAX = 2.0
const WEIGHT_STEP = 0.05
const WEIGHT_EPS = 0.001
const PAREN_DEFAULT = 1.1
const BRACKET_FACTOR = 0.9

/**
 * @param {string} value
 * @returns {{ base: string, weight: number }}
 */
export function parseTagWeight(value) {
  let t = String(value || '').trim()
  if (!t) return { base: '', weight: 1 }

  let weight = 1

  while (t.startsWith('[') && t.endsWith(']')) {
    const inner = t.slice(1, -1).trim()
    if (!inner || inner.includes('[')) break
    weight *= BRACKET_FACTOR
    t = inner
  }

  while (t.startsWith('(') && t.endsWith(')')) {
    const inner = t.slice(1, -1).trim()
    if (!inner) break

    const explicit = inner.match(/^(.+):([\d.]+)$/)
    if (explicit && !explicit[1].includes('(')) {
      t = explicit[1].trim()
      weight *= parseFloat(explicit[2])
      break
    }

    weight *= PAREN_DEFAULT
    t = inner
  }

  return { base: t, weight: clampWeight(weight) }
}

/**
 * 写入 ComfyUI 推荐的显式 (base:weight) 形式
 * @param {string} base
 * @param {number} weight
 */
export function formatTagValue(base, weight = 1) {
  const b = String(base || '').trim()
  if (!b) return ''
  const w = clampWeight(weight)
  if (Math.abs(w - 1) < WEIGHT_EPS) return b
  return `(${b}:${w.toFixed(2)})`
}

export function clampWeight(w) {
  const n = Number(w)
  if (!Number.isFinite(n)) return 1
  return Math.min(WEIGHT_MAX, Math.max(WEIGHT_MIN, Math.round(n / WEIGHT_STEP) * WEIGHT_STEP))
}

/** 复杂词条（含逗号、过长）不调节权重、不显示柱条 */
export function canAdjustWeight(value) {
  const t = String(value || '').trim()
  if (!t || t.length > 120) return false
  if (t.includes(',') || t.includes('，')) return false
  return true
}

/** 查词库用：去掉括号/方括号包装后的英文本体 */
export function lookupKeyForVocabulary(value) {
  if (!canAdjustWeight(value)) return String(value || '').trim()
  const { base } = parseTagWeight(value)
  return base || String(value || '').trim()
}

export function adjustWeight(value, deltaSteps) {
  if (!canAdjustWeight(value)) return value
  const { base, weight } = parseTagWeight(value)
  if (!base) return value
  return formatTagValue(base, clampWeight(weight + deltaSteps * WEIGHT_STEP))
}

/** 柱条高度 12%～100%，权重 1.0 约在中间（旧版侧栏用） */
export function weightBarPercent(weight) {
  const w = clampWeight(weight)
  const t = (w - WEIGHT_MIN) / (WEIGHT_MAX - WEIGHT_MIN)
  return Math.round(12 + t * 88)
}

/** 是否为默认权重 1.0（无彩色柱，仅分隔线） */
export function isDefaultWeight(weight) {
  return Math.abs(clampWeight(weight) - 1) < WEIGHT_EPS
}

/** 原始中线位置（文字层固定 50/50，此值仅用于背景） */
export const WEIGHT_CENTER_LINE = 50

/** 液面线距顶部 %；增权 → 0（顶），减权 → 100（底） */
export function weightActiveLineFromTopPercent(weight) {
  const w = clampWeight(weight)
  const c = WEIGHT_CENTER_LINE
  if (isDefaultWeight(w)) return c
  if (w > 1) {
    const u = (w - 1) / (WEIGHT_MAX - 1)
    return c - u * c
  }
  const u = (1 - w) / (1 - WEIGHT_MIN)
  return c + u * (100 - c)
}

export function weightActiveLineStyle(weight) {
  return {
    top: `${weightActiveLineFromTopPercent(weight)}%`,
    transition: 'top 0.22s ease-out',
  }
}

/** 蓝光区：液面线 → 原始中线 */
export function weightBlueZoneStyle(weight) {
  const w = clampWeight(weight)
  if (w <= 1 + WEIGHT_EPS) return null
  const top = weightActiveLineFromTopPercent(w)
  const h = WEIGHT_CENTER_LINE - top
  if (h <= 0) return null
  return { top: `${top}%`, height: `${h}%` }
}

/** 红光区：原始中线 → 液面线 */
export function weightRedZoneStyle(weight) {
  const w = clampWeight(weight)
  if (w >= 1 - WEIGHT_EPS) return null
  const line = weightActiveLineFromTopPercent(w)
  const h = line - WEIGHT_CENTER_LINE
  if (h <= 0) return null
  return { top: `${WEIGHT_CENTER_LINE}%`, height: `${h}%` }
}

/** 英文栏预留宽度用：按最大权重格式化后的字符串 */
export function tagValueReservedText(value) {
  const { base } = parseTagWeight(value)
  const b = base || String(value || '').trim()
  return formatTagValue(b, WEIGHT_MAX)
}

export function getTagWeight(value) {
  return parseTagWeight(value).weight
}

export { WEIGHT_STEP, WEIGHT_MIN, WEIGHT_MAX, WEIGHT_EPS, PAREN_DEFAULT, BRACKET_FACTOR }
