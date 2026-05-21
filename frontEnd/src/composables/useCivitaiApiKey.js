const STORAGE_KEY = 'comfyui-custom-project-civitai-api-key'

export function loadCivitaiApiKey() {
  try {
    return (localStorage.getItem(STORAGE_KEY) || '').trim()
  } catch {
    return ''
  }
}

export function saveCivitaiApiKey(token) {
  const v = (token || '').trim()
  try {
    if (v) localStorage.setItem(STORAGE_KEY, v)
    else localStorage.removeItem(STORAGE_KEY)
  } catch {
    /* private mode / quota */
  }
  return v
}

export function hasCivitaiApiKey(token) {
  return !!(token || '').trim()
}
