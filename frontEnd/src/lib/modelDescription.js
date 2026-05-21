/** 与后端 source_url_utils 一致的说明首行链接 */

const PREFIX = '访问链接:'

export function normalizeSourceUrl(url) {
  const u = (url || '').trim()
  if (!u) return ''
  if (/^https?:\/\//i.test(u)) return u
  return `https://${u.replace(/^\/+/, '')}`
}

export function prependSourceUrl(sourceUrl, body) {
  const url = normalizeSourceUrl(sourceUrl)
  const text = (body || '').trim()
  if (!url) return text
  const line = `${PREFIX} ${url}`
  if (text.startsWith(line)) return text
  const first = text.split('\n')[0]?.trim() || ''
  if (first === url || /^https?:\/\//i.test(first)) return text
  return text ? `${line}\n\n${text}` : line
}

export function splitSourceUrl(text) {
  const raw = text || ''
  if (!raw.trim()) return { sourceUrl: null, content: raw }
  const lines = raw.split('\n')
  const first = lines[0]?.trim() || ''
  if (first.startsWith(PREFIX)) {
    const url = normalizeSourceUrl(first.slice(PREFIX.length).trim())
    return { sourceUrl: url || null, content: lines.slice(1).join('\n').replace(/^\n+/, '') }
  }
  if (/^https?:\/\//i.test(first)) {
    return { sourceUrl: first, content: lines.slice(1).join('\n').replace(/^\n+/, '') }
  }
  return { sourceUrl: null, content: raw }
}
