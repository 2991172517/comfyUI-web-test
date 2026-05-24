import { computed, ref, watch } from 'vue'

const STORAGE_KEY = 'custom_project_magnifier_settings'

/** 设置页预览用示例图（public 静态资源） */
export const MAGNIFIER_PREVIEW_SAMPLE = `${import.meta.env.BASE_URL}bg-images/coolbackgrounds-fractalize-spectrum.png`

export const MAGNIFIER_DEFAULTS = {
  lensSize: 180,
  borderWidth: 2,
  zoom: 2.5,
}

/** 悬停多久后才显示放大镜（毫秒），便于先滚轮浏览页面 */
export const MAGNIFIER_SHOW_DELAY_MS = 1000

const LIMITS = {
  lensSize: { min: 100, max: 320, step: 4 },
  borderWidth: { min: 1, max: 8, step: 1 },
  zoom: { min: 1, max: 5, step: 0.1, wheelStep: 0.5 },
}

function clamp(n, min, max) {
  return Math.min(max, Math.max(min, n))
}

function readStored() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return { ...MAGNIFIER_DEFAULTS }
    const p = JSON.parse(raw)
    return {
      lensSize: clamp(
        Number(p.lensSize) || MAGNIFIER_DEFAULTS.lensSize,
        LIMITS.lensSize.min,
        LIMITS.lensSize.max,
      ),
      borderWidth: clamp(
        Number(p.borderWidth) || MAGNIFIER_DEFAULTS.borderWidth,
        LIMITS.borderWidth.min,
        LIMITS.borderWidth.max,
      ),
      zoom: clamp(
        Number(p.zoom) || MAGNIFIER_DEFAULTS.zoom,
        LIMITS.zoom.min,
        LIMITS.zoom.max,
      ),
    }
  } catch {
    return { ...MAGNIFIER_DEFAULTS }
  }
}

const settingsRef = ref(readStored())

watch(
  settingsRef,
  (s) => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(s))
    } catch {
      /* ignore */
    }
  },
  { deep: true },
)

export function useMagnifierSettings() {
  const lensSize = computed({
    get: () => settingsRef.value.lensSize,
    set: (v) => {
      settingsRef.value = {
        ...settingsRef.value,
        lensSize: clamp(Number(v), LIMITS.lensSize.min, LIMITS.lensSize.max),
      }
    },
  })

  const borderWidth = computed({
    get: () => settingsRef.value.borderWidth,
    set: (v) => {
      settingsRef.value = {
        ...settingsRef.value,
        borderWidth: clamp(Number(v), LIMITS.borderWidth.min, LIMITS.borderWidth.max),
      }
    },
  })

  const zoom = computed({
    get: () => settingsRef.value.zoom,
    set: (v) => {
      settingsRef.value = {
        ...settingsRef.value,
        zoom: clamp(Number(v), LIMITS.zoom.min, LIMITS.zoom.max),
      }
    },
  })

  function resetToDefaults() {
    settingsRef.value = { ...MAGNIFIER_DEFAULTS }
  }

  return {
    settingsRef,
    lensSize,
    borderWidth,
    zoom,
    limits: LIMITS,
    resetToDefaults,
  }
}
