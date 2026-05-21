import { promptToComma } from '@/lib/promptDisplay.js'

/** 收藏条目均为单张图；区分来源用于角标展示 */
export function isFromBatchGrid(fav) {
  if (!fav) return false
  return (
    fav.source === 'batch' ||
    !!fav.batch_id ||
    fav.grid_ia != null ||
    fav.grid_ib != null
  )
}

export function favoriteSourceLabel(fav) {
  if (isFromBatchGrid(fav)) {
    const ia = fav.grid_ia
    const ib = fav.grid_ib
    if (ia != null && ib != null) return `批量格 A${ia}×B${ib}`
    return '批量格'
  }
  return '单抽'
}

const SAMPLER_KEYS = ['seed', 'steps', 'cfg', 'sampler_name', 'scheduler', 'denoise']

function mergeSamplerPatch(target, patch) {
  if (!patch || typeof patch !== 'object') return
  for (const k of SAMPLER_KEYS) {
    if (patch[k] != null && patch[k] !== '') target[k] = patch[k]
  }
}

/** 从收藏 params 提取正负提示词（prompt_nodes 为空时回退 overrides 3/4） */
export function extractFavoritePrompts(params) {
  const p = params || {}
  const nodes = p.prompt_nodes || {}
  const ids = Object.keys(nodes).sort((a, b) => Number(a) - Number(b))
  let prompt_positive = ids[0] != null ? String(nodes[ids[0]] ?? '') : ''
  let prompt_negative = ids[1] != null ? String(nodes[ids[1]] ?? '') : ''

  const ov = p.overrides || {}
  if (!prompt_positive.trim()) {
    prompt_positive = String(ov['3']?.text ?? ov[3]?.text ?? '')
  }
  if (!prompt_negative.trim()) {
    prompt_negative = String(ov['4']?.text ?? ov[4]?.text ?? '')
  }
  return { prompt_positive, prompt_negative }
}

function buildFavoriteSampler(params) {
  const p = params || {}
  const ov = p.overrides || {}
  const sampler = { ...(p.sampler || {}) }
  mergeSamplerPatch(sampler, ov['5'])
  mergeSamplerPatch(sampler, ov['14'])
  if (p.seed != null && sampler.seed == null) sampler.seed = p.seed
  return sampler
}

/** 转为 HistoryMetaPanel 可用的 meta */
export function favoriteToDetailMeta(fav) {
  const p = fav?.params || {}
  const { prompt_positive, prompt_negative } = extractFavoritePrompts(p)
  const sampler = buildFavoriteSampler(p)

  return {
    checkpoint: p.checkpoint,
    loras: p.loras || [],
    sampler,
    seed: p.seed ?? sampler.seed,
    prompt_positive,
    prompt_negative,
    prompt_positive_comma: promptToComma(prompt_positive),
    prompt_negative_comma: promptToComma(prompt_negative),
    workflow_id: fav.workflow_id,
    label: fav.label,
    prompt_id: fav.prompt_id,
    batch_id: fav.batch_id,
    ia: fav.grid_ia,
    ib: fav.grid_ib,
  }
}

export function buildFavoriteFilterOptions(items) {
  const checkpoints = new Set()
  const workflows = new Set()
  const loras = new Map()

  for (const f of items) {
    const p = f.params || {}
    if (p.checkpoint) checkpoints.add(p.checkpoint)
    if (f.workflow_id) workflows.add(f.workflow_id)
    for (const l of p.loras || []) {
      const name = l.lora_name
      if (!name) continue
      if (!loras.has(name)) {
        loras.set(name, { lora_name: name, short_name: l.short_name || name, weights: new Set() })
      }
      const w = l.strength_model
      if (w != null) loras.get(name).weights.add(Number(w))
    }
  }

  return {
    checkpoints: [...checkpoints].sort(),
    workflows: [...workflows].sort(),
    loras: [...loras.values()]
      .map((x) => ({
        lora_name: x.lora_name,
        short_name: x.short_name,
        weights: [...x.weights].sort((a, b) => a - b),
      }))
      .sort((a, b) => a.short_name.localeCompare(b.short_name)),
  }
}

export function filterFavorites(items, filters) {
  return items.filter((f) => {
    const p = f.params || {}
    if (filters.checkpoint && p.checkpoint !== filters.checkpoint) return false
    if (filters.workflow_id && f.workflow_id !== filters.workflow_id) return false
    if (filters.lora_name) {
      const hit = (p.loras || []).some((l) => l.lora_name === filters.lora_name)
      if (!hit) return false
      if (filters.lora_weight !== '' && filters.lora_weight != null) {
        const w = Number(filters.lora_weight)
        const wHit = (p.loras || []).some(
          (l) => l.lora_name === filters.lora_name && Number(l.strength_model) === w,
        )
        if (!wHit) return false
      }
    }
    return true
  })
}
