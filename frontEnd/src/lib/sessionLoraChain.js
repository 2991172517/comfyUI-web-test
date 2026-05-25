/** 生成页临时 LoRA 链（不写回工作流 JSON） */

export const SESS_LORA_PREFIX = 'sess:'

export function isSessionLoraId(id) {
  return String(id || '').startsWith(SESS_LORA_PREFIX)
}

export function newSessionLoraId() {
  const hex =
    typeof crypto !== 'undefined' && crypto.randomUUID
      ? crypto.randomUUID().replace(/-/g, '').slice(0, 8)
      : String(Date.now()).slice(-8)
  return `${SESS_LORA_PREFIX}${hex}`
}

/** @param {Array<{ node_id: string }>} loras */
export function createSessionLoraChain(loras) {
  return {
    order: (loras || []).map((l) => String(l.node_id)),
    hidden: [],
    added: [],
  }
}

export function sessionChainIsDirty(chain, baseIds) {
  if (!chain) return false
  const base = new Set((baseIds || []).map(String))
  if ((chain.hidden || []).some((id) => base.has(String(id)))) return true
  if ((chain.added || []).length) return true
  const order = (chain.order || []).map(String)
  const visible = order.filter((id) => !isSessionLoraId(id) && !chain.hidden.includes(id))
  const baseOrder = (baseIds || []).map(String).filter((id) => !chain.hidden.includes(id))
  if (visible.length !== baseOrder.length) return true
  for (let i = 0; i < visible.length; i++) {
    if (visible[i] !== baseOrder[i]) return true
  }
  return false
}

/**
 * @param {object} chain
 * @param {Array<object>} workflowLoras
 * @param {Record<string, Record<string, unknown>>} overrides
 */
export function buildSessionLorasForUi(chain, workflowLoras, overrides = {}) {
  if (!chain) return workflowLoras || []
  const hidden = new Set((chain.hidden || []).map(String))
  const byId = new Map((workflowLoras || []).map((l) => [String(l.node_id), { ...l }]))
  const addedById = new Map((chain.added || []).map((a) => [String(a.id), a]))
  const list = []
  for (const id of chain.order || []) {
    if (hidden.has(id)) continue
    if (isSessionLoraId(id)) {
      const add = addedById.get(id)
      if (!add) continue
      const patch = overrides[id] || {}
      const loraName = patch.lora_name ?? add.lora_name ?? ''
      list.push({
        node_id: id,
        role: add.role || 'character',
        kind: 'lora_chain',
        lora_name: loraName,
        short_name: String(loraName).replace(/\.(safetensors|ckpt|pt)$/i, '') || id,
        strength_model: patch.strength_model ?? add.strength_model ?? 0.65,
        strength_clip: patch.strength_clip ?? add.strength_clip ?? 0.65,
        session_only: true,
      })
      continue
    }
    const base = byId.get(id)
    if (base) list.push({ ...base, session_only: false })
  }
  return list
}

/** @param {object|null} chain */
export function serializeSessionLoraChain(chain) {
  if (!chain) return null
  return {
    order: [...(chain.order || [])],
    hidden: [...(chain.hidden || [])],
    added: (chain.added || []).map((a) => ({ ...a })),
  }
}
