/**
 * @param {string} nodeId
 * @param {string | null | undefined} currentNodeId
 * @param {string[]} completedNodeIds
 * @param {string} jobStatus
 * @param {string[]} [trackNodeIds] 进度条节点顺序（用于 current 之前推断为 done）
 * @returns {'pending' | 'active' | 'done'}
 */
export function pipelineNodeStatus(
  nodeId,
  currentNodeId,
  completedNodeIds,
  jobStatus,
  trackNodeIds,
) {
  const id = String(nodeId)
  const completed = new Set((completedNodeIds || []).map(String))
  if (jobStatus === 'completed') return 'done'
  if (currentNodeId != null && String(currentNodeId) === id) return 'active'

  const order = (trackNodeIds || []).map(String).filter(Boolean)
  if (currentNodeId != null && order.length) {
    const curIdx = order.indexOf(String(currentNodeId))
    const myIdx = order.indexOf(id)
    if (curIdx >= 0 && myIdx >= 0 && myIdx < curIdx) return 'done'
  }

  if (completed.has(id)) return 'done'
  return 'pending'
}
