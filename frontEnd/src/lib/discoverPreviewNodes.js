/**
 * 从 ComfyUI API 工作流（prompt）识别流水线节点。
 * 顺序：拓扑排序 + 预览节点紧挨其 images 上游（非按 #101 数字排最后）。
 */

function sortNodeId(a, b) {
  const na = Number(a)
  const nb = Number(b)
  if (!Number.isNaN(na) && !Number.isNaN(nb)) return na - nb
  return String(a).localeCompare(String(b))
}

function primaryImageSource(node) {
  const images = node?.inputs?.images
  if (Array.isArray(images) && images.length >= 2) return String(images[0])
  return null
}

/**
 * @param {Record<string, { inputs?: Record<string, unknown> }>} prompt
 * @param {Set<string>} validIds
 */
function upstreamNodeIds(node, validIds) {
  const ups = []
  const seen = new Set()
  for (const value of Object.values(node.inputs || {})) {
    if (!Array.isArray(value) || value.length < 2) continue
    const up = String(value[0])
    if (validIds.has(up) && !seen.has(up)) {
      seen.add(up)
      ups.push(up)
    }
  }
  return ups
}

function flushReadyPreviews(prompt, parentId, dependents, inDegree, order, ready) {
  for (const child of [...(dependents[parentId] || [])].sort(sortNodeId)) {
    inDegree[child] -= 1
    if (inDegree[child] !== 0) continue
    const childNode = prompt[child]
    if (
      childNode?.class_type === 'PreviewImage' &&
      primaryImageSource(childNode) === parentId
    ) {
      order.push(child)
      for (const gc of dependents[child] || []) {
        inDegree[gc] -= 1
        if (inDegree[gc] === 0) ready.push(gc)
      }
      ready.sort(sortNodeId)
    } else {
      ready.push(child)
    }
  }
  ready.sort(sortNodeId)
}

/**
 * @param {Record<string, object> | null | undefined} prompt
 * @returns {string[]}
 */
export function topologicalSortNodeIds(prompt) {
  if (!prompt || typeof prompt !== 'object') return []
  const idSet = new Set(
    Object.entries(prompt)
      .filter(([, node]) => node && typeof node === 'object' && node.class_type)
      .map(([id]) => String(id)),
  )
  if (!idSet.size) return []

  const inDegree = Object.fromEntries([...idSet].map((id) => [id, 0]))
  const dependents = Object.fromEntries([...idSet].map((id) => [id, []]))

  for (const nid of idSet) {
    const node = prompt[nid]
    for (const up of upstreamNodeIds(node, idSet)) {
      inDegree[nid] += 1
      dependents[up].push(nid)
    }
  }

  const ready = [...idSet].filter((id) => inDegree[id] === 0).sort(sortNodeId)
  const order = []

  while (ready.length) {
    const nid = ready.shift()
    order.push(nid)
    flushReadyPreviews(prompt, nid, dependents, inDegree, order, ready)
  }

  const remaining = [...idSet].filter((id) => !order.includes(id)).sort(sortNodeId)
  return [...order, ...remaining]
}

/**
 * @param {Record<string, { class_type?: string, _meta?: { title?: string } }> | null | undefined} prompt
 * @returns {import('./discoverPreviewNodes.js').PipelineNode[]}
 */
export function discoverPipelineNodesFromPrompt(prompt) {
  if (!prompt || typeof prompt !== 'object') return []
  const byId = new Map()
  for (const [nodeId, node] of Object.entries(prompt)) {
    if (!node || typeof node !== 'object') continue
    const ct = node.class_type || ''
    const title = node._meta?.title || ct || `#${nodeId}`
    byId.set(String(nodeId), {
      node_id: String(nodeId),
      class_type: ct,
      title,
      is_preview: ct === 'PreviewImage',
      is_save: ct === 'SaveImage',
    })
  }
  return topologicalSortNodeIds(prompt)
    .filter((id) => byId.has(id))
    .map((id) => byId.get(id))
}

/**
 * @param {Record<string, object> | null | undefined} prompt
 */
/**
 * @param {PipelineNode[]} pipeline
 * @param {string[]} enabledPreviewNodeIds
 */
export function filterPipelineForExecution(pipeline, enabledPreviewNodeIds) {
  const enabled = new Set((enabledPreviewNodeIds || []).map(String))
  return (pipeline || []).filter(
    (n) => !n.is_preview || enabled.has(String(n.node_id)),
  )
}

export function discoverPreviewNodesFromPrompt(prompt) {
  return discoverPipelineNodesFromPrompt(prompt)
    .filter((n) => n.is_preview)
    .map(({ node_id, class_type, title }) => ({ node_id, class_type, title }))
}

/**
 * @typedef {object} PipelineNode
 * @property {string} node_id
 * @property {string} class_type
 * @property {string} title
 * @property {boolean} is_preview
 * @property {boolean} is_save
 */
