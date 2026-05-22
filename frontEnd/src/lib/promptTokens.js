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
export function groupPickModeLabel(group) {
  return group?.pick_mode === 'sequential' ? '顺序' : '随机'
}

export function groupModeDescription(group) {
  const n = countCandidates(group)
  const side = group.target === 'negative' ? '负向' : '正向'
  const mode = group.pick_mode === 'sequential' ? 'sequential' : 'random'
  if (n <= 1) {
    const line = (group.prompts || []).find((p) => String(p).trim()) || ''
    const k = splitPromptTokens(line).length
    if (mode === 'sequential') {
      return `词条池 · 顺序：按生成序号从 ${k || '…'} 个词条依次取 1 个（循环），追加到${side}。`
    }
    return `词条池 · 随机：从 ${k || '…'} 个词条中按权重抽 1 个，追加到${side}。未设权重默认为 1。`
  }
  if (mode === 'sequential') {
    return `多方案 · 顺序：共 ${n} 条方案，按生成序号依次选用（循环），方案内全部词条一并追加到${side}。`
  }
  return `多方案 · 随机：共 ${n} 条方案，按权重抽 1 条，方案内全部词条追加到${side}。未设权重默认为 1。`
}

/** @param {{ prompts?: string[] }} group */
export function groupModeBadge(group) {
  const n = countCandidates(group)
  const pick = groupPickModeLabel(group)
  if (n <= 1) {
    const line = (group.prompts || []).find((p) => String(p).trim()) || ''
    const k = splitPromptTokens(line).length
    return `${pick} · 池 ${k} 词`
  }
  return `${pick} · ${n} 方案`
}
