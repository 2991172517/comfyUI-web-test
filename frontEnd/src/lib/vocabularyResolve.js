import { api } from '@/api/client.js'
import { getTagWeight } from '@/lib/promptTagWeight.js'

const RESOLVE_CHUNK = 500

/** @type {Map<string, { known: boolean, label: string, value: string }>} */
const cache = new Map()

function cacheKey(value) {
  return String(value || '').trim().toLowerCase()
}

function normalizeLabel(label) {
  const text = String(label || '').trim()
  return text === '-' ? '' : text
}

function storeItems(items) {
  for (const item of items || []) {
    const key = cacheKey(item.value)
    if (!key) continue
    cache.set(key, {
      value: item.value,
      known: !!item.known,
      label: normalizeLabel(item.known ? item.label : ''),
    })
  }
}

export function clearVocabularyResolveCache() {
  cache.clear()
}

export function readVocabularyResolveCache(value) {
  return cache.get(cacheKey(value)) || null
}

/** 批量 resolve，自动分块并写入缓存 */
export async function resolveVocabularyValues(values) {
  const list = (values || []).map((v) => String(v || '').trim()).filter(Boolean)
  if (!list.length) return []

  const allItems = []
  for (let i = 0; i < list.length; i += RESOLVE_CHUNK) {
    const chunk = list.slice(i, i + RESOLVE_CHUNK)
    const res = await api.vocabularyResolve(chunk)
    allItems.push(...(res.items || []))
  }
  storeItems(allItems)
  return allItems
}

export function resolvedItemToTag(item, id = crypto.randomUUID()) {
  const v = item.value
  const known = !!item.known
  const label = normalizeLabel(item.label)
  return {
    id,
    value: v,
    label,
    known: known && !!label,
    weight: getTagWeight(v),
    muted: false,
  }
}

export async function resolveLabelForValue(rawValue) {
  const v = String(rawValue || '').trim()
  if (!v) return { known: false, label: '' }

  const cached = readVocabularyResolveCache(v)
  if (cached) {
    return { known: cached.known && !!cached.label, label: cached.label }
  }

  const items = await resolveVocabularyValues([v])
  const item = items[0]
  if (!item) return { known: false, label: '' }
  const label = normalizeLabel(item.label)
  return { known: !!item.known && !!label, label }
}
