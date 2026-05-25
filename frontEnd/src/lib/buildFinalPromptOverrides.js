import { api } from '@/api/client.js'
import {
  promptConfigHasContent,
  serializePromptConfig,
} from '@/composables/usePromptConfig.js'

/** @returns {{ positive: string, negative: string }} */
export function resolveEncodeNodeIds(app) {
  const enc = app.promptEncode || {}
  return {
    positive: String(enc.positive?.node_id || '3'),
    negative: String(enc.negative?.node_id || '4'),
  }
}

/**
 * 与后端入队相同的合并逻辑（/api/prompts/merge-preview），写出 CLIP 节点最终 text。
 * @param {object} app useAppStore
 * @param {{ overrides?: Record<string, object>, promptSeed?: number | null, styleEnabled?: boolean | null }} [opts]
 */
export async function buildFinalPromptOverrides(app, opts = {}) {
  const workflowId = app.selectedId
  if (!workflowId) {
    throw new Error('未选择工作流')
  }

  const baseOverrides = opts.overrides ?? { ...app.overrides }
  const session = app.sessionPrompts
  const batchPrompts = promptConfigHasContent(session)
    ? serializePromptConfig(session)
    : null

  const res = await api.previewPromptMerge({
    workflow_id: workflowId,
    overrides: baseOverrides,
    style_enabled: opts.styleEnabled ?? app.styleEnabled,
    batch_prompts: batchPrompts,
    prompt_seed: opts.promptSeed ?? null,
    prompt_global_priority: !!session?.merge?.random_before_workflow,
  })

  const ids = resolveEncodeNodeIds(app)
  const out = { ...baseOverrides }
  const positive = String(res.positive ?? '')
  const negative = String(res.negative ?? '')
  out[ids.positive] = { ...(out[ids.positive] || {}), text: positive }
  out[ids.negative] = { ...(out[ids.negative] || {}), text: negative }

  return {
    overrides: out,
    positive,
    negative,
    promptPicks: res.prompt_picks ?? [],
    segments: res.segments ?? null,
    mergeDebug: res.merge_debug ?? null,
    encodeNodeIds: ids,
  }
}
