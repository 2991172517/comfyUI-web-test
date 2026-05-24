import { api } from '@/api/client.js'

const TERMINAL_FAIL = new Set(['failed', 'cancelled'])

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms))
}

/**
 * @param {import('@/stores/useAppStore.js').useAppStore extends Function ? object : object} app
 */
export function collectPromptNodeIds(app) {
  const ids = new Set()
  const pe = app?.promptEncode
  if (pe?.positive?.node_id != null) ids.add(String(pe.positive.node_id))
  if (pe?.negative?.node_id != null) ids.add(String(pe.negative.node_id))

  for (const node of app?.state?.nodes || []) {
    const ct = String(node?.class_type || node?.type || '').toLowerCase()
    if (ct.includes('cliptextencode')) {
      ids.add(String(node.id))
    }
  }
  return ids
}

/**
 * @param {string | number | null | undefined} currentNode
 * @param {Set<string>} promptNodeIds
 */
export function isExecutingPromptNode(currentNode, promptNodeIds) {
  if (currentNode == null || currentNode === '') return false
  return promptNodeIds.has(String(currentNode))
}

/**
 * @param {object} detail
 */
function detailReachedPromptStage(detail) {
  if (!detail) return false
  if (detail.prompt_stage_reached) return true
  return false
}

/**
 * 单抽：高频轮询 + 后端 WS 标记 prompt_stage_reached，避免提示词节点执行过快被 1s 轮询跳过。
 * @param {object} app
 * @param {{ maxWaitMs?: number, pollMs?: number }} [opts]
 */
export async function waitUntilPromptStage(app, { maxWaitMs = 120_000, pollMs = 60 } = {}) {
  const promptNodeIds = collectPromptNodeIds(app)
  const deadline = Date.now() + maxWaitMs
  let sawInProgress = false
  let stickyPromptStage = false

  while (Date.now() < deadline) {
    const promptId = app?.job?.promptId
    if (!promptId) {
      await sleep(40)
      continue
    }

    let detail
    try {
      detail = await api.getJob(promptId)
    } catch {
      await sleep(pollMs)
      continue
    }

    if (app?.applyJobDetail) {
      app.applyJobDetail(detail)
    } else if (app?.job) {
      app.job.currentNode = detail.current_node ?? null
      app.job.progress = detail.progress ?? null
      app.job.status = detail.status
    }

    const status = detail.status

    if (detailReachedPromptStage(detail)) {
      stickyPromptStage = true
    }
    if (isExecutingPromptNode(detail.current_node, promptNodeIds)) {
      stickyPromptStage = true
    }
    if (status === 'in_progress') {
      sawInProgress = true
    }

    if (stickyPromptStage) {
      return {
        ready: true,
        reason: detail.prompt_stage_reached ? 'ws-prompt-stage' : 'prompt-node',
        node: detail.prompt_stage_node || detail.current_node,
      }
    }

    if (TERMINAL_FAIL.has(status)) {
      return { ready: false, reason: status }
    }

    if (status === 'completed' || status === 'finalizing') {
      if (stickyPromptStage || detailReachedPromptStage(detail)) {
        return { ready: true, reason: 'completed-after-prompt', node: detail.prompt_stage_node }
      }
      if (sawInProgress || promptNodeIds.size > 0) {
        return { ready: true, reason: 'fast-complete-fallback' }
      }
      return { ready: false, reason: status }
    }

    if (!promptNodeIds.size && status === 'in_progress' && detail.current_node) {
      return { ready: true, reason: 'in-progress-fallback', node: detail.current_node }
    }

    await sleep(pollMs)
  }

  if (stickyPromptStage) {
    return { ready: true, reason: 'sticky-after-timeout' }
  }
  return { ready: false, reason: 'timeout' }
}
