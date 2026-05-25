import { computed, ref } from 'vue'
import { api } from '@/api/client.js'

const SESSION_KEY = 'custom_project_session_gacha_animation'

const globalEnabled = ref(true)
let globalLoaded = false

function readSessionOverride() {
  try {
    const v = localStorage.getItem(SESSION_KEY)
    if (v === '1') return true
    if (v === '0') return false
  } catch {
    /* ignore */
  }
  return null
}

const sessionOverride = ref(readSessionOverride())

export async function loadGachaAnimationGlobal() {
  try {
    const res = await api.getGlobalPromptConfig()
    globalEnabled.value = res?.config?.gacha_animation_enabled !== false
    globalLoaded = true
  } catch {
    globalEnabled.value = true
  }
}

export function useGachaAnimation() {
  const effectiveEnabled = computed(() => {
    if (sessionOverride.value !== null) return sessionOverride.value
    return globalEnabled.value
  })

  function setSessionOverride(enabled) {
    sessionOverride.value = enabled
    try {
      localStorage.setItem(SESSION_KEY, enabled ? '1' : '0')
    } catch {
      /* ignore */
    }
  }

  function clearSessionOverride() {
    sessionOverride.value = null
    try {
      localStorage.removeItem(SESSION_KEY)
    } catch {
      /* ignore */
    }
  }

  function setGlobalEnabled(enabled) {
    globalEnabled.value = !!enabled
    globalLoaded = true
  }

  return {
    globalEnabled,
    globalLoaded,
    sessionOverride,
    effectiveEnabled,
    setSessionOverride,
    clearSessionOverride,
    setGlobalEnabled,
    loadGachaAnimationGlobal,
  }
}
