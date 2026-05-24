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
import {
  resolveRestoreWorkflowId,
  WORKFLOW_TEMPLATE_ID,
} from '@/lib/workflowRestore.js'
import { getConfirmDialog } from '@/composables/useConfirmDialog.js'

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
  /** 每次从历史快照恢复后递增，用于强制刷新 LoRA 等表单控件 */
  const restoreEpoch = ref(0)

  const job = reactive({
    promptId: '',
    clientId: '',
    status: 'idle',
    statusText: '',
    currentNode: null,
    progress: null,
    message: '',
    images: [],
  })

  let pollTimer = null
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
    })
  }

  function stopPoll() {
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
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
        workflows.value.find((w) => w.is_master) ||
        workflows.value.find((w) => w.id === 'First_api') ||
        workflows.value[0]
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
      isMasterWorkflow.value = !!res.is_master
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
        ensureOverride(String(sn.node_id), 'seed', snap.seed)
      }
      return
    }
    const fallback = workflowTargets.value?.seed_node_id
    if (fallback) ensureOverride(String(fallback), 'seed', snap.seed)
  }

  async function applyWorkflowSnapshot(snap) {
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
    if (usedFallback && missingId) {
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

  async function saveWorkflow() {
    if (!selectedId.value) return
    if (isMasterWorkflow.value) {
      setMessage('母版工作流只读，请在工作流页另存为子工作流后再保存', true)
      return
    }
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

  function applyJobDetail(detail) {
    job.status = detail.status || 'unknown'
    job.statusText = statusLabel(job.status)
    job.message = detail.message || ''
    job.currentNode = detail.current_node ?? null
    job.progress = detail.progress ?? null
    job.images = detail.images || []
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
      if (job.images.length) {
        setMessage(`生成完成，共 ${job.images.length} 张`)
      } else {
        setMessage(job.message || '未找到输出', true)
      }
      return
    }
    if (detail.status === 'finalizing') {
      setTimeout(() => pollJobOnce(promptId), 500)
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
    pollJobOnce(promptId)
    pollTimer = setInterval(() => pollJobOnce(promptId), 1000)
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

  async function queueWorkflow() {
    if (!selectedId.value || isGeneratingNow()) return
    loading.value = true
    resetJob()
    stopPoll()
    try {
      const batchPrompts = hasSessionPrompts()
        ? serializePromptConfig(sessionPrompts)
        : null
      const seed =
        batchPrompts && workflowTargets.value?.seed_nodes?.[0]?.seed != null
          ? Number(workflowTargets.value.seed_nodes[0].seed)
          : null
      const res = await api.queueWorkflow(
        selectedId.value,
        { ...overrides },
        styleEnabled.value,
        batchPrompts,
        seed,
      )
      Object.assign(job, {
        promptId: res.prompt_id,
        clientId: res.client_id,
        status: 'pending',
        statusText: statusLabel('pending'),
        message: '已提交，等待 ComfyUI 执行…',
      })
      applyQuotaFromApi(res)
      setMessage(`已提交，任务 ID: ${job.promptId}`)
      startJobPolling(job.promptId)
    } catch (e) {
      setMessage(e.message, true)
      job.status = 'failed'
      job.statusText = statusLabel('failed')
    } finally {
      loading.value = false
    }
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
    restoreEpoch,

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
    saveWorkflow,
    applyJobDetail,
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
