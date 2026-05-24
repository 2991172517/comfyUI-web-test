import { computed, ref } from 'vue'
import {
  ECOSYSTEM_MODES,
  applyPaletteToMode,
  loadSavedModeId,
  loadSavedPalette,
  pickRandomPalette,
  saveModeId,
  savePalette,
} from '@/lib/loginEcosystemThemes.js'

const modeId = ref(loadSavedModeId())
const paletteOverride = ref(loadSavedPalette())
const paletteLabel = ref(paletteOverride.value?.name || '')

const activeTheme = computed(() => {
  const base = ECOSYSTEM_MODES[modeId.value] ?? ECOSYSTEM_MODES[0]
  return applyPaletteToMode(base, paletteOverride.value)
})

/** 登录页与各业务页共用的萤火背景主题（localStorage 同步） */
export function useFireflyEcosystemTheme() {
  function setMode(id) {
    modeId.value = id
    paletteOverride.value = null
    paletteLabel.value = ''
    saveModeId(id)
    savePalette(null)
  }

  function randomizeColors() {
    const picked = pickRandomPalette()
    paletteOverride.value = picked
    paletteLabel.value = picked.name || ''
    savePalette(picked)
  }

  function reloadFromStorage() {
    modeId.value = loadSavedModeId()
    paletteOverride.value = loadSavedPalette()
    paletteLabel.value = paletteOverride.value?.name || ''
  }

  return {
    modeId,
    paletteOverride,
    paletteLabel,
    activeTheme,
    ECOSYSTEM_MODES,
    setMode,
    randomizeColors,
    reloadFromStorage,
  }
}
