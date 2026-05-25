import { api } from '@/api/client.js'
import {
  globalConfigToPromptLayers,
  normalizePromptConfig,
  serializePromptConfig,
} from '@/composables/usePromptConfig.js'
import { splitPromptTokens, joinPromptTokens } from '@/lib/promptTokens.js'

const MUTED_PREFIX = '!'

function isMutedToken(token) {
  return String(token || '').trim().startsWith(MUTED_PREFIX)
}

function activeTokensFromLine(line) {
  return splitPromptTokens(line).filter((t) => !isMutedToken(t))
}

/**
 * 与后端 collect_all_random_groups 一致：全局 + 当次，按 id 去重。
 * @param {object | null | undefined} globalConfig
 * @param {object | null | undefined} sessionPrompts
 */
export function collectEnabledRandomGroups(globalConfig, sessionPrompts) {
  const out = []
  const seen = new Set()

  const pushGroup = (group) => {
    if (!group || group.enabled === false) return
    const id = group.id || group.name
    if (id && seen.has(id)) return
    const pool = (group.prompts || []).map((p) => String(p).trim()).filter(Boolean)
    if (!pool.length) return
    if (id) seen.add(id)
    out.push({ ...group, prompts: pool })
  }

  const g = globalConfigToPromptLayers(globalConfig)
  for (const group of g.random_groups || []) pushGroup(group)

  const s = normalizePromptConfig(sessionPrompts)
  for (const group of s.random_groups || []) pushGroup(group)

  return out
}

/**
 * @param {object | null | undefined} globalConfig
 * @param {object | null | undefined} sessionPrompts
 * @param {{ masterEnabled?: boolean }} [opts]
 */
export function collectEnabledRandomBundleGroups(
  globalConfig,
  sessionPrompts,
  { masterEnabled = true } = {},
) {
  if (!masterEnabled) return []
  const out = []
  const seen = new Set()

  const pushGroup = (group) => {
    if (!group || group.enabled === false) return
    const id = group.id || group.name
    if (id && seen.has(id)) return
    const bundles = (group.bundles || []).filter((b) => String(b.text || '').trim())
    if (!bundles.length) return
    if (id) seen.add(id)
    out.push({ ...group, bundles })
  }

  const g = globalConfigToPromptLayers(globalConfig)
  for (const group of g.random_bundle_groups || []) pushGroup(group)

  const s = normalizePromptConfig(sessionPrompts)
  for (const group of s.random_bundle_groups || []) pushGroup(group)

  return out
}

export function buildBundleReelCandidates(group) {
  return (group.bundles || [])
    .filter((b) => String(b.text || '').trim())
    .map((b) => {
      const alias = String(b.alias || '').trim()
      const preview = String(b.text || '').trim()
      const short =
        preview.length > 72 ? `${preview.slice(0, 72)}…` : preview
      return alias ? `${alias} · ${short}` : short
    })
}

/**
 * @param {object} group
 * @returns {string[]}
 */
export function buildReelCandidates(group) {
  const pool = (group.prompts || []).map((p) => String(p).trim()).filter(Boolean)
  if (!pool.length) return []

  if (pool.length <= 1) {
    return activeTokensFromLine(pool[0] || '')
  }

  return pool.map((line) => {
    const tokens = activeTokensFromLine(line)
    const merged = joinPromptTokens(tokens)
    if (merged) return merged
    const t = String(line).trim()
    return t.length > 96 ? `${t.slice(0, 96)}…` : t
  })
}

/**
 * @param {object[]} groups
 * @param {object[]} picks
 * @returns {{ id: string, name: string, target: string, candidates: string[], winner: string }[]}
 */
export function buildGachaRows(groups, picks) {
  const byId = new Map()
  for (const g of groups || []) {
    if (g?.id) byId.set(String(g.id), g)
  }

  const rows = []
  const bundleById = new Map()
  for (const g of groups || []) {
    if (g?.bundles?.length && g?.id) bundleById.set(String(g.id), g)
  }

  for (const pick of picks || []) {
    const gid = pick?.group_id != null ? String(pick.group_id) : ''
    const isBundle = pick?.pick_type === 'bundle_group'
    const group = isBundle
      ? bundleById.get(gid) || null
      : (gid && byId.get(gid)) || null
    const baseName = String(pick?.group_name || group?.name || '随机组').trim() || '随机组'
    const name = isBundle
      ? `${baseName}${pick?.bundle_alias ? ` · ${pick.bundle_alias}` : ''}`
      : baseName
    const winner =
      String(pick?.text || '').trim() ||
      joinPromptTokens(pick?.tokens || []) ||
      ''

    if (!winner) continue

    let candidates = []
    if (isBundle && group) {
      candidates = buildBundleReelCandidates(group)
      const alias = String(pick?.bundle_alias || '').trim()
      const winnerLabel =
        alias && winner
          ? candidates.find((c) => c.startsWith(`${alias} ·`)) || `${alias} · ${winner}`
          : winner
      if (!candidates.includes(winnerLabel)) candidates = [...candidates, winnerLabel]
      rows.push({
        id: gid || name,
        name,
        target: pick?.target || group?.target || 'positive',
        candidates,
        winner: winnerLabel,
        kind: 'bundle',
      })
      continue
    }

    candidates = group ? buildReelCandidates(group) : []
    if (!candidates.length) candidates = [winner]
    if (!candidates.includes(winner)) candidates = [...candidates, winner]

    rows.push({
      id: gid || name,
      name,
      target: pick?.target || group?.target || 'positive',
      candidates,
      winner,
      kind: 'token',
    })
  }
  return rows
}

/**
 * @returns {Promise<object | null>}
 */
export async function loadGlobalPromptConfigForPlan() {
  try {
    const gRes = await api.getGlobalPromptConfig()
    return gRes?.config ?? null
  } catch {
    return null
  }
}

/**
 * 客户端模拟抽词（设置页预览用，不影响实际生成）。
 * @param {object[]} groups
 * @returns {ReturnType<typeof buildGachaRows>}
 */
export function simulateGachaRowsForGroups(groups) {
  const enabled = (groups || []).filter((g) => {
    if (!g || g.enabled === false) return false
    return (g.prompts || []).some((p) => String(p).trim())
  })

  const picks = enabled.map((group) => {
    const candidates = buildReelCandidates(group)
    const winner =
      candidates.length > 0
        ? candidates[Math.floor(Math.random() * candidates.length)]
        : String((group.prompts || []).find((p) => String(p).trim()) || '').trim()

    return {
      group_id: group.id,
      group_name: group.name,
      target: group.target || 'positive',
      text: winner,
    }
  })

  return buildGachaRows(enabled, picks)
}

export function simulateGachaRowsForBundleGroups(groups) {
  const enabled = (groups || []).filter((g) => {
    if (!g || g.enabled === false) return false
    return (g.bundles || []).some((b) => String(b.text || '').trim())
  })

  const picks = enabled.map((group) => {
    const candidates = buildBundleReelCandidates(group)
    const bundles = (group.bundles || []).filter((b) => String(b.text || '').trim())
    const bundle =
      bundles.length > 0
        ? bundles[Math.floor(Math.random() * bundles.length)]
        : null
    const text = bundle ? String(bundle.text).trim() : ''
    return {
      pick_type: 'bundle_group',
      group_id: group.id,
      group_name: group.name,
      target: group.target || 'positive',
      bundle_alias: bundle?.alias || '',
      text,
    }
  })

  return buildGachaRows(enabled, picks)
}

/**
 * @param {object} app useAppStore 实例
 * @param {{ globalConfig?: object | null }} [opts]
 * @returns {Promise<ReturnType<typeof buildGachaRows> | null>}
 */
export async function fetchRandomGachaPlan(
  app,
  { globalConfig = null, bundleMasterEnabled = true } = {},
) {
  if (!app?.selectedId) return null

  const seedNode = app.workflowTargets?.seed_nodes?.[0]
  const promptSeed =
    seedNode?.seed != null && Number.isFinite(Number(seedNode.seed))
      ? Number(seedNode.seed)
      : null

  let globalConfigResolved = globalConfig
  if (globalConfigResolved === null) {
    globalConfigResolved = await loadGlobalPromptConfigForPlan()
  }

  const session = app.sessionPrompts
  const groups = collectEnabledRandomGroups(globalConfigResolved, session)
  const bundleGroups = collectEnabledRandomBundleGroups(
    globalConfigResolved,
    session,
    { masterEnabled: bundleMasterEnabled },
  )
  if (!groups.length && !bundleGroups.length) return null

  const hasSession = (() => {
    const n = normalizePromptConfig(session)
    return (
      String(n.positive).trim() ||
      String(n.negative).trim() ||
      (n.random_groups || []).some(
        (g) => g.enabled !== false && (g.prompts || []).some((p) => String(p).trim()),
      )
    )
  })()

  try {
    const res = await api.previewPromptMerge({
      workflow_id: app.selectedId,
      overrides: app.overrides,
      style_enabled: app.styleEnabled,
      batch_prompts: hasSession ? serializePromptConfig(session) : null,
      prompt_seed: promptSeed,
      prompt_global_priority: session?.merge?.random_before_workflow ?? false,
    })
    const picks = res?.prompt_picks || []
    if (!picks.length) return null
    const rows = buildGachaRows([...groups, ...bundleGroups], picks)
    return rows.length ? rows : null
  } catch (err) {
    const msg = err?.message || String(err)
    throw new Error(msg || '提示词合并预览失败')
  }
}

/**
 * 等待单抽任务已提交（拿到 promptId）。
 * @param {object} app
 */
export async function waitForJobQueued(app, { maxWaitMs = 20_000, pollMs = 40 } = {}) {
  const deadline = Date.now() + maxWaitMs
  while (Date.now() < deadline) {
    if (app?.job?.promptId) return true
    await new Promise((r) => setTimeout(r, pollMs))
  }
  return false
}

/**
 * 等待单抽任务进入 in_progress（ComfyUI 已开始执行）。
 * @param {object} app
 */
export async function waitUntilJobRunning(app, { maxWaitMs = 3000, pollMs = 50 } = {}) {
  const deadline = Date.now() + maxWaitMs
  while (Date.now() < deadline) {
    const pid = app?.job?.promptId
    if (!pid) {
      await new Promise((r) => setTimeout(r, pollMs))
      continue
    }
    try {
      const detail = await api.getJob(pid)
      if (app?.applyJobDetail) app.applyJobDetail(detail)
      if (detail.status === 'in_progress') return true
      if (['failed', 'cancelled', 'completed'].includes(detail.status)) return false
    } catch {
      /* 继续轮询 */
    }
    await new Promise((r) => setTimeout(r, pollMs))
  }
  return true
}
