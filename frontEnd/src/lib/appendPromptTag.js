import { splitPromptTokens } from '@/lib/promptDisplay.js'
import { lookupKeyForVocabulary } from '@/lib/promptTagWeight.js'

/**
 * 向提示词末尾追加词条（逗号分隔，跳过已存在的同义 tag）
 * @returns {{ text: string, added: boolean }}
 */
export function appendPromptTag(text, insertText) {
  const value = String(insertText || '').trim()
  if (!value) return { text: String(text || ''), added: false }

  const key = lookupKeyForVocabulary(value).toLowerCase()
  if (!key) return { text: String(text || ''), added: false }

  const exists = splitPromptTokens(text).some(
    (part) => lookupKeyForVocabulary(part).toLowerCase() === key,
  )
  if (exists) return { text: String(text || ''), added: false }

  const cur = String(text || '').trim()
  if (!cur) return { text: value, added: true }
  const base = cur.replace(/[,，]\s*$/, '')
  return { text: `${base}, ${value}`, added: true }
}

/**
 * 从提示词中移除与 insertText 同义的词条（保留其余 tag 与逗号格式）
 * @returns {{ text: string, removed: boolean }}
 */
export function removePromptTag(text, insertText) {
  const value = String(insertText || '').trim()
  if (!value) return { text: String(text || ''), removed: false }

  const key = lookupKeyForVocabulary(value).toLowerCase()
  if (!key) return { text: String(text || ''), removed: false }

  const tokens = splitPromptTokens(text)
  const filtered = tokens.filter(
    (part) => lookupKeyForVocabulary(part).toLowerCase() !== key,
  )
  if (filtered.length === tokens.length) {
    return { text: String(text || ''), removed: false }
  }
  return { text: filtered.join(', '), removed: true }
}

/** 追加或移除（已存在则移除） */
export function togglePromptTag(text, insertText) {
  const value = String(insertText || '').trim()
  if (!value) return { text: String(text || ''), changed: false, added: false }

  const key = lookupKeyForVocabulary(value).toLowerCase()
  const exists = key
    && splitPromptTokens(text).some(
      (part) => lookupKeyForVocabulary(part).toLowerCase() === key,
    )

  if (exists) {
    const { text: next, removed } = removePromptTag(text, value)
    return { text: next, changed: removed, added: false }
  }
  const { text: next, added } = appendPromptTag(text, value)
  return { text: next, changed: added, added }
}
