import { api } from '@/api/client.js'
import { serializePromptConfig } from '@/composables/usePromptConfig.js'

/**
 * @param {'overwrite' | 'create'} mode
 * @param {object} promptConfig reactive fixed + random_groups
 * @param {string} [presetId]
 */
export async function savePromptPresetExport(
  mode,
  promptConfig,
  { presetId, name, description = '', workflowPositive = '', workflowNegative = '' } = {},
) {
  const serialized = serializePromptConfig(promptConfig)
  const body = {
    name: (name || '未命名预设').trim(),
    description: (description || '').trim(),
    ...serialized,
    positive: String(workflowPositive || serialized.positive || '').trim(),
    negative: String(workflowNegative || serialized.negative || '').trim(),
  }
  if (mode === 'overwrite' && presetId) {
    const res = await api.updatePromptPreset(presetId, body)
    return { mode: 'overwrite', preset: res.preset }
  }
  const res = await api.createPromptPreset(body)
  return { mode: 'create', preset: res.preset }
}
