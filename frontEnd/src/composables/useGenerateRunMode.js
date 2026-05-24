import { computed } from 'vue'
import { useBatchStore } from '@/stores/useBatchStore.js'
import { allowsBatch } from '@/composables/useAuth.js'

/** 统一生成页：根据张数 / 扫参决定走单张还是批量 API */
export function useGenerateRunMode() {
  const batch = useBatchStore()

  const usesBatchApi = computed(
    () => allowsBatch() && (batch.hasSweepEnabled || batch.plannedTotal > 1),
  )

  const showBatchResults = computed(() => {
    if (!allowsBatch()) return false
    if (batch.isBatchRunning) return true
    if (!batch.batchId) return false
    if (['idle', 'deleted'].includes(batch.status)) return false
    return batch.total > 1 || batch.hasSweepEnabled
  })

  const showSingleOutput = computed(() => !showBatchResults.value)

  const generateLabel = computed(() => {
    const n = batch.plannedTotal
    if (n <= 1) return '生成'
    return `生成 ${n} 张`
  })

  return {
    usesBatchApi,
    showBatchResults,
    showSingleOutput,
    generateLabel,
    plannedTotal: computed(() => batch.plannedTotal),
  }
}
