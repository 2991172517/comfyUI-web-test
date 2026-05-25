import { inject, onUnmounted, provide, reactive, ref } from 'vue'
import { api } from '@/api/client.js'
import {
  connectGenerateQueueWs,
  disconnectGenerateQueueWs,
  subscribeGenerateEvents,
} from '@/lib/generateQueueWs.js'
import { mergeCompletedNodeIds } from '@/lib/mergeJobProgress.js'

const GENERATE_QUEUE = Symbol('generateQueue')

function newId() {
  return `gq-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

function terminalJobStatus(s) {
  return ['completed', 'failed', 'cancelled'].includes(s)
}

function terminalBatchStatus(s) {
  return ['completed', 'failed', 'cancelled', 'deleted'].includes(s)
}

export function createGenerateQueueStore(app, batch) {
  const items = ref([])
  let pumping = false
  let wsUnsub = null

  function pendingItems() {
    return items.value.filter((i) => i.status === 'pending')
  }

  function runningItem() {
    return items.value.find((i) => i.status === 'running') || null
  }

  function hasRunning() {
    return (
      !!runningItem() ||
      app.isGenerating ||
      batch.isBatchRunning
    )
  }

  function dispatchWs(ev) {
    if (!ev?.type) return

    if (ev.type === 'job') {
      for (const it of items.value) {
        if (it.promptId === ev.prompt_id && it.status === 'running') {
          it.progress = ev.progress ?? it.progress
          it.status =
            ev.status === 'in_progress' || ev.status === 'finalizing'
              ? 'running'
              : ev.status || it.status
        }
      }
      app.applyWsJobEvent?.(ev)
      if (
        batch.batch.batchId &&
        batch.batch.currentPromptId === ev.prompt_id
      ) {
        batch.applyWsCellJobEvent?.(ev)
      }
    }

    if (ev.type === 'batch') {
      for (const it of items.value) {
        if (it.batchId === ev.batch_id && it.status === 'running') {
          it.batchCompleted = ev.completed ?? 0
          it.batchTotal = ev.total ?? 0
          it.progress = ev.progress ?? 0
          it.label = ev.current_label
            ? `批量 · ${ev.current_label}`
            : it.label
          if (terminalBatchStatus(ev.status)) {
            it.status = ev.status === 'completed' ? 'completed' : 'failed'
          }
        }
      }
      if (batch.batch.batchId === ev.batch_id) {
        batch.applyWsBatchEvent?.(ev)
      }
    }
  }

  function waitForJobDone(promptId, timeoutMs = 3600_000) {
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        unsub()
        reject(new Error('等待单张任务超时'))
      }, timeoutMs)
      const unsub = subscribeGenerateEvents((ev) => {
        if (ev.type !== 'job' || ev.prompt_id !== promptId) return
        if (terminalJobStatus(ev.status)) {
          clearTimeout(timer)
          unsub()
          resolve(ev)
        }
      })
    })
  }

  function waitForBatchDone(batchId, timeoutMs = 7200_000) {
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        unsub()
        reject(new Error('等待批量任务超时'))
      }, timeoutMs)
      const unsub = subscribeGenerateEvents((ev) => {
        if (ev.type !== 'batch' || ev.batch_id !== batchId) return
        if (terminalBatchStatus(ev.status)) {
          clearTimeout(timer)
          unsub()
          resolve(ev)
        }
      })
    })
  }

  async function executeItem(item, run) {
    item.status = 'running'
    item.progress = 0
    try {
      const result = await run()
      if (item.type === 'single') {
        item.promptId = result?.promptId || app.job.promptId
        const ev = await waitForJobDone(item.promptId)
        item.progress = ev.progress ?? 100
        item.status = ev.status === 'completed' ? 'completed' : 'failed'
      } else {
        item.batchId = result?.batchId || batch.batch.batchId
        if (result?.total) item.batchTotal = result.total
        const ev = await waitForBatchDone(item.batchId)
        item.batchCompleted = ev.completed ?? item.batchTotal
        item.batchTotal = ev.total ?? item.batchTotal
        item.progress = ev.progress ?? 100
        item.status = ev.status === 'completed' ? 'completed' : 'failed'
      }
    } catch (e) {
      item.status = 'failed'
      item.error = e.message || String(e)
    }
  }

  async function pump() {
    if (pumping || hasRunning()) return
    const next = items.value.find((i) => i.status === 'pending')
    if (!next || !next.run) return
    pumping = true
    const run = next.run
    next.run = null
    try {
      await executeItem(next, run)
    } finally {
      pumping = false
      pump()
    }
  }

  function pumpSoon() {
    queueMicrotask(() => pump())
  }

  function createItem(type, label, run) {
    return {
      id: newId(),
      type,
      label,
      status: 'pending',
      progress: 0,
      batchCompleted: 0,
      batchTotal: 0,
      promptId: null,
      batchId: null,
      error: '',
      run,
      createdAt: Date.now(),
    }
  }

  async function submit({ type, label, run, batchTotal = 0 }) {
    const item = createItem(type, label, run)
    if (type === 'batch' && batchTotal > 0) item.batchTotal = batchTotal
    if (hasRunning()) {
      items.value = [...items.value, item]
      const n = pendingItems().length
      app.setMessage(`当前有任务在执行，「${label}」已排队（前面 ${n} 项）`)
      pumpSoon()
      return { queued: true, id: item.id }
    }
    items.value = [...items.value, item]
    await executeItem(item, run)
    pumpSoon()
    return { queued: false, id: item.id }
  }

  async function cancelItem(id) {
    const it = items.value.find((i) => i.id === id)
    if (!it) return
    if (it.status === 'pending') {
      it.status = 'cancelled'
      items.value = items.value.filter((i) => i.id !== id)
      return
    }
    if (it.status === 'running') {
      try {
        if (it.type === 'batch' && it.batchId) {
          await api.cancelBatch(it.batchId)
        } else if (it.promptId) {
          await api.cancelJob(it.promptId)
        }
        it.status = 'cancelled'
      } catch (e) {
        app.setMessage(e.message, true)
      }
    }
  }

  function movePending(id, direction) {
    const pending = pendingItems()
    const idx = pending.findIndex((i) => i.id === id)
    if (idx < 0) return
    const target = direction < 0 ? idx - 1 : idx + 1
    if (target < 0 || target >= pending.length) return
    const all = items.value.filter((i) => i.status !== 'pending')
    const reordered = [...pending]
    const [row] = reordered.splice(idx, 1)
    reordered.splice(target, 0, row)
    items.value = [...all, ...reordered]
  }

  function clearFinished() {
    items.value = items.value.filter(
      (i) => !['completed', 'failed', 'cancelled'].includes(i.status),
    )
  }

  function progressLabel(item) {
    if (item.type === 'batch' && item.batchTotal > 0) {
      const done = item.batchCompleted ?? 0
      const current =
        item.status === 'running'
          ? Math.min(done + 1, item.batchTotal)
          : Math.min(done, item.batchTotal)
      const pct =
        item.progress ??
        (item.batchTotal ? Math.round((100 * done) / item.batchTotal) : 0)
      return `${current}/${item.batchTotal} · ${pct}%`
    }
    const pct = item.progress ?? 0
    return `${pct}%`
  }

  wsUnsub = subscribeGenerateEvents(dispatchWs)
  connectGenerateQueueWs()

  onUnmounted(() => {
    wsUnsub?.()
    disconnectGenerateQueueWs()
  })

  return reactive({
    items,
    hasRunning,
    runningItem,
    pendingItems,
    submit,
    cancelItem,
    movePending,
    clearFinished,
    progressLabel,
    pumpSoon,
  })
}

let queueSingleton = null

export function createGenerateQueueWithApp(app, batch) {
  const store = createGenerateQueueStore(app, batch)
  queueSingleton = store
  provide(GENERATE_QUEUE, store)
  return store
}

export function getGenerateQueueStore() {
  return queueSingleton
}

export function useGenerateQueueStore() {
  const store = inject(GENERATE_QUEUE)
  if (!store) throw new Error('useGenerateQueueStore 需在 AppLayout 内使用')
  return store
}

/** 供 app store 复用 WS 合并逻辑 */
export function applyWsJobToAppJob(job, trackPipelineNodes, ev) {
  job.status = ev.status || job.status
  job.currentNode = ev.current_node ?? null
  job.progress = ev.progress ?? job.progress
  const trackForMerge =
    job.trackPipelineNodes?.length > 0
      ? job.trackPipelineNodes
      : (ev.execution_track_nodes || []).map((id) => ({ node_id: id }))
  job.completedNodeIds = mergeCompletedNodeIds(
    job.completedNodeIds,
    ev.completed_nodes,
    trackForMerge,
    ev.current_node,
  )
}
