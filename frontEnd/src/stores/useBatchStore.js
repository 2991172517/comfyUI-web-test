import { inject, onUnmounted, provide, reactive, ref } from 'vue'
import { api, statusLabel } from '@/api/client.js'
import { encodeWorkflowSnapshot, snapshotFromBatchCell } from '@/lib/workflowRestore.js'
import { buildBatchFavoritePayload } from '@/utils/favoritePayload.js'
import {
  applyPromptConfigTo,
  normalizePromptConfig,
  promptConfigHasContent,
  serializePromptConfig,
} from '@/composables/usePromptConfig.js'

const BATCH_STORE = Symbol('batchStore')

const DEFAULT_FILENAME_TEMPLATE =
  '{batch_id}/g{index:02d}_{a_name}_w{a_w}_{a_dir}_x_{b_name}_w{b_w}_{b_dir}_seed{seed}'

/** @param {ReturnType<typeof import('./useAppStore.js').createAppStore>} app */
export function createBatchStore(app) {
  if (!app) throw new Error('createBatchStore(app) requires app store from createAppStore()')

  const batch = reactive({
    batchId: '',
    status: 'idle',
    statusText: '空闲',
    total: 0,
    completed: 0,
    message: '',
    items: [],
    grid: null,
    currentLabel: '',
  })

  const form = reactive({
    seedMode: 'fixed',
    seed: 0,
    syncClip: true,
    filenameTemplate: DEFAULT_FILENAME_TEMPLATE,
  })

  const batchPromptSaving = ref(false)

  /** @type {Record<string, object>} 每个 LoRA 节点：固定权重或扫参 */
  const loraAxisState = reactive({})

  const preview = ref(null)
  const historyRecords = ref([])
  const historyLoading = ref(false)
  const selectedHistoryId = ref('')
  const historyTaskId = ref('')
  const runConfig = ref(null)
  let batchPollTimer = null

  function isBatchRunningNow() {
    return ['running', 'cancelling'].includes(batch.status)
  }

  function batchProgressPercent() {
    if (!batch.total) return 0
    return Math.round((batch.completed / batch.total) * 100)
  }

  function syncLoraAxisState() {
    const ids = new Set(app.workflowLoras.map((l) => l.node_id))
    for (const id of Object.keys(loraAxisState)) {
      if (!ids.has(id)) delete loraAxisState[id]
    }
    for (const l of app.workflowLoras) {
      if (!loraAxisState[l.node_id]) {
        loraAxisState[l.node_id] = {
          enabled: false,
          sweepRole: null,
          start: l.strength_model ?? 0.5,
          step: 0.1,
          direction: 'up',
          count: 4,
          fixedModel: l.strength_model ?? 1,
          fixedClip: l.strength_clip ?? 1,
          loraName: l.lora_name || '',
        }
      } else {
        loraAxisState[l.node_id].loraName = l.lora_name || loraAxisState[l.node_id].loraName
      }
    }
    reassignSweepRoles()
  }

  function reassignSweepRoles() {
    const pool = app.workflowLoras.filter((l) => {
      if (l.role === 'style' && !app.styleEnabled) return false
      return true
    })
    const enabled = pool.filter((l) => loraAxisState[l.node_id]?.enabled)
    const byRole = (role) => enabled.find((l) => l.role === role)
    const char = byRole('character')
    const style = byRole('style')
    if (char) loraAxisState[char.node_id].sweepRole = 'A'
    if (style && style !== char) loraAxisState[style.node_id].sweepRole = 'B'
    let slot = char && style && style !== char ? 2 : char ? 1 : 0
    for (const l of enabled) {
      if (l === char || l === style) continue
      loraAxisState[l.node_id].sweepRole = slot === 0 ? 'A' : slot === 1 ? 'B' : null
      slot += 1
    }
  }

  function toggleLoraSweep(nodeId, enabled) {
    if (!loraAxisState[nodeId]) return
    const enabledList = app.workflowLoras.filter((l) => loraAxisState[l.node_id]?.enabled)
    if (enabled && enabledList.length >= 2 && !loraAxisState[nodeId].enabled) {
      app.setMessage('最多 2 个 LoRA 参与扫参', true)
      return
    }
    loraAxisState[nodeId].enabled = enabled
    reassignSweepRoles()
  }

  function enabledSweepLoras() {
    return app.workflowLoras.filter((l) => loraAxisState[l.node_id]?.enabled)
  }

  function plannedBatchTotal() {
    const en = enabledSweepLoras()
    if (!en.length) return 0
    const counts = en.map((l) => Math.max(1, loraAxisState[l.node_id]?.count || 1))
    if (counts.length === 1) return counts[0]
    return counts[0] * counts[1]
  }

  function gridCellsMatrix() {
    const cols = batch.grid?.b_count || 1
    const rows = batch.grid?.a_count || 1
    const matrix = Array.from({ length: rows }, () => Array(cols).fill(null))
    for (const item of batch.items) {
      const ia = item.ia ?? item.grid_ia
      const ib = item.ib ?? item.grid_ib
      if (ia != null && ib != null && matrix[ia]) {
        matrix[ia][ib] = item
      }
    }
    return { matrix, cols, rows }
  }

  function applyDefaultStrategy() {
    syncLoraAxisState()
    for (const l of app.workflowLoras) {
      const st = loraAxisState[l.node_id]
      if (!st) continue
      st.enabled = false
      st.sweepRole = null
    }
    if (app.workflowTargets?.seed_nodes?.length) {
      form.seed = app.workflowTargets.seed_nodes[0].seed ?? 0
    }
  }

  function buildLoraAxesPayload() {
    return app.workflowLoras.map((l) => {
      const st = loraAxisState[l.node_id] || {}
      return {
        node_id: l.node_id,
        enabled: !!st.enabled,
        alias: l.short_name || l.node_id,
        sweep_role: st.sweepRole,
        start: st.start,
        step: st.step,
        direction: st.direction,
        count: st.count,
        fixed_strength_model: st.fixedModel,
        fixed_strength_clip: st.fixedClip,
        lora_name: st.loraName || l.lora_name,
      }
    })
  }

  function buildBatchBody() {
    const base = { ...app.overrides }
    for (const l of app.workflowLoras) {
      const st = loraAxisState[l.node_id]
      if (!st || st.enabled) continue
      if (!base[l.node_id]) base[l.node_id] = {}
      if (st.loraName) base[l.node_id].lora_name = st.loraName
      base[l.node_id].strength_model = st.fixedModel
      base[l.node_id].strength_clip = form.syncClip ? st.fixedModel : st.fixedClip
    }
    return {
      base_overrides: base,
      style_enabled: app.styleEnabled,
      batch_prompts: serializePromptConfig(app.sessionPrompts),
      prompt_global_priority: !!app.sessionPrompts.merge?.random_before_workflow,
      seed_mode: form.seedMode,
      seed: form.seed,
      sync_clip: form.syncClip,
      save_node_id: app.workflowTargets?.save_node_id,
      seed_node_id: app.workflowTargets?.seed_node_id,
      filename_template: form.filenameTemplate,
      lora_axes: buildLoraAxesPayload(),
    }
  }

  function stopBatchPoll() {
    if (batchPollTimer) {
      clearInterval(batchPollTimer)
      batchPollTimer = null
    }
  }

  function applyBatchEntry(entry) {
    batch.batchId = entry.batch_id || batch.batchId
    batch.status = entry.status || 'idle'
    batch.statusText = statusLabel(batch.status)
    batch.total = entry.total || 0
    batch.completed = entry.completed || 0
    batch.message = entry.message || ''
    batch.items = entry.items || []
    batch.grid = entry.plan?.grid || batch.grid
    batch.currentLabel = entry.current_label || ''
  }

  async function loadBatchPromptConfig() {
    const res = await api.getBatchPromptConfig()
    const cfg = normalizePromptConfig(res.config)
    if (!promptConfigHasContent(app.sessionPrompts) && promptConfigHasContent(cfg)) {
      applyPromptConfigTo(app.sessionPrompts, cfg)
    }
  }

  async function saveBatchPromptConfig() {
    batchPromptSaving.value = true
    try {
      const payload = serializePromptConfig(app.sessionPrompts)
      await api.saveBatchPromptConfig(payload)
      const cfg = normalizePromptConfig(payload)
      applyPromptConfigTo(app.sessionPrompts, cfg)
      app.setMessage('当次提示词已保存为批量默认配置')
    } catch (e) {
      app.setMessage(e.message, true)
    } finally {
      batchPromptSaving.value = false
    }
  }

  async function refreshHistory(taskId = null) {
    historyLoading.value = true
    const tid = (taskId ?? historyTaskId.value) || null
    try {
      const res = await api.listBatches(80, tid || null)
      historyRecords.value = res.batches || []
    } catch (e) {
      app.setMessage(e.message, true)
    } finally {
      historyLoading.value = false
    }
  }

  async function openHistoryRecord(rec) {
    if (!rec?.batch_id) return
    selectedHistoryId.value = rec.batch_id
    stopBatchPoll()
    try {
      const entry = await api.getBatch(rec.batch_id)
      applyBatchEntry(entry)
      runConfig.value = entry.run_config || null
      preview.value = null
      if (['running', 'cancelling'].includes(entry.status)) {
        batchPollTimer = setInterval(pollBatch, 1200)
      }
    } catch (e) {
      app.setMessage(e.message, true)
    }
  }

  function formatRecordTime(iso) {
    if (!iso) return '—'
    try {
      return new Date(iso).toLocaleString('zh-CN', { hour12: false })
    } catch {
      return iso
    }
  }

  async function pollBatch() {
    if (!batch.batchId) return
    try {
      const entry = await api.getBatch(batch.batchId)
      applyBatchEntry(entry)
      if (entry.run_config) runConfig.value = entry.run_config
      if (['completed', 'failed', 'cancelled', 'deleted'].includes(entry.status)) {
        stopBatchPoll()
        refreshHistory()
        app.setMessage(entry.error || `批量完成 ${entry.completed}/${entry.total}`)
      }
    } catch (e) {
      app.setMessage(e.message, true)
    }
  }

  async function previewPlan() {
    if (!app.selectedId) return
    try {
      const res = await api.batchPreview(app.selectedId, buildBatchBody())
      preview.value = res.plan
      app.setMessage(`预览：共 ${res.plan.grid.total} 张（${res.plan.grid.a_count}×${res.plan.grid.b_count}）`)
    } catch (e) {
      app.setMessage(e.message, true)
    }
  }

  async function startBatch() {
    if (!app.selectedId || isBatchRunningNow()) return
    try {
      const res = await api.startBatch(app.selectedId, buildBatchBody())
      batch.batchId = res.batch_id
      batch.total = res.total
      batch.grid = res.grid
      batch.status = 'running'
      batch.statusText = statusLabel('running')
      batch.completed = 0
      batch.items = []
      batch.message = `批量已开始，共 ${res.total} 张`
      app.setMessage(batch.message)
      stopBatchPoll()
      pollBatch()
      batchPollTimer = setInterval(pollBatch, 1200)
      refreshHistory()
    } catch (e) {
      app.setMessage(e.message, true)
    }
  }

  async function cancelBatch() {
    if (!batch.batchId) return
    try {
      await api.cancelBatch(batch.batchId)
      app.setMessage('已请求取消批量任务')
      pollBatch()
    } catch (e) {
      app.setMessage(e.message, true)
    }
  }

  async function deleteBatch() {
    if (!batch.batchId) return
    if (!confirm('删除本批次所有输出文件与目录？')) return
    try {
      await api.deleteBatch(batch.batchId)
      batch.items = []
      batch.status = 'deleted'
      batch.statusText = statusLabel('deleted')
      stopBatchPoll()
      selectedHistoryId.value = ''
      refreshHistory()
      app.setMessage('已删除批次输出')
    } catch (e) {
      app.setMessage(e.message, true)
    }
  }

  function cellImage(item) {
    if (!item?.images?.length) return null
    return item.images[0]
  }

  function currentBatchWorkflowId() {
    return runConfig.value?.workflow_id || app.selectedId
  }

  function workflowSnapshotForCell(cell) {
    return snapshotFromBatchCell(cell, runConfig.value)
  }

  function encodeRestoreQuery(cell) {
    return encodeWorkflowSnapshot(workflowSnapshotForCell(cell))
  }

  function batchImagesForLightbox() {
    const list = []
    for (const item of batch.items) {
      const img = cellImage(item)
      if (img?.url) {
        const picks = (item.prompt_picks || [])
          .map((p) => `${p.group_name || ''}: ${p.text || ''}`)
          .filter(Boolean)
          .join(' · ')
        list.push({
          url: img.url,
          title: [item.filename_hint || item.label || img.filename, picks].filter(Boolean).join('\n'),
          cell: item,
        })
      }
    }
    return list
  }

  function batchFavoritePayload(cell) {
    return buildBatchFavoritePayload(app.selectedId, cell, batch.batchId, app.overrides)
  }

  async function downloadImage(img) {
    const res = await fetch(img.url)
    if (!res.ok) throw new Error('下载失败')
    const blob = await res.blob()
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = img.filename
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(a.href)
  }

  function statusBadgeVariant(status) {
    if (status === 'completed') return 'success'
    if (['failed', 'cancelled', 'deleted'].includes(status)) return 'destructive'
    if (['running', 'cancelling', 'pending'].includes(status)) return 'default'
    return 'secondary'
  }

  onUnmounted(stopBatchPoll)

  const store = reactive({
    batch,
    form,
    preview,
    historyRecords,
    historyLoading,
    selectedHistoryId,
    historyTaskId,
    runConfig,

    get isBatchRunning() {
      return isBatchRunningNow()
    },
    get batchProgress() {
      return batchProgressPercent()
    },
    get gridCells() {
      return gridCellsMatrix()
    },
    get loras() {
      return app.workflowLoras
    },
    loraAxisState,
    batchPromptSaving,
    get plannedTotal() {
      return plannedBatchTotal()
    },

    syncLoraAxisState,
    toggleLoraSweep,
    reassignSweepRoles,
    enabledSweepLoras,
    applyDefaultStrategy,
    loadBatchPromptConfig,
    saveBatchPromptConfig,
    buildBatchBody,
    stopBatchPoll,
    refreshHistory,
    openHistoryRecord,
    formatRecordTime,
    previewPlan,
    startBatch,
    cancelBatch,
    deleteBatch,
    cellImage,
    batchImagesForLightbox,
    workflowSnapshotForCell,
    encodeRestoreQuery,
    batchFavoritePayload,
    downloadImage,
    statusBadgeVariant,
  })

  provide(BATCH_STORE, store)
  return store
}

export function useBatchStore() {
  const store = inject(BATCH_STORE)
  if (!store) throw new Error('useBatchStore must be used within AppLayout')
  return store
}
