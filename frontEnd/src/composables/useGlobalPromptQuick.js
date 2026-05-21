import { computed, ref } from 'vue'
import { api } from '@/api/client.js'
import {
  emptyBatchPromptConfig,
  globalConfigToPromptLayers,
  globalRandomGroupsActive,
  globalRandomGroupsCounts,
  formatGlobalRandomSummary,
  applyGlobalRandomGroupsMaster,
  serializeGlobalPromptConfig,
} from '@/composables/usePromptConfig.js'

/** 全局提示词保存后递增，供摘要栏 / 合并预览刷新 */
export const globalPromptRevision = ref(0)

let skipBarReloadOnce = false

function bumpRevision() {
  globalPromptRevision.value += 1
}

const cfg = ref(emptyBatchPromptConfig())
const loading = ref(false)
const saving = ref(false)
let randomGroupSnapshot = null

function buildSummary(g) {
  const pos = (g.positive || '').trim()
  const neg = (g.negative || '').trim()
  const { on: rndOn, total: rndTotal } = globalRandomGroupsCounts(g)
  const random = formatGlobalRandomSummary(g)
  return {
    enabled: g.enabled !== false,
    randomActive: random.active,
    randomText: random.text,
    pos: pos ? `正: ${pos.slice(0, 40)}${pos.length > 40 ? '…' : ''}` : '正: （空）',
    neg: neg ? `负: ${neg.slice(0, 40)}${neg.length > 40 ? '…' : ''}` : '负: （空）',
    rnd: rndOn,
    rndTotal,
    merge: [
      g.merge?.global_before_workflow ? '全局在前' : '',
      g.merge?.random_before_workflow ? '随机在前' : '',
    ]
      .filter(Boolean)
      .join(' · ') || '默认顺序',
  }
}

const summary = computed(() => buildSummary(cfg.value))

/** 设置页等外部保存后调用，生成页摘要栏会重新拉取 */
export function notifyGlobalPromptSaved() {
  skipBarReloadOnce = false
  bumpRevision()
}

export function useGlobalPromptQuick() {
  async function load() {
    loading.value = true
    try {
      const res = await api.getGlobalPromptConfig()
      cfg.value = globalConfigToPromptLayers(res.config)
      randomGroupSnapshot = null
    } catch {
      cfg.value = emptyBatchPromptConfig()
    } finally {
      loading.value = false
    }
  }

  async function saveFromCfg() {
    saving.value = true
    try {
      const res = await api.saveGlobalPromptConfig(serializeGlobalPromptConfig(cfg.value))
      cfg.value = globalConfigToPromptLayers(res.config)
      skipBarReloadOnce = true
      bumpRevision()
    } finally {
      saving.value = false
    }
  }

  function shouldSkipBarReload() {
    if (!skipBarReloadOnce) return false
    skipBarReloadOnce = false
    return true
  }

  async function setGlobalEnabled(enabled) {
    if (loading.value) return
    cfg.value.enabled = !!enabled
    await saveFromCfg()
  }

  async function setRandomGroupsMaster(enabled) {
    if (loading.value) return
    if (!enabled) {
      randomGroupSnapshot = applyGlobalRandomGroupsMaster(cfg.value, false)
    } else {
      randomGroupSnapshot = applyGlobalRandomGroupsMaster(
        cfg.value,
        true,
        randomGroupSnapshot,
      )
      randomGroupSnapshot = null
    }
    await saveFromCfg()
  }

  return {
    cfg,
    loading,
    saving,
    summary,
    load,
    setGlobalEnabled,
    setRandomGroupsMaster,
    shouldSkipBarReload,
  }
}
