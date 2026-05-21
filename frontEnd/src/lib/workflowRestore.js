/** 工作流快照编解码（用于「以此生成」跳转） */

export const WORKFLOW_TEMPLATE_ID = 'First_api'

export function encodeWorkflowSnapshot(snapshot) {
  if (!snapshot) return ''
  try {
    const json = JSON.stringify(snapshot)
    const bytes = new TextEncoder().encode(json)
    let binary = ''
    for (const b of bytes) binary += String.fromCharCode(b)
    return btoa(binary)
  } catch {
    return ''
  }
}

export function decodeWorkflowSnapshot(encoded) {
  if (!encoded || typeof encoded !== 'string') return null
  try {
    const binary = atob(encoded)
    const bytes = Uint8Array.from(binary, (c) => c.charCodeAt(0))
    const json = new TextDecoder().decode(bytes)
    return JSON.parse(json)
  } catch {
    try {
      return JSON.parse(decodeURIComponent(encoded))
    } catch {
      return null
    }
  }
}

/** 用网格格子的 LoRA 信息补全 overrides（兼容旧 manifest） */
export function mergeOverridesFromCell(cell, baseOverrides = {}) {
  const ov = { ...(baseOverrides || {}) }
  if (cell?.overrides && typeof cell.overrides === 'object') {
    for (const [nid, patch] of Object.entries(cell.overrides)) {
      ov[nid] = { ...(ov[nid] || {}), ...patch }
    }
  }
  for (const key of ['A', 'B']) {
    const axis = cell?.loras?.[key]
    if (!axis?.node_id) continue
    const nid = String(axis.node_id)
    ov[nid] = {
      ...(ov[nid] || {}),
      ...(axis.lora_name ? { lora_name: axis.lora_name } : {}),
      ...(axis.strength_model != null ? { strength_model: axis.strength_model } : {}),
      ...(axis.strength_clip != null ? { strength_clip: axis.strength_clip } : {}),
    }
  }
  return ov
}

/**
 * 从批量格子 + run_config 构建可恢复快照。
 * 优先使用格子内 workflow_snapshot（执行时写入的完整参数）；
 * 否则用 run_config / overrides 拼装。
 */
export function snapshotFromBatchCell(cell, runConfig) {
  const rc = runConfig && typeof runConfig === 'object' ? runConfig : null
  const wid =
    cell?.workflow_snapshot?.workflow_id ||
    rc?.workflow_id ||
    ''

  if (cell?.workflow_snapshot) {
    const snap = { ...cell.workflow_snapshot }
    if (!snap.workflow_id && wid) snap.workflow_id = wid
    snap.overrides = mergeOverridesFromCell(cell, snap.overrides || {})
    if (snap.style_enabled == null && rc?.style_enabled != null) {
      snap.style_enabled = rc.style_enabled
    }
    if (!snap.batch_prompts && rc?.batch_prompts) {
      snap.batch_prompts = rc.batch_prompts
    }
    if (snap.prompt_global_priority == null && rc?.prompt_global_priority != null) {
      snap.prompt_global_priority = rc.prompt_global_priority
    }
    if (!snap.seed_mode && rc?.seed_mode) snap.seed_mode = rc.seed_mode
    return snap
  }

  const rb = rc?.request_body && typeof rc.request_body === 'object' ? rc.request_body : {}
  return {
    workflow_id: wid,
    overrides: mergeOverridesFromCell(cell, {
      ...(rc?.base_overrides || {}),
      ...(rb?.base_overrides || {}),
    }),
    batch_prompts: rc?.batch_prompts ?? rb?.batch_prompts ?? null,
    prompt_picks: cell?.prompt_picks || [],
    style_enabled: rc?.style_enabled ?? rb?.style_enabled ?? null,
    prompt_global_priority:
      rc?.prompt_global_priority ?? rb?.prompt_global_priority ?? null,
    seed: cell?.seed,
    seed_mode: rc?.seed_mode ?? rb?.seed_mode,
    loras: cell?.loras,
  }
}

/**
 * 解析恢复时应加载的工作流 ID。
 * 不自动新建文件：脚本/任务用的是磁盘上的母版或子工作流；缺失时用母版拓扑 + overrides 还原。
 */
const RESTORE_KEY_PREFIX = 'cp-restore:'

export function restoreStorageKey(batchId, cellIndex) {
  return `${RESTORE_KEY_PREFIX}${batchId}:${cellIndex}`
}

/** 写入 sessionStorage，避免 URL 过长导致快照被截断 */
export function persistRestoreSnapshot(batchId, cellIndex, snapshot) {
  if (!batchId || cellIndex == null || !snapshot) return null
  const key = restoreStorageKey(batchId, cellIndex)
  try {
    sessionStorage.setItem(key, JSON.stringify(snapshot))
    return key
  } catch {
    return null
  }
}

export function loadRestoreSnapshot(restoreKey) {
  if (!restoreKey || typeof restoreKey !== 'string') return null
  try {
    const raw = sessionStorage.getItem(restoreKey)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export function resolveRestoreWorkflowId(workflowId, workflows) {
  const list = workflows || []
  const id = (workflowId || '').trim()
  if (id && list.some((w) => w.id === id)) {
    return { id, usedFallback: false, missingId: id }
  }
  if (list.some((w) => w.id === WORKFLOW_TEMPLATE_ID)) {
    return {
      id: WORKFLOW_TEMPLATE_ID,
      usedFallback: !!id && id !== WORKFLOW_TEMPLATE_ID,
      missingId: id || null,
    }
  }
  if (list.length) {
    return { id: list[0].id, usedFallback: true, missingId: id || null }
  }
  return { id: id || WORKFLOW_TEMPLATE_ID, usedFallback: true, missingId: id || null }
}
