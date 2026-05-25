import { INPAINT_NODES } from '@/lib/inpaintWorkflow.js'

const STORAGE_PREFIX = 'cp-inpaint-bootstrap:'

/** 内存兜底：避免 query 被 replace 后组件重挂载时 session 已消费 */
let pendingByKey = null

function findCkptInOverrides(overrides) {
  if (!overrides || typeof overrides !== 'object') return ''
  if (overrides[INPAINT_NODES.checkpoint]?.ckpt_name) {
    return String(overrides[INPAINT_NODES.checkpoint].ckpt_name)
  }
  for (const patch of Object.values(overrides)) {
    if (patch?.ckpt_name) return String(patch.ckpt_name)
  }
  return ''
}

function promptsFromPromptNodes(promptNodes) {
  const nodes = promptNodes && typeof promptNodes === 'object' ? promptNodes : {}
  const vals = Object.entries(nodes)
  const positive =
    nodes[INPAINT_NODES.positive] ||
    nodes['3'] ||
    vals.find(([id]) => id !== '4' && id !== INPAINT_NODES.negative)?.[1] ||
    ''
  const negative =
    nodes[INPAINT_NODES.negative] || nodes['4'] || vals[1]?.[1] || ''
  return {
    positive: String(positive || '').trim(),
    negative: String(negative || '').trim(),
  }
}

/** 从快照 / meta / params 提取局部重绘页可填写的参数 */
export function extractInpaintSettings(source = {}) {
  const snap = source.workflow_snapshot || {}
  const overrides = {
    ...(snap.overrides || {}),
    ...(source.overrides || {}),
    ...(source.params?.overrides || {}),
  }
  const meta = source.meta || {}
  const params = source.params || {}

  const checkpoint =
    String(
      meta.checkpoint ||
        params.checkpoint ||
        findCkptInOverrides(overrides) ||
        '',
    ).trim() || ''

  const fromNodes = promptsFromPromptNodes(params.prompt_nodes)
  const positive =
    String(meta.prompt_positive || fromNodes.positive || '').trim() ||
    ''
  const negative =
    String(meta.prompt_negative || fromNodes.negative || '').trim() ||
    ''

  const sampler = { ...(meta.sampler || {}), ...(params.sampler || {}) }
  const ovSampler = overrides[INPAINT_NODES.sampler] || {}

  return {
    checkpoint,
    positive,
    negative,
    seed:
      ovSampler.seed ??
      sampler.seed ??
      params.seed ??
      null,
    steps: ovSampler.steps ?? sampler.steps ?? null,
    cfg: ovSampler.cfg ?? sampler.cfg ?? null,
    denoise: ovSampler.denoise ?? sampler.denoise ?? null,
    source_workflow_id: source.workflow_id || snap.workflow_id || '',
  }
}

export function persistInpaintBootstrap(payload) {
  const key = `${STORAGE_PREFIX}${Date.now()}`
  try {
    const json = JSON.stringify(payload)
    sessionStorage.setItem(key, json)
    pendingByKey = { key, payload }
    return key
  } catch {
    pendingByKey = { key, payload }
    return key
  }
}

export function peekInpaintBootstrap(key) {
  if (!key || typeof key !== 'string') return null
  if (pendingByKey?.key === key) return pendingByKey.payload
  try {
    const raw = sessionStorage.getItem(key)
    if (!raw) return null
    return JSON.parse(raw)
  } catch {
    return null
  }
}

export function consumeInpaintBootstrap(key) {
  if (!key) return
  if (pendingByKey?.key === key) pendingByKey = null
  try {
    sessionStorage.removeItem(key)
  } catch {
    /* ignore */
  }
}

/** @deprecated 使用 peek + consume */
export function loadInpaintBootstrap(key) {
  const data = peekInpaintBootstrap(key)
  if (data) consumeInpaintBootstrap(key)
  return data
}

export function imageFromRecord(rec) {
  const img = rec?.images?.[0]
  if (img?.url) return img
  if (rec?.thumbnail_url) {
    return { url: rec.thumbnail_url, filename: '', subfolder: '', type: 'output' }
  }
  return null
}

export function buildInpaintPayloadFromHistory(rec) {
  const image = imageFromRecord(rec)
  if (!image?.url) return null
  return {
    image,
    workflow_id: rec.workflow_id,
    workflow_snapshot: rec.workflow_snapshot,
    overrides: rec.overrides,
    meta: rec.meta,
  }
}

export function buildInpaintPayloadFromFavorite(f) {
  if (!f?.image?.url) return null
  return {
    image: {
      url: f.image.url,
      filename: f.image.filename,
      subfolder: f.image.subfolder || '',
      type: f.image.type || 'output',
    },
    workflow_id: f.workflow_id,
    overrides: f.params?.overrides || {},
    params: f.params,
  }
}

export function buildInpaintPayloadFromGenerate(app, img) {
  if (!img?.url) return null
  const meta = {
    checkpoint: app.getActiveCheckpointName?.() || '',
    prompt_positive: app.lastQueuedPrompts?.positive || '',
    prompt_negative: app.lastQueuedPrompts?.negative || '',
  }
  return {
    image: {
      url: img.url,
      filename: img.filename,
      subfolder: img.subfolder || '',
      type: img.type || 'output',
    },
    workflow_id: app.selectedId,
    overrides: JSON.parse(JSON.stringify(app.overrides || {})),
    meta,
  }
}

export function buildInpaintPayloadFromBatchCell(cell, runConfig) {
  const img = cell?.images?.[0]
  if (!img?.url) return null
  const snap = cell?.workflow_snapshot || {
    workflow_id: runConfig?.workflow_id,
    overrides: cell?.overrides,
    batch_prompts: runConfig?.batch_prompts,
  }
  return {
    image: img,
    workflow_id: snap.workflow_id || runConfig?.workflow_id,
    workflow_snapshot: snap,
    overrides: cell?.overrides,
    meta: cell?.meta,
  }
}
