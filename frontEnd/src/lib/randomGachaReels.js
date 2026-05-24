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
  for (const pick of picks || []) {
    const gid = pick?.group_id != null ? String(pick.group_id) : ''
    const group = (gid && byId.get(gid)) || null
    const name = String(pick?.group_name || group?.name || '随机组').trim() || '随机组'
    const winner =
      String(pick?.text || '').trim() ||
      joinPromptTokens(pick?.tokens || []) ||
      ''

    if (!winner) continue

    let candidates = group ? buildReelCandidates(group) : []
    if (!candidates.length) {
      candidates = [winner]
    }
    if (!candidates.includes(winner)) {
      candidates = [...candidates, winner]
    }

    rows.push({
      id: gid || name,
      name,
      target: pick?.target || group?.target || 'positive',
      candidates,
      winner,
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

/**
 * @param {object} app useAppStore 实例
 * @param {{ globalConfig?: object | null }} [opts]
 * @returns {Promise<ReturnType<typeof buildGachaRows> | null>}
 */
export async function fetchRandomGachaPlan(app, { globalConfig = null } = {}) {
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
  if (!groups.length) return null

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
    const rows = buildGachaRows(groups, picks)
    return rows.length ? rows : null
  } catch {
    return null
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
