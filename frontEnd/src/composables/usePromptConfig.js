/** 提示词配置：当次/预设/全局 统一结构 */

import { splitPromptTokens } from '@/lib/promptTokens.js'

export function emptyMergeOptions() {
  return {
    global_before_workflow: false,
    random_before_workflow: false,
  }
}

export function emptyFixedSides() {
  return {
    positive: { prefix: '', suffix: '' },
    negative: { prefix: '', suffix: '' },
  }
}

export function emptyBatchPromptConfig() {
  return {
    enabled: true,
    positive: '',
    negative: '',
    fixed: emptyFixedSides(),
    random_groups: [],
    random_bundle_groups: [],
    merge: emptyMergeOptions(),
  }
}

export function newRandomGroup(name = '') {
  return {
    id: `g_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 6)}`,
    name: name || '新随机组',
    enabled: true,
    target: 'positive',
    pick_mode: 'random',
    prompts: [''],
    weights: [1],
  }
}

export function newRandomBundle(alias = '') {
  return {
    id: `b_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 6)}`,
    alias: alias || '新词条',
    text: '',
  }
}

export function newRandomBundleGroup(name = '') {
  return {
    id: `bg_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 6)}`,
    name: name || '新随机词串组',
    enabled: true,
    target: 'positive',
    pick_mode: 'random',
    bundles: [newRandomBundle()],
    weights: [1],
  }
}

function normalizeWeight(value, fallback = 1) {
  const n = Number(value)
  if (!Number.isFinite(n) || n < 0) return fallback
  return n
}

function weightSlotCount(prompts) {
  const lines = (prompts || []).map((p) => String(p).trim()).filter(Boolean)
  if (lines.length <= 1) {
    return Math.max(splitPromptTokens(lines[0] || '').length, 1)
  }
  return lines.length
}

function normalizeGroupWeights(prompts, rawWeights) {
  const n = weightSlotCount(prompts)
  const weights = []
  for (let i = 0; i < n; i++) {
    weights.push(normalizeWeight(rawWeights?.[i], 1))
  }
  return weights
}

/** @param {object} raw API / store 数据 */
export function normalizePromptConfig(raw) {
  const base = emptyBatchPromptConfig()
  if (!raw) return base
  base.enabled = raw.enabled !== false
  base.positive = String(raw.positive ?? '')
  base.negative = String(raw.negative ?? '')
  const fixed = raw.fixed || {}
  for (const side of ['positive', 'negative']) {
    base.fixed[side] = {
      prefix: fixed[side]?.prefix ?? '',
      suffix: fixed[side]?.suffix ?? '',
    }
  }
  const merge = raw.merge || {}
  base.merge = {
    global_before_workflow: !!merge.global_before_workflow,
    random_before_workflow: !!merge.random_before_workflow,
  }
  base.random_groups = (raw.random_groups || []).map((g) => {
    const prompts = (g.prompts?.length ? g.prompts : ['']).map(String)
    const pickMode = g.pick_mode === 'sequential' ? 'sequential' : 'random'
    return {
      id: g.id || newRandomGroup().id,
      name: g.name || '未命名组',
      enabled: g.enabled !== false,
      target: g.target === 'negative' ? 'negative' : 'positive',
      pick_mode: pickMode,
      prompts,
      weights: normalizeGroupWeights(prompts, g.weights),
    }
  })
  base.random_bundle_groups = (raw.random_bundle_groups || []).map((g) => {
    let bundles = (g.bundles || []).map((b) => ({
      id: b.id || newRandomBundle().id,
      alias: String(b.alias || '').trim() || '未命名',
      text: String(b.text ?? ''),
    }))
    if (!bundles.length) bundles = [newRandomBundle()]
    const pickMode = g.pick_mode === 'sequential' ? 'sequential' : 'random'
    const texts = bundles.map((b) => b.text)
    return {
      id: g.id || newRandomBundleGroup().id,
      name: g.name || '未命名词串组',
      enabled: g.enabled !== false,
      target: g.target === 'negative' ? 'negative' : 'positive',
      pick_mode: pickMode,
      bundles,
      weights: normalizeGroupWeights(
        bundles.map((b) => b.text || ' '),
        g.weights,
      ),
    }
  })
  return base
}

/** 提交 API 前去掉空随机组 / 空条目 */
export function serializePromptConfig(cfg) {
  const out = {
    enabled: cfg.enabled !== false,
    positive: String(cfg.positive ?? '').trim(),
    negative: String(cfg.negative ?? '').trim(),
    fixed: cfg.fixed,
    merge: { ...(cfg.merge || emptyMergeOptions()) },
    random_groups: [],
    random_bundle_groups: [],
  }
  for (const g of cfg.random_groups || []) {
    const prompts = (g.prompts || []).map((p) => String(p).trim()).filter(Boolean)
    if (!prompts.length) continue
    out.random_groups.push({
      id: g.id,
      name: g.name,
      enabled: !!g.enabled,
      target: g.target,
      pick_mode: g.pick_mode === 'sequential' ? 'sequential' : 'random',
      prompts,
      weights: normalizeGroupWeights(prompts, g.weights),
    })
  }
  for (const g of cfg.random_bundle_groups || []) {
    const bundles = (g.bundles || [])
      .map((b) => ({
        id: b.id,
        alias: String(b.alias || '').trim() || '未命名',
        text: String(b.text || '').trim(),
      }))
      .filter((b) => b.text)
    if (!bundles.length) continue
    out.random_bundle_groups.push({
      id: g.id,
      name: g.name,
      enabled: !!g.enabled,
      target: g.target,
      pick_mode: g.pick_mode === 'sequential' ? 'sequential' : 'random',
      bundles,
      weights: normalizeGroupWeights(
        bundles.map((b) => b.text),
        g.weights,
      ),
    })
  }
  return out
}

export function promptConfigHasContent(cfg) {
  const n = normalizePromptConfig(cfg)
  if (String(n.positive).trim() || String(n.negative).trim()) return true
  if (
    (n.random_groups || []).some(
      (g) => g.enabled !== false && (g.prompts || []).some((p) => String(p).trim()),
    )
  ) {
    return true
  }
  return (n.random_bundle_groups || []).some(
    (g) =>
      g.enabled !== false &&
      (g.bundles || []).some((b) => String(b.text || '').trim()),
  )
}

/** 抽卡/批量页摘要一行 */
export function promptConfigSummary(cfg) {
  const n = normalizePromptConfig(cfg)
  const parts = []
  const groups = (n.random_groups || []).filter(
    (g) => g.enabled !== false && (g.prompts || []).some((p) => String(p).trim()),
  )
  if (groups.length) parts.push(`${groups.length} 个随机组`)
  const bundleGroups = (n.random_bundle_groups || []).filter(
    (g) =>
      g.enabled !== false &&
      (g.bundles || []).some((b) => String(b.text || '').trim()),
  )
  if (bundleGroups.length) parts.push(`${bundleGroups.length} 个词串组`)
  if (String(n.positive).trim() || String(n.negative).trim()) parts.push('正/负全文')
  return parts.join(' · ') || ''
}

export function clonePromptConfig(cfg) {
  const n = normalizePromptConfig(cfg)
  return {
    enabled: n.enabled,
    positive: n.positive,
    negative: n.negative,
    fixed: {
      positive: { ...n.fixed.positive },
      negative: { ...n.fixed.negative },
    },
    random_groups: n.random_groups.map((g) => ({
      ...g,
      prompts: [...g.prompts],
      weights: [...(g.weights || [])],
    })),
    random_bundle_groups: (n.random_bundle_groups || []).map((g) => ({
      ...g,
      bundles: (g.bundles || []).map((b) => ({ ...b })),
      weights: [...(g.weights || [])],
    })),
    merge: { ...n.merge },
  }
}

export function applyPromptConfigTo(target, cfg) {
  const cloned = clonePromptConfig(cfg)
  target.enabled = cloned.enabled
  target.positive = cloned.positive
  target.negative = cloned.negative
  target.merge = cloned.merge
  target.fixed.positive = cloned.fixed.positive
  target.fixed.negative = cloned.fixed.negative
  if (Array.isArray(target.random_groups)) {
    target.random_groups.splice(0, target.random_groups.length, ...cloned.random_groups)
  } else {
    target.random_groups = cloned.random_groups
  }
  if (Array.isArray(target.random_bundle_groups)) {
    target.random_bundle_groups.splice(
      0,
      target.random_bundle_groups.length,
      ...cloned.random_bundle_groups,
    )
  } else {
    target.random_bundle_groups = cloned.random_bundle_groups
  }
  return cloned
}

/** 旧版 prompt_defaults → 全局配置（迁移展示用） */
export function globalDefaultsToFixed(defaults) {
  const d = defaults || {}
  return {
    positive: {
      prefix: d.positive?.prefix ?? '',
      suffix: d.positive?.suffix ?? '',
    },
    negative: {
      prefix: d.negative?.prefix ?? '',
      suffix: d.negative?.suffix ?? '',
    },
  }
}

export function globalConfigToPromptLayers(config) {
  return normalizePromptConfig(config)
}

/** 全局配置 PUT /api/global-prompt-config */
export function serializeGlobalPromptConfig(cfg, extras = {}) {
  const n = normalizePromptConfig(cfg)
  return {
    enabled: n.enabled,
    positive: n.positive,
    negative: n.negative,
    gacha_animation_enabled:
      extras.gacha_animation_enabled !== undefined
        ? !!extras.gacha_animation_enabled
        : true,
    merge: { ...n.merge },
    random_groups: (n.random_groups || [])
      .map((g) => {
        const prompts = (g.prompts || []).map((p) => String(p).trim()).filter(Boolean)
        if (!prompts.length) return null
        return {
          id: g.id,
          name: g.name,
          enabled: !!g.enabled,
          target: g.target,
          pick_mode: g.pick_mode === 'sequential' ? 'sequential' : 'random',
          prompts,
          weights: normalizeGroupWeights(prompts, g.weights),
        }
      })
      .filter(Boolean),
    random_bundle_groups: (n.random_bundle_groups || [])
      .map((g) => {
        const bundles = (g.bundles || [])
          .map((b) => ({
            id: b.id,
            alias: String(b.alias || '').trim() || '未命名',
            text: String(b.text || '').trim(),
          }))
          .filter((b) => b.text)
        if (!bundles.length) return null
        return {
          id: g.id,
          name: g.name,
          enabled: !!g.enabled,
          target: g.target,
          pick_mode: g.pick_mode === 'sequential' ? 'sequential' : 'random',
          bundles,
          weights: normalizeGroupWeights(
            bundles.map((b) => b.text),
            g.weights,
          ),
        }
      })
      .filter(Boolean),
  }
}

/** 含有效条目的全局随机组 */
export function globalRandomGroupsWithContent(cfg) {
  const n = normalizePromptConfig(cfg)
  return (n.random_groups || []).filter((g) =>
    (g.prompts || []).some((p) => String(p).trim()),
  )
}

/** 是否有已启用且含条目的全局随机组 */
export function globalRandomGroupsActive(cfg) {
  return globalRandomGroupsWithContent(cfg).some((g) => g.enabled !== false)
}

/** @returns {{ on: number, total: number }} */
export function globalRandomGroupsCounts(cfg) {
  const groups = globalRandomGroupsWithContent(cfg)
  return {
    on: groups.filter((g) => g.enabled !== false).length,
    total: groups.length,
  }
}

/** 摘要行用：关闭时显示「已关」，避免 0/6 组随机已开 */
export function formatGlobalRandomSummary(cfg) {
  const { on, total } = globalRandomGroupsCounts(cfg)
  const active = globalRandomGroupsActive(cfg)
  if (total === 0) {
    return { text: '无随机组', active: false }
  }
  if (!active || on === 0) {
    return { text: '随机组已关', active: false }
  }
  if (on === total) {
    return { text: `${total} 组随机已开`, active: true }
  }
  return { text: `${on}/${total} 组随机已开`, active: true }
}

/**
 * 一键开/关全局随机组（就地修改 cfg.random_groups，保留各组 enabled 供恢复）。
 * @returns {Record<string, boolean>|null} 关闭时返回快照；开启并恢复后返回 null
 */
export function globalRandomBundleGroupsWithContent(cfg) {
  const n = normalizePromptConfig(cfg)
  return (n.random_bundle_groups || []).filter((g) =>
    (g.bundles || []).some((b) => String(b.text || '').trim()),
  )
}

export function globalRandomBundleGroupsActive(cfg) {
  return globalRandomBundleGroupsWithContent(cfg).some((g) => g.enabled !== false)
}

export function formatGlobalRandomBundleSummary(cfg) {
  const groups = globalRandomBundleGroupsWithContent(cfg)
  const on = groups.filter((g) => g.enabled !== false).length
  const total = groups.length
  if (total === 0) return { text: '无词串组', active: false }
  if (!on) return { text: '词串组已关', active: false }
  if (on === total) return { text: `${total} 组词串已开`, active: true }
  return { text: `${on}/${total} 组词串已开`, active: true }
}

export function applyGlobalRandomBundleGroupsMaster(cfg, enabled, snapshot = null) {
  const groups = cfg?.random_bundle_groups
  if (!Array.isArray(groups)) return null
  const withContent = groups.filter((g) =>
    (g.bundles || []).some((b) => String(b.text || '').trim()),
  )
  if (!enabled) {
    const snap = {}
    for (const g of withContent) {
      snap[g.id] = g.enabled !== false
      g.enabled = false
    }
    return snap
  }
  if (snapshot && typeof snapshot === 'object') {
    for (const g of withContent) {
      g.enabled = snapshot[g.id] !== false
    }
  } else {
    for (const g of withContent) {
      g.enabled = true
    }
  }
  return null
}

export function applyGlobalRandomGroupsMaster(cfg, enabled, snapshot = null) {
  const groups = cfg?.random_groups
  if (!Array.isArray(groups)) return null

  const withContent = groups.filter((g) =>
    (g.prompts || []).some((p) => String(p).trim()),
  )
  if (!enabled) {
    const snap = {}
    for (const g of withContent) {
      snap[g.id] = g.enabled !== false
      g.enabled = false
    }
    return snap
  }
  if (snapshot && typeof snapshot === 'object') {
    for (const g of withContent) {
      g.enabled = snapshot[g.id] !== false
    }
  } else {
    for (const g of withContent) {
      g.enabled = true
    }
  }
  return null
}
