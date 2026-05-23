/** 与后端 reference_pick_service.MUTED_TOKEN_PREFIX 一致 */
export const MUTED_TOKEN_PREFIX = '!'

export function isMutedStoredToken(token) {
  const t = String(token || '').trim()
  return t.startsWith(MUTED_TOKEN_PREFIX)
}

export function stripMutedStoredToken(token) {
  const t = String(token || '').trim()
  if (isMutedStoredToken(t)) return t.slice(MUTED_TOKEN_PREFIX.length).trim()
  return t
}

export function encodeMutedStoredToken(value) {
  const v = String(value || '').trim()
  if (!v) return ''
  return `${MUTED_TOKEN_PREFIX}${v}`
}

/** @returns {{ value: string, muted: boolean }} */
export function parseStoredPromptToken(raw) {
  const t = String(raw || '').trim()
  if (!t) return { value: '', muted: false }
  if (isMutedStoredToken(t)) {
    const value = stripMutedStoredToken(t)
    return { value, muted: !!value }
  }
  return { value: t, muted: false }
}
