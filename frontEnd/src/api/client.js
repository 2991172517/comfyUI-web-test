async function request(path, options = {}) {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    const detail = data.detail
    if (typeof detail === 'string') {
      const err = new Error(detail)
      if (res.status === 409) err.conflict = data
      throw err
    }
    if (detail && typeof detail === 'object') {
      const err = new Error(detail.message || JSON.stringify(detail))
      if (res.status === 409) err.conflict = detail
      throw err
    }
    throw new Error(data.error || res.statusText)
  }
  return data
}

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms))
}

function wfPath(id) {
  return encodeURIComponent(id)
}

export const api = {
  health: () => request('/api/health'),
  listWorkflows: () => request('/api/workflows'),
  getWorkflowTemplate: () => request('/api/workflow-template'),
  listWorkflowVariants: () => request('/api/workflow-variants'),
  createWorkflowVariant: (body) =>
    request('/api/workflow-variants', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  updateWorkflowMeta: (workflowId, body) =>
    request(`/api/workflows/${wfPath(workflowId)}/meta`, {
      method: 'PUT',
      body: JSON.stringify(body),
    }),
  getBatchPromptConfig: () => request('/api/batch-prompt-config'),
  saveBatchPromptConfig: (body) =>
    request('/api/batch-prompt-config', {
      method: 'PUT',
      body: JSON.stringify(body),
    }),
  getPromptDefaults: () => request('/api/prompt-defaults'),
  savePromptDefaults: (body) =>
    request('/api/prompt-defaults', {
      method: 'PUT',
      body: JSON.stringify(body),
    }),
  getWorkflowEssentials: (id) => request(`/api/workflows/${wfPath(id)}/essentials`),
  saveWorkflowEssentials: (id, body) =>
    request(`/api/workflows/${wfPath(id)}/essentials`, {
      method: 'PUT',
      body: JSON.stringify(body),
    }),
  addLoraSlot: (id, body) =>
    request(`/api/workflows/${wfPath(id)}/lora-slots`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  removeLoraSlot: (id, nodeId) =>
    request(`/api/workflows/${wfPath(id)}/lora-slots/${encodeURIComponent(nodeId)}`, {
      method: 'DELETE',
    }),
  getWorkflow: (id, styleEnabled = null) => {
    const q =
      styleEnabled === null ? '' : `?style_enabled=${styleEnabled ? '1' : '0'}`
    return request(`/api/workflows/${wfPath(id)}${q}`)
  },
  saveWorkflow: (id, overrides) =>
    request(`/api/workflows/${wfPath(id)}`, {
      method: 'PUT',
      body: JSON.stringify({ overrides }),
    }),
  listPromptPresets: () => request('/api/prompt-presets'),
  getPromptPreset: (id) => request(`/api/prompt-presets/${encodeURIComponent(id)}`),
  createPromptPreset: (body) =>
    request('/api/prompt-presets', { method: 'POST', body: JSON.stringify(body) }),
  updatePromptPreset: (id, body) =>
    request(`/api/prompt-presets/${encodeURIComponent(id)}`, {
      method: 'PUT',
      body: JSON.stringify(body),
    }),
  deletePromptPreset: (id) =>
    request(`/api/prompt-presets/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  queueWorkflow: (id, overrides, styleEnabled = null, batchPrompts = null, promptSeed = null) =>
    request(`/api/workflows/${wfPath(id)}/queue`, {
      method: 'POST',
      body: JSON.stringify({
        overrides,
        ...(styleEnabled !== null ? { style_enabled: styleEnabled } : {}),
        ...(batchPrompts ? { batch_prompts: batchPrompts } : {}),
        ...(promptSeed != null ? { prompt_seed: promptSeed } : {}),
      }),
    }),
  getJob: (promptId) => request(`/api/jobs/${promptId}`),
  deleteJobOutputs: (promptId, images = null) =>
    request(`/api/jobs/${promptId}/outputs`, {
      method: 'DELETE',
      body: JSON.stringify(images ? { images } : {}),
    }),
  batchPreview: (workflowId, body) =>
    request(`/api/workflows/${wfPath(workflowId)}/batch/preview`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  startBatch: (workflowId, body) =>
    request(`/api/workflows/${wfPath(workflowId)}/batch`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  getGlobalReferenceGroups: () => request('/api/global-reference-groups'),
  saveGlobalReferenceGroups: (body) =>
    request('/api/global-reference-groups', {
      method: 'PUT',
      body: JSON.stringify(body),
    }),
  getModelFolderPaths: () => request('/api/models/folder-paths'),
  openModelFolder: (folder) =>
    request('/api/models/open-folder', {
      method: 'POST',
      body: JSON.stringify({ folder }),
    }),
  getGlobalPromptConfig: () => request('/api/global-prompt-config'),
  saveGlobalPromptConfig: (config) =>
    request('/api/global-prompt-config', {
      method: 'PUT',
      body: JSON.stringify(config),
    }),
  previewPromptMerge: (body) =>
    request('/api/prompts/merge-preview', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  listNodeCatalog: () => request('/api/node-catalog'),
  saveNodeCatalog: (body) =>
    request('/api/node-catalog', {
      method: 'PUT',
      body: JSON.stringify(body),
    }),
  getLoraModelDefaults: (name) =>
    request(`/api/node-catalog/lora-defaults?name=${encodeURIComponent(name)}`),
  getWorkflowNodeCatalog: (workflowId) =>
    request(`/api/workflows/${wfPath(workflowId)}/node-catalog`),
  saveWorkflowNodeCatalog: (workflowId, body) =>
    request(`/api/workflows/${wfPath(workflowId)}/node-catalog`, {
      method: 'PUT',
      body: JSON.stringify(body),
    }),
  listBatchTasks: () => request('/api/batch-tasks'),
  getBatchTask: (id) => request(`/api/batch-tasks/${encodeURIComponent(id)}`),
  getBatchTaskBatches: (id, limit = 50) =>
    request(`/api/batch-tasks/${encodeURIComponent(id)}/batches?limit=${limit}`),
  saveBatchTask: (body) =>
    request('/api/batch-tasks', { method: 'POST', body: JSON.stringify(body) }),
  deleteBatchTask: (id) =>
    request(`/api/batch-tasks/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  runBatchTasks: (taskIds) =>
    request('/api/batch-tasks/run', {
      method: 'POST',
      body: JSON.stringify({ task_ids: taskIds }),
    }),
  listCampaigns: (limit = 50) => request(`/api/campaigns?limit=${limit}`),
  getCampaign: (id) => request(`/api/campaigns/${encodeURIComponent(id)}`),
  createCampaign: (body) =>
    request('/api/campaigns', { method: 'POST', body: JSON.stringify(body) }),
  runCampaign: (id) =>
    request(`/api/campaigns/${encodeURIComponent(id)}/run`, { method: 'POST' }),
  cancelCampaign: (id) =>
    request(`/api/campaigns/${encodeURIComponent(id)}/cancel`, { method: 'POST' }),
  listHistory: (params = {}) => {
    const q = new URLSearchParams({ limit: String(params.limit ?? 80) })
    if (params.checkpoint) q.set('checkpoint', params.checkpoint)
    if (params.lora_name) q.set('lora_name', params.lora_name)
    if (params.lora_weight != null && params.lora_weight !== '')
      q.set('lora_weight', String(params.lora_weight))
    if (params.lora_node) q.set('lora_node', params.lora_node)
    if (params.type) q.set('type', params.type)
    return request(`/api/history?${q}`)
  },
  getHistoryFilterOptions: (limit = 200) =>
    request(`/api/history/filter-options?limit=${limit}`),
  getHistorySingle: (promptId) =>
    request(`/api/history/single/${encodeURIComponent(promptId)}`),
  getHistoryBatch: (batchId) => request(`/api/history/batch/${batchId}`),
  deleteHistorySingle: (promptId) =>
    request(`/api/history/single/${encodeURIComponent(promptId)}`, { method: 'DELETE' }),
  deleteHistoryBatch: (batchId) =>
    request(`/api/history/batch/${encodeURIComponent(batchId)}`, { method: 'DELETE' }),
  deleteHistoryBatchItems: (batchId, indices) =>
    request(`/api/history/batch/${encodeURIComponent(batchId)}/delete-items`, {
      method: 'POST',
      body: JSON.stringify({ indices }),
    }),
  listBatches: (limit = 50, taskId = null) => {
    const q = new URLSearchParams({ limit: String(limit) })
    if (taskId) q.set('task_id', taskId)
    return request(`/api/batches?${q}`)
  },
  getBatch: (batchId) => request(`/api/batches/${batchId}`),
  cancelBatch: (batchId) =>
    request(`/api/batches/${batchId}/cancel`, { method: 'POST' }),
  deleteBatch: (batchId) =>
    request(`/api/batches/${batchId}`, { method: 'DELETE' }),
  listModels: (folder, withPreviews = false) =>
    request(`/api/models/${folder}${withPreviews ? '?with_previews=1' : ''}`),
  getModelPreviews: (folder, name) =>
    request(`/api/models/${folder}/previews?name=${encodeURIComponent(name)}`),
  getModelSourceSettings: () => request('/api/model-sources/settings'),
  parseModelSourceUrl: (url) =>
    request(`/api/model-sources/parse?url=${encodeURIComponent(url)}`),
  getModelSourceVersion: (site, versionId, modelId) => {
    const params = new URLSearchParams()
    if (modelId) params.set('modelId', String(modelId))
    const q = params.toString() ? `?${params}` : ''
    return request(
      `/api/model-sources/version/${encodeURIComponent(site)}/${encodeURIComponent(versionId)}${q}`,
    )
  },
  startModelImport: (body) =>
    request('/api/model-sources/import', { method: 'POST', body: JSON.stringify(body) }),
  getModelImportJob: (jobId) =>
    request(`/api/model-sources/import/${encodeURIComponent(jobId)}`),
  /** 轮询直到完成，onProgress(job) 每次状态更新时调用 */
  async importModelSourceWithProgress(body, onProgress) {
    const { jobId } = await this.startModelImport(body)
    if (onProgress) {
      const initial = await this.getModelImportJob(jobId)
      onProgress(initial)
    }
    for (let i = 0; i < 7200; i++) {
      await sleep(500)
      const job = await this.getModelImportJob(jobId)
      if (onProgress) onProgress(job)
      if (job.status === 'completed') {
        return job.result || job
      }
      if (job.status === 'conflict') {
        const err = new Error(job.message || '模型已存在')
        err.conflict = job.result || job
        throw err
      }
      if (job.status === 'failed') {
        throw new Error(job.message || job.error || '导入失败')
      }
    }
    throw new Error('导入超时')
  },
  listFavorites: () => request('/api/favorites'),
  addFavorite: (body) =>
    request('/api/favorites', { method: 'POST', body: JSON.stringify(body) }),
  toggleFavorite: (body) =>
    request('/api/favorites/toggle', { method: 'POST', body: JSON.stringify(body) }),
  deleteFavorite: (id) => request(`/api/favorites/${id}`, { method: 'DELETE' }),
  sleep,
}

const STATUS_LABEL = {
  pending: '排队中',
  in_progress: '生成中',
  running: '批量进行中',
  finalizing: '收尾中',
  completed: '已完成',
  failed: '失败',
  cancelled: '已取消',
  cancelling: '取消中',
  deleted: '已删除',
  unknown: '未知',
  idle: '空闲',
}

export function statusLabel(status) {
  return STATUS_LABEL[status] || status
}

export const PARAM_HINTS = [
  {
    group: 'LoRA A / B 权重',
    affects: '画风、角色脸型、线条/上色风格。链中越靠后的 LoRA（如 B）对最终模型影响通常更明显。',
    fields: 'strength_model / strength_clip',
  },
  {
    group: '提示词',
    affects: '画面内容、人物动作、服装、背景描述；几乎决定「画什么」。',
    fields: 'CLIPTextEncode.text',
  },
  {
    group: '采样（步数 / CFG / 采样器）',
    affects: '细节锐度、对提示词服从度、噪点与收敛速度；不直接改画风 LoRA。',
    fields: 'KSampler: steps, cfg, sampler_name, scheduler, denoise',
  },
  {
    group: 'Seed',
    affects: '随机构图与细节噪声。固定 seed 便于只比较 LoRA；随机 seed 看泛化。',
    fields: 'KSampler.seed',
  },
  {
    group: '分辨率',
    affects: '构图比例与像素总量；过大显存暴涨，过小细节不足。',
    fields: 'EmptyLatentImage: width, height',
  },
  {
    group: 'Checkpoint',
    affects: '底层模型能力（SDXL/动漫/写实等），决定上限。',
    fields: 'CheckpointLoaderSimple.ckpt_name',
  },
]

/** 与 editable_config.json 分组名对应，用于单张参数卡片标题旁 */
export const GROUP_HINTS = {
  提示词: '决定画什么：人物、动作、服装、背景等语义内容。',
  采样: '控制细节、锐度、对提示词服从度与噪点；不直接替换 LoRA 画风。',
  尺寸: '宽高比与像素量；影响构图与显存占用。',
  模型: 'Checkpoint 决定底层画风与能力上限。',
  LoRA: '在 Checkpoint 上叠加风格/角色；strength 越大影响越强。',
  其他: '其他节点参数，请对照 ComfyUI 节点说明调整。',
}
