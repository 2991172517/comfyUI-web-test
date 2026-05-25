import { computed, ref } from 'vue'

const STORAGE_KEY = 'custom_project_session_bundle_groups_enabled'

function readInitial() {
  try {
    const v = localStorage.getItem(STORAGE_KEY)
    if (v === '0') return false
  } catch {
    /* ignore */
  }
  return true
}

const enabled = ref(readInitial())

export function useSessionBundleGroups() {
  const masterEnabled = computed({
    get: () => enabled.value,
    set: (v) => {
      enabled.value = !!v
      try {
        localStorage.setItem(STORAGE_KEY, enabled.value ? '1' : '0')
      } catch {
        /* ignore */
      }
    },
  })

  return { masterEnabled }
}
