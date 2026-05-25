import { inject, onUnmounted, provide, reactive, ref } from 'vue'
import { api, GROUP_HINTS, statusLabel } from '@/api/client.js'
import { useFavorites } from '@/composables/useFavorites.js'
import { applyQuotaFromApi } from '@/composables/useAuth.js'
import {
  applyPromptConfigTo,
  emptyBatchPromptConfig,
  normalizePromptConfig,
  serializePromptConfig,
  promptConfigHasContent,
} from '@/composables/usePromptConfig.js'
import { isPngRestoreWorkflowId } from '@/lib/workflowCategories.js'
import {
  resolveRestoreWorkflowId,
  WORKFLOW_TEMPLATE_ID,
} from '@/lib/workflowRestore.js'
import {
  discoverPipelineNodesFromPrompt,
  discoverPreviewNodesFromPrompt,
  filterPipelineForExecution,
} from '@/lib/discoverPreviewNodes.js'
import { mergeCompletedNodeIds } from '@/lib/mergeJobProgress.js'
import { isGenerateWsConnected } from '@/lib/generateQueueWs.js'
import { applyWsJobToAppJob } from '@/stores/useGenerateQueueStore.js'
import { getConfirmDialog } from '@/composables/useConfirmDialog.js'
import {
  buildSessionLorasForUi,
  createSessionLoraChain,
  isSessionLoraId,
  newSessionLoraId,
  serializeSessionLoraChain,
  sessionChainIsDirty,
} from '@/lib/sessionLoraChain.js'

const APP_STORE = Symbol('appStore')

export function createAppStore() {
  const health = ref(null)
  const workflows = ref([])
  const selectedId = ref('')
  const loading = ref(false)
  const message = ref('')
  const error = ref('')

  const state = reactive({ format: 'api', nodes: [] })
  const workflowLoras = ref([])
  const workflowTargets = ref({})
  const workflowMeta = ref(null)
  const styleEnabled = ref(false)
  const isMasterWorkflow = ref(false)
  const overrides = reactive({})
  const modelLists = reactive({
    checkpoints: [],
    loras: [],
    checkpointCatalog: [],
    loraCatalog: [],
  })
  const modelsLoading = ref(false)
  const sessionPrompts = reactive(emptyBatchPromptConfig())
  const sessionPromptPresetId = ref('')
  const sessionPromptPresetName = ref('')
  const promptEncode = ref(null)
  /** 流水线全节点（总体预览，按 ID 排序） */
  const pipelineNodes = ref([])
  /** 仅 PreviewImage（兼容） */
  const previewNodes = ref([])
  /** 本次/默认启用的预览节点 ID；空 = 仅 SaveImage */
  const enabledPreviewNodeIds = ref([])
  /** 每次从历史快照恢复后递增，用于强制刷新 LoRA 等表单控件 */
  const restoreEpoch = ref(0)
  /** 「以此生成」等恢复的 PNG/缺失工作流，生成页显示为临时工作流 */
  const temporaryWorkflowActive = ref(false)
  const temporaryWorkflowHint = ref('')
  /** 生成页临时 LoRA 链（不写回工作流文件） */
  const sessionLoraChain = ref(null)
  /** 最近一次单张入队的最终正/负全文（前端 merge-preview 结果，便于复制排错） */
  const lastQueuedPrompts = ref(null)

  const job = reactive({
    promptId: '',
    clientId: '',
    status: 'idle',
    statusText: '',
    currentNode: null,
    progress: null,
    message: '',
    images: [],
    /** 本次 queue 实际执行的节点（已去掉未勾选预览） */
    trackPipelineNodes: [],
    completedNodeIds: [],
  })

  let pollTimer = null
  let pollActive = false
  let pollBurstCount = 0
  const POLL_BURST_MS = 200
  const POLL_BURST_MAX = 12
  const POLL_MS_ACTIVE = 400
  const POLL_MS_PENDING = 700
  const POLL_MS_FINALIZING = 450
  const { refreshFavorites } = useFavorites()

  function setMessage(text, isError = false) {
    message.value = text
    error.value = isError ? text : ''
  }

  function resetJob() {
    Object.assign(job, {
      promptId: '',
      clientId: '',
      status: 'idle',
      statusText: '',
      currentNode: null,
      progress: null,
      message: '',
      images: [],
      trackPipelineNodes: [],
      completedNodeIds: [],
    })
  }

  function stopPoll() {
    pollActive = false
    if (pollTimer) {
      clearTimeout(pollTimer)
      pollTimer = null
    }
  }

  function pollIntervalMs() {
    if (pollBurstCount < POLL_BURST_MAX) return POLL_BURST_MS
    if (job.status === 'finalizing') return POLL_MS_FINALIZING
    if (job.status === 'in_progress') return POLL_MS_ACTIVE
    return POLL_MS_PENDING
  }

  function scheduleJobPoll(promptId) {
    if (!pollActive) return
    pollTimer = setTimeout(async () => {
      if (!pollActive) return
      await pollJobOnce(promptId)
      if (!pollActive) return
      pollBurstCount += 1
      scheduleJobPoll(promptId)
    }, pollIntervalMs())
  }

  function nid(nodeId) {
    return String(nodeId)
  }

  function ensureOverride(nodeId, key, fallback) {
    const id = nid(nodeId)
    if (!overrides[id]) overrides[id] = {}
    if (overrides[id][key] === undefined) overrides[id][key] = fallback
    return overrides[id][key]
  }

  /** 强制写入节点参数（用于历史快照恢复，必须覆盖母版默认值） */
  function applyOverridesPatch(patch, { force = true } = {}) {
    if (!patch || typeof patch !== 'object') return
    for (const [nodeId, nodePatch] of Object.entries(patch)) {
      if (!nodePatch || typeof nodePatch !== 'object') continue
      const id = nid(nodeId)
      if (!overrides[id]) overrides[id] = {}
      for (const [key, val] of Object.entries(nodePatch)) {
        if (force || overrides[id][key] === undefined) {
          overrides[id][key] = val
        }
      }
    }
  }

  function loraShortName(filename) {
    return String(filename || '').replace(/\.(safetensors|ckpt|pt)$/i, '')
  }

  /** 将 overrides 中的 LoRA/权重同步到 workflowLoras，避免界面仍显示母版默认名 */
  function syncWorkflowLorasFromOverrides() {
    workflowLoras.value = (workflowLoras.value || []).map((l) => {
      const id = nid(l.node_id)
      const patch = overrides[id]
      if (!patch) return l
      const loraName = patch.lora_name ?? l.lora_name
      return {
        ...l,
        lora_name: loraName,
        short_name: loraShortName(loraName) || l.short_name,
        strength_model:
          patch.strength_model !== undefined ? patch.strength_model : l.strength_model,
        strength_clip:
          patch.strength_clip !== undefined ? patch.strength_clip : l.strength_clip,
      }
    })
  }

  function fieldValue(nodeId, field) {
    const id = nid(nodeId)
    if (overrides[id] && overrides[id][field.key] !== undefined) {
      return overrides[id][field.key]
    }
    return field.value
  }

  function updateField(nodeId, key, value) {
    const id = nid(nodeId)
    if (!overrides[id]) overrides[id] = {}
    overrides[id][key] = value
    if (key === 'lora_name' || key === 'strength_model' || key === 'strength_clip') {
      syncWorkflowLorasFromOverrides()
    }
  }

  function isGeneratingNow() {
    return ['pending', 'in_progress', 'finalizing'].includes(job.status)
  }

  /** 当前工作流中选中的 Checkpoint（ckpt_name） */
  function getActiveCheckpointName() {
    for (const node of state.nodes || []) {
      for (const field of node.fields || []) {
        if (field.key === 'ckpt_name') {
          const v = fieldValue(node.id, field)
          return String(v || '').trim()
        }
      }
    }
    return ''
  }

  function groupHint(group) {
    return GROUP_HINTS[group] || GROUP_HINTS['其他']
  }

  function isModelSelectField(field) {
    return (
      field.type === 'model_select' ||
      field.key === 'ckpt_name' ||
      field.key === 'lora_name'
    )
  }

  function modelFolderForField(field) {
    if (field.model_folder) return field.model_folder
    if (field.key === 'ckpt_name') return 'checkpoints'
    if (field.key === 'lora_name') return 'loras'
    return 'checkpoints'
  }

  function modelOptions(field) {
    return modelLists[modelFolderForField(field)] || []
  }

  function modelCatalogForFolder(folder) {
    if (folder === 'loras') return modelLists.loraCatalog
    if (folder === 'checkpoints') return modelLists.checkpointCatalog
    return []
  }

  function modelSelectMissing(nodeId, field) {
    const v = fieldValue(nodeId, field)
    return v && !modelOptions(field).includes(v)
  }

  async function refreshHealth() {
    health.value = await api.health()
    if (health.value?.ok) await loadModelLists()
  }

  async function loadModelLists() {
    if (!health.value?.ok) return
    modelsLoading.value = true
    try {
      const [ckpt, lora] = await Promise.all([
        api.listModels('checkpoints', true),
        api.listModels('loras', true),
      ])
      const ckptCatalog = ckpt.models || []
      modelLists.checkpointCatalog = ckptCatalog
      modelLists.checkpoints =
        ckpt.files?.length > 0
          ? ckpt.files
          : ckptCatalog.map((m) => m.name).filter(Boolean)
      const loraCatalog = lora.models || []
      modelLists.loraCatalog = loraCatalog
      modelLists.loras =
        lora.files?.length > 0
          ? lora.files
          : loraCatalog.map((m) => m.name).filter(Boolean)
    } catch (e) {
      setMessage(`加载模型列表失败: ${e.message}`, true)
    } finally {
      modelsLoading.value = false
    }
  }

  async function loadWorkflowList() {
    const res = await api.listWorkflows()
    workflows.value = (res.workflows || []).filter(
      (w) => w.format === 'api' && !String(w.id || '').includes('.meta'),
    )
    if (!selectedId.value && workflows.value.length) {
      const pick =
        workflows.value.find((w) => w.category === 'generate') || workflows.value[0]
      selectedId.value = pick.id
      await loadWorkflow(selectedId.value)
    }
  }

  async function applyLoraSlotDefaults(nodeId, loraName) {
    const name = String(loraName || '').trim()
    if (!name) return
    try {
      const res = await api.getLoraModelDefaults(name)
      const d = res.defaults
      if (!d || d.strength_model == null) return
      applyOverridesPatch(
        {
          [nodeId]: {
            strength_model: d.strength_model,
            strength_clip: d.strength_clip ?? d.strength_model,
          },
        },
        { force: true },
      )
      syncWorkflowLorasFromOverrides()
    } catch {
      /* ignore */
    }
  }

  async function loadWorkflow(id, savedOverrides = null, opts = {}) {
    if (!id) return
    loading.value = true
    setMessage('')
    try {
      const styleQ =
        opts.styleEnabled !== undefined ? opts.styleEnabled : styleEnabled.value
      const res = await api.getWorkflow(id, styleQ)
      state.format = res.format
      state.nodes = res.nodes
      workflowLoras.value = res.loras || []
      workflowTargets.value = res.targets || {}
      workflowMeta.value = res.meta || null
      promptEncode.value = res.prompt_encode || null
      styleEnabled.value = !!res.style_enabled
      isMasterWorkflow.value = false
      let pipeline = res.pipeline_nodes || []
      if (!pipeline.length) {
        pipeline = discoverPipelineNodesFromPrompt(res.prompt)
      }
      if (!pipeline.length) {
        try {
          const pn = await api.getWorkflowPreviewNodes(id)
          pipeline = pn.pipeline_nodes || []
          if (pn.enabled_preview_node_ids && !res.enabled_preview_node_ids) {
            res.enabled_preview_node_ids = pn.enabled_preview_node_ids
          }
        } catch {
          /* ignore */
        }
      }
      pipelineNodes.value = pipeline
      previewNodes.value = pipeline.filter((n) => n.is_preview)
      enabledPreviewNodeIds.value = (res.enabled_preview_node_ids || []).map(String)
      resetSessionLoraChain()
      Object.keys(overrides).forEach((k) => delete overrides[k])
      for (const node of res.nodes) {
        for (const field of node.fields) {
          ensureOverride(node.id, field.key, field.value)
        }
      }
      if (savedOverrides && typeof savedOverrides === 'object') {
        applyOverridesPatch(savedOverrides, { force: true })
        syncWorkflowLorasFromOverrides()
      }
      selectedId.value = id
      await loadModelLists()
    } catch (e) {
      setMessage(e.message, true)
    } finally {
      loading.value = false
    }
  }

  async function applyFavorite(fav) {
    if (!fav?.workflow_id) {
      setMessage('收藏记录缺少工作流 ID', true)
      return false
    }
    await loadWorkflow(fav.workflow_id, fav.params?.overrides || {})
    setMessage(
      `已加载收藏「${fav.label || fav.workflow_id}」的参数，可修改提示词后生成`,
    )
    return true
  }

  async function resolveWorkflowForRestore(snap) {
    if (!workflows.value.length) {
      await loadWorkflowList()
    }
    const requested = (snap?.workflow_id || '').trim()
    const { id, usedFallback, missingId } = resolveRestoreWorkflowId(
      requested,
      workflows.value,
    )
    return { id, usedFallback, missingId, requested }
  }

  function applySeedOverridesFromSnapshot(snap) {
    if (snap?.seed == null) return
    const nodes = workflowTargets.value?.seed_nodes || []
    if (nodes.length) {
      for (const sn of nodes) {
        const field = sn.seed_field || 'seed'
        ensureOverride(String(sn.node_id), field, snap.seed)
      }
      return
    }
    const fallback = workflowTargets.value?.seed_node_id
    if (fallback) ensureOverride(String(fallback), 'seed', snap.seed)
  }

  function clearTemporaryWorkflow() {
    temporaryWorkflowActive.value = false
    temporaryWorkflowHint.value = ''
  }

  function markTemporaryWorkflow(snap, { id, usedFallback, missingId }) {
    const temp = !!(
      snap?.temporary_workflow ||
      snap?.imported_variant ||
      isPngRestoreWorkflowId(id) ||
      (usedFallback && missingId)
    )
    temporaryWorkflowActive.value = temp
    temporaryWorkflowHint.value =
      temp && missingId && missingId !== id ? String(missingId) : ''
  }

  async function applyWorkflowSnapshot(snap) {
    if (snap?.imported_variant || snap?.restore_source === 'png_metadata') {
      await loadWorkflowList()
    }
    const { id, usedFallback, missingId, requested } = await resolveWorkflowForRestore(snap)
    if (!id) {
      setMessage('没有可用的工作流文件，请先将 API 工作流放入 workflows/', true)
      return false
    }
    const style =
      snap.style_enabled !== undefined && snap.style_enabled !== null
        ? !!snap.style_enabled
        : styleEnabled.value
    await loadWorkflow(id, {}, { styleEnabled: style })
    applyOverridesPatch(snap.overrides || {}, { force: true })
    syncWorkflowLorasFromOverrides()
    restoreEpoch.value += 1
    if (snap.style_enabled != null) {
      styleEnabled.value = !!snap.style_enabled
    }
    applySeedOverridesFromSnapshot(snap)
    if (snap.batch_prompts) {
      applyPromptConfigTo(sessionPrompts, normalizePromptConfig(snap.batch_prompts))
    } else {
      clearSessionPrompts()
    }
    markTemporaryWorkflow(snap, { id, usedFallback, missingId })
    if (snap.restore_message) {
      setMessage(snap.restore_message)
    } else if (usedFallback && missingId) {
      setMessage(
        `原工作流「${missingId}」不在列表中，已用「${id === WORKFLOW_TEMPLATE_ID ? '母版' : id}」拓扑恢复参数`,
      )
    } else {
      setMessage('')
    }
    return true
  }

  async function setStyleEnabled(enabled) {
    styleEnabled.value = !!enabled
    if (!selectedId.value) return
    try {
      await api.updateWorkflowMeta(selectedId.value, { style_enabled: styleEnabled.value })
      await loadWorkflow(selectedId.value, { ...overrides }, { styleEnabled: styleEnabled.value })
      setMessage(styleEnabled.value ? '已启用 Style LoRA 链' : '已关闭 Style（绕过 #16）')
    } catch (e) {
      setMessage(e.message, true)
    }
  }

  function setEnabledPreviewNodeIds(ids) {
    const sorted = [...ids].map(String).sort((a, b) => {
      const na = Number(a)
      const nb = Number(b)
      if (!Number.isNaN(na) && !Number.isNaN(nb)) return na - nb
      return a.localeCompare(b)
    })
    enabledPreviewNodeIds.value = sorted
  }

  function previewNodeLabel(nodeId) {
    const id = String(nodeId)
    const saveId = workflowTargets.value?.save_node_id
    if (saveId && id === String(saveId)) return '保存图像'
    const hit = previewNodes.value.find((n) => String(n.node_id) === id)
    return hit?.title || `节点 #${id}`
  }

  async function savePreviewNodeSelection({ quiet = false } = {}) {
    if (!selectedId.value) return
    try {
      await api.updateWorkflowMeta(selectedId.value, {
        enabled_preview_node_ids: [...enabledPreviewNodeIds.value],
      })
      if (workflowMeta.value) {
        workflowMeta.value = {
          ...workflowMeta.value,
          enabled_preview_node_ids: [...enabledPreviewNodeIds.value],
        }
      }
      if (!quiet) setMessage('预览节点默认已保存')
    } catch (e) {
      setMessage(e.message, true)
    }
  }

  async function saveWorkflow() {
    if (!selectedId.value) return
    loading.value = true
    try {
      await api.saveWorkflow(selectedId.value, { ...overrides })
      setMessage(`已保存到子工作流（${state.format}）`)
    } catch (e) {
      setMessage(e.message, true)
    } finally {
      loading.value = false
    }
  }

  async function refreshWorkflowAfterChainEdit(workflowId) {
    const wid = workflowId || selectedId.value
    if (!wid) return
    await loadWorkflow(wid)
    if (wid === selectedId.value) {
      syncWorkflowLorasFromOverrides()
      restoreEpoch.value += 1
    }
  }

  async function addLoraChainSlot(loraName, workflowId = null) {
    const wid = workflowId || selectedId.value
    if (!wid || !loraName) return
    try {
      await api.addLoraSlot(wid, { role: 'character', lora_name: loraName })
      await refreshWorkflowAfterChainEdit(wid)
      if (wid === selectedId.value) setMessage('已添加 LoRA')
    } catch (e) {
      setMessage(e.message, true)
      throw e
    }
  }

  async function removeLoraChainSlot(nodeId, workflowId = null) {
    const wid = workflowId || selectedId.value
    if (!wid) return
    try {
      await api.removeLoraSlot(wid, nodeId)
      await refreshWorkflowAfterChainEdit(wid)
      if (wid === selectedId.value) setMessage('已移除 LoRA')
    } catch (e) {
      setMessage(e.message, true)
      throw e
    }
  }

  async function reorderLoraChain(nodeIds, workflowId = null) {
    const wid = workflowId || selectedId.value
    if (!wid || !nodeIds?.length) return
    try {
      await api.reorderLoraSlots(wid, nodeIds)
      await refreshWorkflowAfterChainEdit(wid)
    } catch (e) {
      setMessage(e.message, true)
      throw e
    }
  }

  function resetSessionLoraChain() {
    sessionLoraChain.value = null
  }

  function initSessionLoraChain() {
    if (sessionLoraChain.value) return sessionLoraChain.value
    sessionLoraChain.value = createSessionLoraChain(workflowLoras.value)
    return sessionLoraChain.value
  }

  function sessionLoraPayloadForQueue() {
    if (!sessionLoraChain.value) return null
    const base = workflowLoras.value.map((l) => String(l.node_id))
    if (!sessionChainIsDirty(sessionLoraChain.value, base)) return null
    return serializeSessionLoraChain(sessionLoraChain.value)
  }

  async function sessionAddLora(loraName) {
    if (!loraName) return
    initSessionLoraChain()
    const id = newSessionLoraId()
    let sm = 0.65
    let sc = 0.65
    try {
      const res = await api.getLoraModelDefaults(loraName)
      const d = res?.defaults
      if (d?.strength_model != null) sm = Number(d.strength_model)
      if (d?.strength_clip != null) sc = Number(d.strength_clip)
    } catch {
      /* defaults */
    }
    sessionLoraChain.value.added.push({
      id,
      lora_name: loraName,
      strength_model: sm,
      strength_clip: sc,
      role: 'character',
    })
    sessionLoraChain.value.order.push(id)
    ensureOverride(id, 'lora_name', loraName)
    ensureOverride(id, 'strength_model', sm)
    ensureOverride(id, 'strength_clip', sc)
    setMessage('已添加 LoRA（仅本次生成生效）')
  }

  function sessionRemoveLora(nodeId) {
    initSessionLoraChain()
    const id = String(nodeId)
    if (isSessionLoraId(id)) {
      sessionLoraChain.value.added = sessionLoraChain.value.added.filter((a) => a.id !== id)
      sessionLoraChain.value.order = sessionLoraChain.value.order.filter((x) => x !== id)
      delete overrides[id]
    } else {
      if (!sessionLoraChain.value.hidden.includes(id)) {
        sessionLoraChain.value.hidden.push(id)
      }
      sessionLoraChain.value.order = sessionLoraChain.value.order.filter((x) => x !== id)
    }
    setMessage('已移除 LoRA（仅本次生成生效）')
  }

  function sessionMoveLora(nodeId, delta) {
    initSessionLoraChain()
    const order = [...sessionLoraChain.value.order]
    const idx = order.indexOf(String(nodeId))
    if (idx < 0) return
    const to = idx + delta
    if (to < 0 || to >= order.length) return
    const [item] = order.splice(idx, 1)
    order.splice(to, 0, item)
    sessionLoraChain.value.order = order
  }

  function sessionReorderLoras(nodeIds) {
    initSessionLoraChain()
    const hidden = sessionLoraChain.value.hidden || []
    const tail = sessionLoraChain.value.order.filter(
      (id) => hidden.includes(id) && !nodeIds.includes(id),
    )
    sessionLoraChain.value.order = [...nodeIds, ...tail]
  }

  function applyWsJobEvent(ev) {
    if (!job.promptId || ev.prompt_id !== job.promptId) return
    applyWsJobToAppJob(job, job.trackPipelineNodes, ev)
    job.statusText = statusLabel(job.status)
    if (ev.status === 'completed' && !(job.images || []).length) {
      api.getJob(ev.prompt_id).then(applyJobDetail).catch(() => {})
    }
    if (['completed', 'failed', 'cancelled'].includes(job.status)) {
      stopPoll()
      if (job.status === 'completed') {
        const previewIds = new Set(
          (job.trackPipelineNodes || [])
            .filter((n) => n.is_preview)
            .map((n) => String(n.node_id)),
        )
        const finalCount = (job.images || []).filter(
          (img) => !previewIds.has(String(img.node_id)),
        ).length
        if (finalCount) setMessage(`生成完成，终图 ${finalCount} 张`)
      } else if (job.status === 'failed') {
        setMessage(job.message || '生成失败', true)
      }
    }
  }

  function applyJobDetail(detail) {
    job.status = detail.status || 'unknown'
    job.statusText = statusLabel(job.status)
    job.message = detail.message || ''
    job.currentNode = detail.current_node ?? null
    job.progress = detail.progress ?? null
    job.images = detail.images || []
    if (detail.execution_track_nodes?.length && !job.trackPipelineNodes.length) {
      const byId = new Map(pipelineNodes.value.map((n) => [String(n.node_id), n]))
      job.trackPipelineNodes = detail.execution_track_nodes
        .map((id) => byId.get(String(id)))
        .filter(Boolean)
    }
    const trackForMerge =
      job.trackPipelineNodes?.length > 0
        ? job.trackPipelineNodes
        : (detail.execution_track_nodes || []).map((id) => ({ node_id: id }))
    job.completedNodeIds = mergeCompletedNodeIds(
      job.completedNodeIds,
      detail.completed_nodes,
      trackForMerge,
      detail.current_node,
    )
  }

  async function pollJobUntilDone(promptId) {
    const detail = await api.getJob(promptId)
    applyJobDetail(detail)
    if (detail.status === 'cancelled') {
      stopPoll()
      setMessage(job.message || '已取消生成')
      return
    }
    if (detail.status === 'failed') {
      stopPoll()
      setMessage(job.message || '生成失败', true)
      return
    }
    if (detail.status === 'completed') {
      stopPoll()
      const previewIds = new Set(
        (job.trackPipelineNodes || [])
          .filter((n) => n.is_preview)
          .map((n) => String(n.node_id)),
      )
      const finalCount = (job.images || []).filter(
        (img) => !previewIds.has(String(img.node_id)),
      ).length
      const previewCount = (job.images || []).length - finalCount
      if (finalCount) {
        const extra =
          previewCount > 0 ? `；${previewCount} 张预览请在节点进度处查看` : ''
        setMessage(`生成完成，终图 ${finalCount} 张${extra}`)
      } else if (previewCount) {
        setMessage(`生成完成，预览 ${previewCount} 张（见节点下方「点击查看」）`)
      } else {
        setMessage(job.message || '未找到输出', true)
      }
      return
    }
  }

  async function pollJobOnce(promptId) {
    try {
      await pollJobUntilDone(promptId)
    } catch {
      /* retry */
    }
  }

  function startJobPolling(promptId) {
    stopPoll()
    if (isGenerateWsConnected()) {
      void pollJobOnce(promptId)
      return
    }
    pollActive = true
    pollBurstCount = 0
    void pollJobOnce(promptId).finally(() => {
      if (pollActive) scheduleJobPoll(promptId)
    })
  }

  function hasSessionPrompts() {
    return promptConfigHasContent(sessionPrompts)
  }

  function clearSessionPrompts() {
    applyPromptConfigTo(sessionPrompts, emptyBatchPromptConfig())
    sessionPromptPresetId.value = ''
    sessionPromptPresetName.value = ''
  }

  async function cancelWorkflow() {
    if (!job.promptId || !isGeneratingNow()) return
    try {
      await api.cancelJob(job.promptId)
      stopPoll()
      job.status = 'cancelled'
      job.statusText = statusLabel('cancelled')
      job.message = '已取消生成'
      job.currentNode = null
      job.progress = null
      setMessage('已取消当前生成任务')
    } catch (e) {
      setMessage(e.message, true)
    }
  }

  async function queueWorkflowCore() {
    if (!selectedId.value) return
    loading.value = true
    resetJob()
    stopPoll()
    try {
      const { getBatchStore } = await import('@/stores/useBatchStore.js')
      const { buildSeedOverridePatch, resolveSeedValue } = await import('@/lib/queueSeed.js')
      const batch = getBatchStore()
      const seedNodes = workflowTargets.value?.seed_nodes || []
      let promptSeed = null
      if (seedNodes.length) {
        promptSeed = resolveSeedValue(batch.form)
        applyOverridesPatch(buildSeedOverridePatch(seedNodes, promptSeed), { force: true })
      }
      const { buildFinalPromptOverrides } = await import(
        '@/lib/buildFinalPromptOverrides.js'
      )
      const finalPrompts = await buildFinalPromptOverrides(
        {
          selectedId: selectedId.value,
          overrides,
          sessionPrompts,
          styleEnabled: styleEnabled.value,
          promptEncode: promptEncode.value,
        },
        { promptSeed },
      )
      lastQueuedPrompts.value = {
        positive: finalPrompts.positive,
        negative: finalPrompts.negative,
        promptPicks: finalPrompts.promptPicks,
        at: Date.now(),
      }
      const trackNodes = filterPipelineForExecution(
        pipelineNodes.value,
        enabledPreviewNodeIds.value,
      )
      const res = await api.queueWorkflow(
        selectedId.value,
        finalPrompts.overrides,
        styleEnabled.value,
        null,
        promptSeed,
        [...(enabledPreviewNodeIds.value || [])],
        sessionLoraPayloadForQueue(),
        true,
      )
      Object.assign(job, {
        promptId: res.prompt_id,
        clientId: res.client_id,
        status: 'pending',
        statusText: statusLabel('pending'),
        message: '已提交，等待 ComfyUI 执行…',
        trackPipelineNodes: trackNodes,
        completedNodeIds: [],
      })
      applyQuotaFromApi(res)
      setMessage(`已提交，任务 ID: ${job.promptId}`)
      startJobPolling(job.promptId)
      return { promptId: job.promptId }
    } catch (e) {
      setMessage(e.message, true)
      job.status = 'failed'
      job.statusText = statusLabel('failed')
      throw e
    } finally {
      loading.value = false
    }
  }

  async function queueWorkflow() {
    if (!selectedId.value) return
    const { getGenerateQueueStore } = await import('@/stores/useGenerateQueueStore.js')
    const queue = getGenerateQueueStore()
    if (queue) {
      return queue.submit({
        type: 'single',
        label: '单张生成',
        run: queueWorkflowCore,
      })
    }
    return queueWorkflowCore()
  }

  async function deleteOutputs() {
    if (!job.promptId || !job.images.length) return false
    if (
      !(await getConfirmDialog().confirmDelete({
        message: '确定删除本次生成的图片？相关历史记录将一并移除。',
      }))
    )
      return false
    loading.value = true
    try {
      await api.deleteJobOutputs(job.promptId, job.images)
      job.images = []
      setMessage('已删除生成结果与历史记录')
      return true
    } catch (e) {
      setMessage(e.message, true)
      return false
    } finally {
      loading.value = false
    }
  }

  async function init() {
    await refreshHealth()
    await refreshFavorites()
    await loadWorkflowList()
  }

  onUnmounted(stopPoll)

  const store = reactive({
    health,
    workflows,
    selectedId,
    loading,
    message,
    error,
    state,
    workflowLoras,
    workflowTargets,
    workflowMeta,
    styleEnabled,
    isMasterWorkflow,
    overrides,
    modelLists,
    modelsLoading,
    job,
    sessionPrompts,
    sessionPromptPresetId,
    sessionPromptPresetName,
    promptEncode,
    pipelineNodes,
    previewNodes,
    enabledPreviewNodeIds,
    restoreEpoch,
    temporaryWorkflowActive,
    temporaryWorkflowHint,
    sessionLoraChain,
    lastQueuedPrompts,

    get groupedNodes() {
      const map = new Map()
      for (const node of state.nodes) {
        const g = node.group || '其他'
        if (!map.has(g)) map.set(g, [])
        map.get(g).push(node)
      }
      return [...map.entries()]
    },
    get healthOk() {
      return !!health.value?.ok
    },
    get isGenerating() {
      return isGeneratingNow()
    },
    get activeCheckpointName() {
      return getActiveCheckpointName()
    },
    get workflowLorasForUi() {
      return workflowLoras.value
    },
    get lorasForRun() {
      if (sessionLoraChain.value) {
        return buildSessionLorasForUi(
          sessionLoraChain.value,
          workflowLoras.value,
          overrides,
        )
      }
      return workflowLoras.value
    },
    get pipelineNodesForUi() {
      return pipelineNodes.value
    },
    get previewNodesForUi() {
      return previewNodes.value
    },
    get executionPipelineNodesForUi() {
      return filterPipelineForExecution(
        pipelineNodes.value,
        enabledPreviewNodeIds.value,
      )
    },
    get enabledPreviewNodeIdsForUi() {
      return enabledPreviewNodeIds.value
    },
    get progressPercent() {
      if (job.progress == null) return null
      return Math.min(100, Math.max(0, job.progress))
    },

    setMessage,
    groupHint,
    isModelSelectField,
    modelFolderForField,
    modelOptions,
    modelCatalogForFolder,
    modelSelectMissing,
    fieldValue,
    getActiveCheckpointName,
    updateField,
    refreshHealth,
    loadModelLists,
    loadWorkflow,
    loadWorkflowList,
    applyLoraSlotDefaults,
    setStyleEnabled,
    clearSessionPrompts,
    hasSessionPrompts,
    applyFavorite,
    applyWorkflowSnapshot,
    clearTemporaryWorkflow,
    saveWorkflow,
    addLoraChainSlot,
    removeLoraChainSlot,
    reorderLoraChain,
    initSessionLoraChain,
    resetSessionLoraChain,
    sessionAddLora,
    sessionRemoveLora,
    sessionMoveLora,
    sessionReorderLoras,
    sessionLoraPayloadForQueue,
    savePreviewNodeSelection,
    setEnabledPreviewNodeIds,
    previewNodeLabel,
    applyJobDetail,
    applyWsJobEvent,
    queueWorkflow,
    cancelWorkflow,
    deleteOutputs,
    resetJob,
    stopPoll,
    init,
  })

  provide(APP_STORE, store)
  return store
}

export function useAppStore() {
  const store = inject(APP_STORE)
  if (!store) throw new Error('useAppStore must be used within AppLayout')
  return store
}
