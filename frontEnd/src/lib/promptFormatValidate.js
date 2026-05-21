/**
 * ComfyUI / CLIP 提示词格式校验
 * 允许：tag、权重 (x:1.2)、@触发词、区域 <|...|>、分隔符等 ComfyUI 常见写法
 */

/** 字母数字与中日韩等 + 空白 + 常见标点与 ComfyUI 扩展符号 */
const ALLOWED_PROMPT_CHAR_RE =
  /[\p{L}\p{N}\s,，.\-_:()\[\]（）【】／/·@|+<>{}#%&*\\'"!?~^;`=$]/u

/** 仍禁止：控制字符（保留换行/制表） */
const CONTROL_CHAR_RE = /[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/u

export function validateComfyPromptText(text) {
  const s = String(text ?? '')
  if (!s.trim()) {
    return { valid: true, issues: [] }
  }

  const issues = []
  const badChars = new Set()

  for (const ch of s) {
    if (ch === '\n' || ch === '\r' || ch === '\t') continue
    if (CONTROL_CHAR_RE.test(ch)) {
      badChars.add(ch === '\t' ? '\\t' : `U+${ch.codePointAt(0).toString(16)}`)
      continue
    }
    if (!ALLOWED_PROMPT_CHAR_RE.test(ch)) {
      badChars.add(ch)
    }
  }

  if (badChars.size) {
    const sample = [...badChars].slice(0, 8).join(' ')
    issues.push(`含不支持字符：${sample}`)
  }

  let depth = 0
  for (const c of s) {
    if (c === '(') depth += 1
    else if (c === ')') {
      depth -= 1
      if (depth < 0) {
        issues.push('括号 ")" 多于 "("')
        break
      }
    }
  }
  if (depth > 0) issues.push('括号 "(" 未闭合')

  return { valid: issues.length === 0, issues }
}

export function isPromptTextField(field) {
  if (!field) return false
  const key = String(field.key || '').toLowerCase()
  return key === 'text'
}

/** 供 UI 展示的允许符号说明 */
export const PROMPT_FORMAT_HINT =
  '支持逗号/换行分 tag、权重 (tag:1.2)、@风格触发、<|emphasis|>、| 分隔等；不支持控制字符。'
