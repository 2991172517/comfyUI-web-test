import { computed, ref, watch } from 'vue'

const STORAGE_KEY = 'custom_project_ui_font_scale'

export const UI_FONT_SCALE_PRESETS = [
  { id: 'compact', label: '紧凑', rootPx: 14, hint: '14px 基准' },
  { id: 'default', label: '标准', rootPx: 16, hint: '16px 基准' },
  { id: 'comfortable', label: '舒适', rootPx: 18, hint: '18px 基准' },
  { id: 'large', label: '大号', rootPx: 20, hint: '20px 基准' },
]

export const UI_FONT_SCALE_DEFAULT = 'default'

const presetById = Object.fromEntries(UI_FONT_SCALE_PRESETS.map((p) => [p.id, p]))

function readStored() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    const id = raw || UI_FONT_SCALE_DEFAULT
    return presetById[id] ? id : UI_FONT_SCALE_DEFAULT
  } catch {
    return UI_FONT_SCALE_DEFAULT
  }
}

export function applyUiFontScale(presetId) {
  if (typeof document === 'undefined') return
  const preset = presetById[presetId] ?? presetById[UI_FONT_SCALE_DEFAULT]
  document.documentElement.style.fontSize = `${preset.rootPx}px`
  document.documentElement.dataset.uiFontScale = preset.id
}

const presetIdRef = ref(readStored())

watch(presetIdRef, (id) => {
  const safeId = presetById[id] ? id : UI_FONT_SCALE_DEFAULT
  applyUiFontScale(safeId)
  try {
    localStorage.setItem(STORAGE_KEY, safeId)
  } catch {
    /* ignore */
  }
})

/** 应用启动时尽早调用，避免字号闪烁 */
export function initUiFontScale() {
  applyUiFontScale(presetIdRef.value)
}

export function useUiFontScale() {
  const presetId = computed({
    get: () => presetIdRef.value,
    set: (v) => {
      presetIdRef.value = presetById[v] ? v : UI_FONT_SCALE_DEFAULT
    },
  })

  const activePreset = computed(
    () => presetById[presetIdRef.value] ?? presetById[UI_FONT_SCALE_DEFAULT],
  )

  function resetToDefault() {
    presetIdRef.value = UI_FONT_SCALE_DEFAULT
  }

  return {
    presetId,
    activePreset,
    presets: UI_FONT_SCALE_PRESETS,
    resetToDefault,
  }
}
