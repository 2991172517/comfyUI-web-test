import { promptToComma } from '@/lib/promptDisplay.js'

/** 从批量格子 / 单抽记录拼出展示用元数据 */

function shortLora(name) {
  return String(name || '').replace(/\.(safetensors|ckpt|pt)$/i, '')
}

const SAMPLER_KEYS = ['seed', 'steps', 'cfg', 'sampler_name', 'scheduler', 'denoise']

function mergeSamplerPatch(target, patch) {
  if (!patch || typeof patch !== 'object') return
  for (const k of SAMPLER_KEYS) {
    if (patch[k] != null && patch[k] !== '') target[k] = patch[k]
  }
}

/** 合并工作流默认（batch meta）与格子 overrides 中的 KSampler 字段 */
function buildSampler(cell, context = {}) {
  const overrides = cell?.overrides || {}
  const base = context.run_config?.base_overrides || {}
  const sampler = { ...(context.batch_meta?.sampler || {}) }

  mergeSamplerPatch(sampler, base['5'])
  mergeSamplerPatch(sampler, base['14'])
  mergeSamplerPatch(sampler, overrides['5'])
  mergeSamplerPatch(sampler, overrides['14'])

  const seed = cell?.seed ?? sampler.seed
  if (seed != null) sampler.seed = seed

  return sampler
}

/**
 * @param {object} cell 批量 manifest item（含后端 meta 时优先使用）
 * @param {object} context { workflow_id, run_config, batch_meta }
 */
export function buildCellDetailMeta(cell, context = {}) {
  if (!cell) return null

  if (cell.meta && (cell.meta.checkpoint || cell.meta.loras?.length || cell.meta.sampler)) {
    const m = { ...cell.meta }
    return {
      checkpoint: m.checkpoint,
      loras: m.loras || [],
      sampler: m.sampler || {},
      sampler_pass2: m.sampler_pass2,
      prompt_positive: m.prompt_positive ?? '',
      prompt_negative: m.prompt_negative ?? '',
      prompt_positive_comma: m.prompt_positive_comma ?? promptToComma(m.prompt_positive),
      prompt_negative_comma: m.prompt_negative_comma ?? promptToComma(m.prompt_negative),
      label: cell.label,
      filename_hint: cell.filename_hint,
      index: cell.index,
      ia: cell.ia,
      ib: cell.ib,
      workflow_id: cell.workflow_snapshot?.workflow_id || context.workflow_id || m.workflow_id,
    }
  }

  const overrides = { ...(cell.overrides || {}) }
  const snap = cell.workflow_snapshot || {}
  const workflowId = snap.workflow_id || context.workflow_id || ''

  const loras = []
  const seen = new Set()

  for (const key of ['A', 'B']) {
    const axis = cell.loras?.[key]
    if (!axis?.node_id) continue
    const nid = String(axis.node_id)
    seen.add(nid)
    loras.push({
      node_id: nid,
      lora_name: axis.lora_name,
      short_name: axis.short_name || shortLora(axis.lora_name),
      strength_model: axis.strength_model,
      strength_clip: axis.strength_clip ?? axis.strength_model,
    })
  }

  for (const [nid, patch] of Object.entries(overrides)) {
    if (!patch?.lora_name || seen.has(nid)) continue
    seen.add(nid)
    loras.push({
      node_id: nid,
      lora_name: patch.lora_name,
      short_name: shortLora(patch.lora_name),
      strength_model: patch.strength_model,
      strength_clip: patch.strength_clip ?? patch.strength_model,
    })
  }
  loras.sort((a, b) => String(a.node_id).localeCompare(String(b.node_id)))

  const ckpt =
    overrides['1']?.ckpt_name ||
    context.batch_meta?.checkpoint ||
    context.run_config?.base_overrides?.['1']?.ckpt_name

  const sampler = buildSampler(cell, context)
  const samplerPass2 = context.batch_meta?.sampler_pass2

  const promptPositive =
    overrides['3']?.text ?? context.batch_meta?.prompt_positive ?? ''
  const promptNegative =
    overrides['4']?.text ?? context.batch_meta?.prompt_negative ?? ''

  return {
    checkpoint: ckpt || null,
    loras,
    sampler,
    sampler_pass2: samplerPass2,
    prompt_positive: promptPositive,
    prompt_negative: promptNegative,
    prompt_positive_comma: promptToComma(promptPositive),
    prompt_negative_comma: promptToComma(promptNegative),
    label: cell.label,
    filename_hint: cell.filename_hint,
    index: cell.index,
    ia: cell.ia,
    ib: cell.ib,
    workflow_id: workflowId,
  }
}
