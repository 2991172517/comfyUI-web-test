import { promptToComma } from '@/lib/promptDisplay.js'
import { favoriteToDetailMeta } from '@/lib/favoriteMeta.js'
import { buildCellDetailMeta } from '@/lib/cellDetailMeta.js'

function shortName(name) {
  return String(name || '').replace(/\.(safetensors|ckpt|pt)$/i, '')
}

function formatSampler(s) {
  if (!s || typeof s !== 'object') return ''
  const parts = []
  if (s.sampler_name) parts.push(String(s.sampler_name))
  if (s.steps != null && s.steps !== '') parts.push(`steps ${s.steps}`)
  if (s.cfg != null && s.cfg !== '') parts.push(`CFG ${s.cfg}`)
  if (s.scheduler) parts.push(String(s.scheduler))
  if (s.denoise != null && s.denoise !== '') parts.push(`denoise ${s.denoise}`)
  if (s.seed != null && s.seed !== '') parts.push(`seed ${s.seed}`)
  return parts.join(' · ')
}

function truncate(text, max = 100) {
  const t = String(text || '').trim()
  if (!t) return ''
  return t.length > max ? `${t.slice(0, max)}…` : t
}

/**
 * @param {object | null | undefined} meta
 * @param {{ maxPromptLen?: number }} [opts]
 * @returns {{ label: string, value: string }[]}
 */
export function metaToFlipRows(meta, { maxPromptLen = 96 } = {}) {
  if (!meta) return []
  const rows = []

  if (meta.label) rows.push({ label: '标签', value: meta.label })
  if (meta.workflow_id) {
    rows.push({
      label: '工作流',
      value: meta.workflow_display || meta.workflow_id,
    })
  }
  if (meta.prompt_id) rows.push({ label: '任务 ID', value: meta.prompt_id })
  if (meta.batch_id) rows.push({ label: '批次', value: meta.batch_id })
  if (meta.index != null) rows.push({ label: '格子', value: `#${meta.index}` })
  if (meta.ia != null && meta.ib != null) {
    rows.push({ label: '网格', value: `A${meta.ia} × B${meta.ib}` })
  }
  if (meta.checkpoint) rows.push({ label: 'Checkpoint', value: shortName(meta.checkpoint) })

  if (meta.loras?.length) {
    const loras = meta.loras
      .map((l) => {
        const n = l.short_name || shortName(l.lora_name)
        const w = l.strength_model != null ? ` @${l.strength_model}` : ''
        return `${n}${w}`
      })
      .join(' · ')
    rows.push({ label: 'LoRA', value: truncate(loras, 120) })
  }

  const sampler = formatSampler(meta.sampler)
  if (sampler) rows.push({ label: '采样', value: sampler })
  const pass2 = formatSampler(meta.sampler_pass2)
  if (pass2) rows.push({ label: '放大', value: pass2 })

  const pos =
    meta.prompt_positive_comma ||
    promptToComma(meta.prompt_positive) ||
    meta.prompt_positive
  if (pos) rows.push({ label: '正向', value: truncate(pos, maxPromptLen) })

  const neg =
    meta.prompt_negative_comma ||
    promptToComma(meta.prompt_negative) ||
    meta.prompt_negative
  if (neg) rows.push({ label: '负向', value: truncate(neg, maxPromptLen) })

  if (meta.filename || meta.filename_hint) {
    rows.push({ label: '文件', value: meta.filename || meta.filename_hint })
  }
  if (meta.started_at || meta.created_at) {
    rows.push({
      label: '时间',
      value: formatTime(meta.started_at || meta.created_at),
    })
  }
  if (meta.status) rows.push({ label: '状态', value: meta.status })

  return rows
}

function formatTime(iso) {
  if (!iso) return ''
  try {
    return new Date(iso).toLocaleString('zh-CN', { hour12: false })
  } catch {
    return String(iso)
  }
}

function samplerFromOverrides(overrides) {
  const ov = overrides || {}
  const sampler = {}
  const keys = ['seed', 'steps', 'cfg', 'sampler_name', 'scheduler', 'denoise']
  for (const nid of ['5', '14', 5, 14]) {
    const p = ov[nid]
    if (!p) continue
    for (const k of keys) {
      if (p[k] != null && p[k] !== '') sampler[k] = p[k]
    }
  }
  return sampler
}

/**
 * @param {import('@/stores/useAppStore.js').useAppStore extends Function ? ReturnType<typeof import('@/stores/useAppStore.js').createAppStore> : object} app
 * @param {{ filename?: string }} img
 */
export function buildJobImageMeta(app, img) {
  const overrides = app.overrides || {}
  const posEnc = app.promptEncode?.positive
  const negEnc = app.promptEncode?.negative
  let prompt_positive = ''
  let prompt_negative = ''
  if (posEnc?.node_id) {
    const node = app.state.nodes.find((n) => n.id === posEnc.node_id)
    const field = node?.fields?.find((f) => f.key === 'text')
    if (field) prompt_positive = app.fieldValue(posEnc.node_id, field) || ''
  }
  if (negEnc?.node_id) {
    const node = app.state.nodes.find((n) => n.id === negEnc.node_id)
    const field = node?.fields?.find((f) => f.key === 'text')
    if (field) prompt_negative = app.fieldValue(negEnc.node_id, field) || ''
  }

  const loras = (app.workflowLorasForUi || []).map((l) => {
    const node = app.state?.nodes?.find((n) => n.id === l.node_id)
    const nameField = node?.fields?.find((f) => f.key === 'lora_name')
    const smField = node?.fields?.find((f) => f.key === 'strength_model')
    const scField = node?.fields?.find((f) => f.key === 'strength_clip')
    return {
      node_id: l.node_id,
      lora_name: nameField ? app.fieldValue(l.node_id, nameField) : l.lora_name,
      short_name: l.short_name || shortName(l.lora_name),
      strength_model: smField ? app.fieldValue(l.node_id, smField) : l.strength_model,
      strength_clip: scField ? app.fieldValue(l.node_id, scField) : l.strength_clip,
    }
  })

  return metaToFlipRows({
    workflow_id: app.selectedId,
    workflow_display: app.workflowMeta?.display_name,
    checkpoint: app.activeCheckpointName,
    loras,
    sampler: samplerFromOverrides(overrides),
    prompt_positive,
    prompt_negative,
    filename: img?.filename,
    prompt_id: app.job?.promptId,
    status: app.job?.statusText,
  })
}

/**
 * @param {object} rec 历史列表项
 */
export function buildHistoryRecordMeta(rec) {
  if (!rec) return []
  if (rec.type === 'batch') {
    return metaToFlipRows({
      workflow_id: rec.workflow_id,
      batch_id: rec.batch_id || rec.id,
      status: rec.status,
      started_at: rec.started_at,
      label: `${rec.completed}/${rec.total} 张`,
      workflow_display: rec.grid
        ? `网格 ${rec.grid.a_count}×${rec.grid.b_count}`
        : undefined,
    })
  }

  const meta = {
    ...(rec.meta || {}),
    workflow_id: rec.workflow_id,
    prompt_id: rec.prompt_id || rec.id,
    started_at: rec.started_at,
    status: rec.status,
  }
  return metaToFlipRows(meta)
}

/**
 * @param {object} fav
 */
export function buildFavoriteImageMeta(fav) {
  if (!fav) return []
  const meta = favoriteToDetailMeta(fav)
  meta.created_at = fav.created_at
  meta.filename = fav.image?.filename
  return metaToFlipRows(meta)
}

/**
 * @param {object} cell
 * @param {object} batchStore batch store context
 */
export function buildBatchCellImageMeta(cell, batchStore) {
  const context = {
    workflow_id: batchStore.batch?.runConfig?.workflow_id || batchStore.app?.selectedId,
    run_config: batchStore.batch?.runConfig,
    batch_meta: batchStore.batch?.meta,
  }
  const meta = buildCellDetailMeta(cell, context)
  return metaToFlipRows(meta, { maxPromptLen: 72 })
}
