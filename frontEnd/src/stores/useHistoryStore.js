import { inject, provide, reactive, ref } from 'vue'
import { api } from '@/api/client.js'

const HISTORY_STORE = Symbol('historyStore')

export function createHistoryStore() {
  const records = ref([])
  const loading = ref(false)
  const filterOptions = ref({ checkpoints: [], loras: [] })
  const filters = reactive({
    checkpoint: '',
    lora_name: '',
    lora_weight: '',
    lora_node: '',
    type: '',
  })
  const selected = ref(null)
  const batchDetail = ref(null)
  const singleDetail = ref(null)
  const detailLoading = ref(false)

  async function loadFilterOptions() {
    try {
      const res = await api.getHistoryFilterOptions()
      filterOptions.value = {
        checkpoints: res.checkpoints || [],
        loras: res.loras || [],
      }
    } catch {
      filterOptions.value = { checkpoints: [], loras: [] }
    }
  }

  async function refresh() {
    loading.value = true
    try {
      const params = { limit: 80 }
      if (filters.checkpoint) params.checkpoint = filters.checkpoint
      if (filters.lora_name) params.lora_name = filters.lora_name
      if (filters.lora_weight !== '' && filters.lora_weight != null)
        params.lora_weight = Number(filters.lora_weight)
      if (filters.lora_node) params.lora_node = filters.lora_node
      if (filters.type) params.type = filters.type
      const res = await api.listHistory(params)
      records.value = res.records || []
    } finally {
      loading.value = false
    }
  }

  function resetFilters() {
    filters.checkpoint = ''
    filters.lora_name = ''
    filters.lora_weight = ''
    filters.lora_node = ''
    filters.type = ''
    refresh()
  }

  function loraWeightsForName(name) {
    const row = filterOptions.value.loras?.find((l) => l.lora_name === name)
    return row?.weights || []
  }

  async function selectRecord(rec) {
    selected.value = rec
    batchDetail.value = null
    singleDetail.value = null
    if (!rec) return
    detailLoading.value = true
    try {
      if (rec.type === 'batch') {
        batchDetail.value = await api.getHistoryBatch(rec.batch_id || rec.id)
      } else {
        singleDetail.value = await api.getHistorySingle(rec.prompt_id || rec.id)
      }
    } finally {
      detailLoading.value = false
    }
  }

  function clearSelection() {
    selected.value = null
    batchDetail.value = null
    singleDetail.value = null
  }

  async function deleteSingle(promptId) {
    await api.deleteHistorySingle(promptId)
    if (selected.value?.prompt_id === promptId || selected.value?.id === promptId) {
      clearSelection()
    }
    await refresh()
  }

  async function deleteBatch(batchId) {
    await api.deleteHistoryBatch(batchId)
    if (selected.value?.batch_id === batchId || selected.value?.id === batchId) {
      clearSelection()
    }
    await refresh()
  }

  async function deleteBatchItems(batchId, indices) {
    const res = await api.deleteHistoryBatchItems(batchId, indices)
    if (selected.value?.batch_id === batchId || selected.value?.id === batchId) {
      const rec = selected.value
      await selectRecord(rec)
    }
    await refresh()
    return res
  }

  const store = reactive({
    records,
    loading,
    filterOptions,
    filters,
    selected,
    batchDetail,
    singleDetail,
    detailLoading,
    refresh,
    loadFilterOptions,
    resetFilters,
    selectRecord,
    clearSelection,
    loraWeightsForName,
    deleteSingle,
    deleteBatch,
    deleteBatchItems,
  })

  provide(HISTORY_STORE, store)
  return store
}

export function useHistoryStore() {
  const store = inject(HISTORY_STORE)
  if (!store) throw new Error('useHistoryStore must be used within AppLayout')
  return store
}
