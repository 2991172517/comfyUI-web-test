import { ref, unref, watch } from 'vue'
import { api } from '@/api/client.js'

/**
 * 根据当前 Checkpoint 加载 LoRA 适配状态（推荐 / 不推荐 / 中性）。
 * @param {import('vue').MaybeRefOrGetter<string>} checkpointSource
 */
export function useCheckpointLoraCompat(checkpointSource) {
  const compatMap = ref({})
  const recommended = ref([])
  const notRecommended = ref([])
  const loading = ref(false)

  async function refresh() {
    const ckpt = String(unref(checkpointSource) || '').trim()
    if (!ckpt) {
      compatMap.value = {}
      recommended.value = []
      notRecommended.value = []
      return
    }
    loading.value = true
    try {
      const res = await api.getCheckpointLoraCompat(ckpt)
      compatMap.value = res.map || {}
      recommended.value = res.recommended || []
      notRecommended.value = res.not_recommended || []
    } catch {
      compatMap.value = {}
      recommended.value = []
      notRecommended.value = []
    } finally {
      loading.value = false
    }
  }

  watch(() => unref(checkpointSource), refresh, { immediate: true })

  function statusFor(loraName) {
    return compatMap.value[loraName] || 'neutral'
  }

  function hintFor(loraName) {
    const s = statusFor(loraName)
    if (s === 'not_recommended') {
      return '不推荐用于当前 Checkpoint，仍可选择'
    }
    if (s === 'recommended') {
      return '推荐用于当前 Checkpoint'
    }
    return ''
  }

  return {
    compatMap,
    recommended,
    notRecommended,
    loading,
    refresh,
    statusFor,
    hintFor,
  }
}
