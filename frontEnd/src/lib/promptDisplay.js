import { isMutedStoredToken } from '@/lib/promptMutedTag.js'
import { lookupKeyForVocabulary } from '@/lib/promptTagWeight.js'

/** 与后端 split_prompt_tokens 一致：优先按逗号拆词条 */
const COMMA_RE = /[,，]\s*/

export function splitPromptTokens(text) {
  const s = String(text ?? '').trim()
  if (!s) return []
  if (COMMA_RE.test(s)) {
    return s.split(COMMA_RE).map((p) => p.trim()).filter(Boolean)
  }
  if (/\s\/\s*|\/\S|\S\//.test(s)) {
    return s.split(/\s*\/\s*/).map((p) => p.trim()).filter(Boolean)
  }
  return [s]
}

/** O(n) 有序去重（与后端 dedupe_prompt_tokens 一致） */
export function dedupePromptTokens(tokens) {
  const seen = new Set()
  const out = []
  let removed = 0
  for (const raw of tokens) {
    const t = String(raw).trim()
    if (!t || isMutedStoredToken(t)) continue
    const key = lookupKeyForVocabulary(t).toLowerCase()
    if (!key) continue
    if (seen.has(key)) {
      removed += 1
      continue
    }
    seen.add(key)
    out.push(t)
  }
  return { tokens: out, removed }
}

/** 多行合并结果 → 单行逗号 tag（按词条拆，避免「行末逗号 + 按行拼接」产生 ,,） */
export function promptToComma(text) {
  if (!text) return ''
  const tokens = []
  for (const line of String(text).replace(/\r\n/g, '\n').split('\n')) {
    tokens.push(...splitPromptTokens(line))
  }
  return dedupePromptTokens(tokens).tokens.join(', ')
}

/** 与提交 ComfyUI 前 dedupe_prompt_text 一致（仅展示/离线用；入队以后端为准） */
export function dedupePromptText(text) {
  const tokens = []
  for (const line of String(text || '').replace(/\r\n/g, '\n').split('\n')) {
    tokens.push(...splitPromptTokens(line))
  }
  const { tokens: deduped, removed } = dedupePromptTokens(tokens)
  return { text: deduped.join(', '), removed }
}

/** 历史/收藏详情：始终从原文重算，不用入库时旧版 comma 字段 */
export function displayPromptComma(meta, side) {
  const key = side === 'negative' ? 'prompt_negative' : 'prompt_positive'
  return promptToComma(meta?.[key])
}
