/** @param {{ node_id?: string | number } | string | number} item */
function nodeIdOf(item) {
  if (item == null) return ''
  if (typeof item === 'object' && 'node_id' in item) return String(item.node_id)
  return String(item)
}

/**
 * 合并后端 completed_nodes，并按流水线顺序把 current 之前的节点标为已完成。
 * 避免 1s 轮询漏掉快节点导致进度条“跳过”前几格。
 */
export function mergeCompletedNodeIds(
  existing,
  incoming,
  trackNodes,
  currentNodeId,
) {
  const merged = new Set((existing || []).map(String))
  for (const id of incoming || []) {
    const s = String(id).trim()
    if (s) merged.add(s)
  }

  const order = (trackNodes || []).map(nodeIdOf).filter(Boolean)
  if (currentNodeId != null && order.length) {
    const cur = String(currentNodeId)
    const curIdx = order.indexOf(cur)
    if (curIdx >= 0) {
      for (let i = 0; i < curIdx; i++) merged.add(order[i])
    }
  }

  return [...merged]
}
