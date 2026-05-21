/**
 * 随机参考词组：词条解析与模式说明（与后端 reference_pick_service 一致）
 */

const COMMA_SPLIT = /[,，]\s*/
const SLASH_SPLIT = /\s*\/\s*/

/** @param {string} text */
export function splitPromptTokens(text) {
  const s = String(text || '').trim()
  if (!s) return []
  if (COMMA_SPLIT.test(s)) {
    return s.split(COMMA_SPLIT).map((p) => p.trim()).filter(Boolean)
  }
  if (s.includes('/')) {
    return s.split(SLASH_SPLIT).map((p) => p.trim()).filter(Boolean)
  }
  return [s]
}

/** @param {string[]} tokens */
export function joinPromptTokens(tokens) {
  return tokens.filter((t) => String(t).trim()).join(', ')
}

/** @param {{ prompts?: string[] }} group */
export function countCandidates(group) {
  return (group.prompts || []).map((p) => String(p).trim()).filter(Boolean).length
}

/**
 * @param {{ prompts?: string[] }} group
 * @returns {'pool' | 'schemes'}
 */
export function randomGroupMode(group) {
  return countCandidates(group) <= 1 ? 'pool' : 'schemes'
}

/** @param {{ prompts?: string[] }} group */
export function groupModeDescription(group) {
  const n = countCandidates(group)
  const side = group.target === 'negative' ? '负向' : '正向'
  if (n <= 1) {
    const line = (group.prompts || []).find((p) => String(p).trim()) || ''
    const k = splitPromptTokens(line).length
    return `词条池模式：从逗号分隔的 ${k || '…'} 个词条中每次随机选 1 个，追加到${side}提示。`
  }
  return `多方案模式：共 ${n} 条候选方案，每次随机选 1 条，并将该方案内全部逗号分隔词条一并追加到${side}提示。`
}

/** @param {{ prompts?: string[] }} group */
export function groupModeBadge(group) {
  const n = countCandidates(group)
  if (n <= 1) {
    const line = (group.prompts || []).find((p) => String(p).trim()) || ''
    const k = splitPromptTokens(line).length
    return `词条池 · ${k} 词`
  }
  return `多方案 · ${n} 条候选`
}
