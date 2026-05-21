import { ref } from 'vue'
import { api } from '../api/client.js'

export function favoriteKeyFromPayload(payload) {
  const img = payload?.image || {}
  return [
    payload?.workflow_id || '',
    img.subfolder || '',
    img.filename || '',
    payload?.prompt_id || '',
    payload?.batch_id || '',
    payload?.grid_ia ?? '',
    payload?.grid_ib ?? '',
  ].join('|')
}

export function favoriteKeyFromEntry(entry) {
  return favoriteKeyFromPayload({
    workflow_id: entry.workflow_id,
    image: entry.image,
    prompt_id: entry.prompt_id,
    batch_id: entry.batch_id,
    grid_ia: entry.grid_ia,
    grid_ib: entry.grid_ib,
  })
}

const favoriteKeys = ref(new Set())

export function useFavorites() {
  async function refreshFavorites() {
    const res = await api.listFavorites()
    const keys = new Set()
    for (const f of res.favorites || []) {
      keys.add(favoriteKeyFromEntry(f))
    }
    favoriteKeys.value = keys
    return res.favorites || []
  }

  function isFavorited(payload) {
    return favoriteKeys.value.has(favoriteKeyFromPayload(payload))
  }

  async function toggleFavorite(payload) {
    const res = await api.toggleFavorite(payload)
    await refreshFavorites()
    return res
  }

  return {
    favoriteKeys,
    refreshFavorites,
    isFavorited,
    toggleFavorite,
  }
}
