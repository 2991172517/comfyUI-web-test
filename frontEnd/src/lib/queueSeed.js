/** 生成前解析 Seed，并写入 overrides（支持 seed / noise_seed） */

/**
 * @param {{ seedMode?: string, seed?: number }} form
 * @returns {number}
 */
export function resolveSeedValue(form) {
  const mode = form?.seedMode || 'fixed'
  if (mode === 'random') {
    return Math.floor(Math.random() * 2147483647)
  }
  const base = Number(form?.seed ?? 0)
  if (mode === 'increment') {
    const next = base + 1
    if (form) form.seed = next
    return next
  }
  return base
}

/**
 * @param {Array<{ node_id: string, seed_field?: string }>} seedNodes
 * @param {number} seed
 */
export function buildSeedOverridePatch(seedNodes, seed) {
  const patch = {}
  for (const sn of seedNodes || []) {
    const id = String(sn.node_id)
    const field = sn.seed_field || 'seed'
    patch[id] = { ...(patch[id] || {}), [field]: seed }
  }
  return patch
}
