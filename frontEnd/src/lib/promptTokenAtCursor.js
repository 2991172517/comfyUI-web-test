/**
 * 提示词输入框：光标处当前 token 与补全插入
 */

import { canAdjustWeight } from '@/lib/promptTagWeight.js'

/** 去掉权重写法中的数值部分，用于搜索 query，如 (wlop:1.10) → 保留原串由后端匹配 */
export function normalizeTokenForSearch(token) {
  const t = String(token || '').trim()
  if (!t) return ''
  const m = t.match(/^(.+):\d+(?:\.\d+)?$/)
  return (m ? m[1] : t).replace(/[\[\]{}]/g, '').trim()
}

/**
 * @param {string} text
 * @param {number} cursor
 */
export function getTokenAtCursor(text, cursor) {
  const left = String(text || '').slice(0, cursor)
  const m = left.match(/([^,，]+)$/)
  const raw = m ? m[1] : ''
  const token = raw.trimStart()
  const tokenStart = cursor - token.length
  return { token, tokenStart, tokenEnd: cursor }
}

/**
 * @param {string} text
 * @param {{ tokenStart: number, tokenEnd: number }} range
 * @param {string} insertText
 */
export function applyTokenCompletion(text, range, insertText) {
  const before = text.slice(0, range.tokenStart)
  const after = text.slice(range.tokenEnd)
  const sep = after && !/^[\s,，]/.test(after) ? ', ' : ''
  const inserted = insertText + sep
  return {
    newText: before + inserted + after,
    newCursor: range.tokenStart + inserted.length,
  }
}

/** 词条是否已有括号/方括号权重包装 */
export function isTokenWeightWrapped(token) {
  const t = String(token || '').trim()
  if (!t) return false
  return t.startsWith('(') || t.startsWith('[')
}

/**
 * 文本/补全模式：输入 `:` 时给当前词条加 `(tag:)` 权重包装
 * @returns {{ newText: string, newCursor: number } | null}
 */
export function applyColonWeightWrap(text, cursor) {
  const { token, tokenStart, tokenEnd } = getTokenAtCursor(text, cursor)
  const t = token.trim()
  if (!t) return null

  if (/^\([^()]+:[\d.]*\)$/.test(t)) return null

  const parenOnly = t.match(/^\(([^()[\]]+)\)$/)
  if (parenOnly) {
    const inner = parenOnly[1].trim()
    if (!inner || !canAdjustWeight(inner)) return null
    const wrapped = `(${inner}:)`
    const before = text.slice(0, tokenStart)
    const after = text.slice(tokenEnd)
    return {
      newText: before + wrapped + after,
      newCursor: tokenStart + wrapped.length - 1,
    }
  }

  if (t.startsWith('(') || t.startsWith('[')) return null
  if (!canAdjustWeight(t)) return null

  const wrapped = `(${t}:)`
  const before = text.slice(0, tokenStart)
  const after = text.slice(tokenEnd)
  return {
    newText: before + wrapped + after,
    newCursor: tokenStart + wrapped.length - 1,
  }
}

/**
 * Backspace / Delete 去掉 `:` 时，移除 `(tag:…)` 包装
 * @param {string} text
 * @param {number} cursor 光标位置（Backspace 时在 `:` 之后，Delete 时在 `:` 之前）
 * @returns {{ newText: string, newCursor: number } | null}
 */
export function applyColonWeightUnwrap(text, cursor) {
  if (cursor <= 0 || cursor > text.length) return null

  let colonIndex = -1
  if (text[cursor - 1] === ':' || text[cursor - 1] === '：') {
    colonIndex = cursor - 1
  } else if (text[cursor] === ':' || text[cursor] === '：') {
    colonIndex = cursor
  } else {
    return null
  }

  const beforeColon = text.slice(0, colonIndex)
  const afterColon = text.slice(colonIndex + 1)

  const openMatch = beforeColon.match(/\(([^(),[\]]+)$/)
  if (!openMatch) return null
  const base = openMatch[1].trim()
  if (!base || !canAdjustWeight(base)) return null

  const openParenIndex = beforeColon.lastIndexOf('(')
  const closeMatch = afterColon.match(/^([\d.]*)?\)/)
  if (!closeMatch) return null

  const endIndex = colonIndex + 1 + closeMatch[0].length
  const before = text.slice(0, openParenIndex)
  const after = text.slice(endIndex)

  return {
    newText: before + base + after,
    newCursor: openParenIndex + base.length,
  }
}

/** @deprecated 使用 applyColonWeightWrap */
export function applyDotWeightWrap(text, cursor) {
  return applyColonWeightWrap(text, cursor)
}
