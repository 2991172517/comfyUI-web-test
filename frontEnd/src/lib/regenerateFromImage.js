import { api } from '@/api/client.js'
import {
  encodeWorkflowSnapshot,
  mergeOverridesFromCell,
  persistRestoreSnapshot,
  snapshotFromBatchCell,
} from '@/lib/workflowRestore.js'

function cellImageRef(cell) {
  if (!cell?.images?.length) return null
  return cell.images[0]
}

/**
 * 构建「以此生成」跳转 query：优先从 PNG 内嵌工作流解析，失败时用格子/批次记录快照。
 * @returns {Promise<{ query: object, snapshot: object, message?: string } | null>}
 */
export async function buildRegenerateRestoreRoute({
  cell,
  runConfig,
  batchId,
  cellIndex,
}) {
  const fallback = snapshotFromBatchCell(cell, runConfig)
  const img = cellImageRef(cell)

  let snap = null
  let message = ''

  if (img?.filename) {
    try {
      const res = await api.buildImageRestoreSnapshot({
        filename: img.filename,
        subfolder: img.subfolder || '',
        type: img.type || 'output',
        fallback_snapshot: fallback,
      })
      snap = res.snapshot || null
      message = res.message || snap?.restore_message || ''
    } catch (e) {
      if (fallback?.workflow_id || Object.keys(fallback?.overrides || {}).length) {
        snap = { ...fallback, restore_source: 'fallback_snapshot' }
        message = `PNG 解析失败（${e.message}），已使用记录快照`
      } else {
        throw e
      }
    }
  } else if (fallback?.workflow_id || Object.keys(fallback?.overrides || {}).length) {
    snap = { ...fallback, restore_source: 'stored_snapshot' }
    message = '无图片文件信息，已使用记录快照'
  } else {
    return null
  }

  snap.overrides = mergeOverridesFromCell(cell, snap.overrides || {})

  const wid = snap.workflow_id || runConfig?.workflow_id
  if (!wid) return null

  snap.workflow_id = wid
  const query = { workflow: wid }
  const idx = cellIndex ?? cell?.index
  const restoreKey =
    batchId != null && idx != null ? persistRestoreSnapshot(batchId, idx, snap) : null
  if (restoreKey) {
    query.restoreKey = restoreKey
  } else {
    const encoded = encodeWorkflowSnapshot(snap)
    if (encoded && encoded.length < 2400) {
      query.restore = encoded
    }
  }

  return { query, snapshot: snap, message }
}
