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
  /** @type {import('vue').Ref<Set<string>>} */
  const selectedKeys = ref(new Set())
  const bulkSelectMode = ref(false)
  const bulkDeleting = ref(false)

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

  function clearDetailSelection() {
    selected.value = null
    batchDetail.value = null
    singleDetail.value = null
  }

  function removeRecordFromList(id, type) {
    records.value = records.value.filter((r) => {
      if (type === 'batch') return r.type !== 'batch' || (r.batch_id || r.id) !== id
      return r.type === 'batch' || (r.prompt_id !== id && r.id !== id)
    })
  }

  function patchBatchRecordInList(batchId, patch) {
    records.value = records.value.map((r) => {
      if (r.type !== 'batch' || (r.batch_id || r.id) !== batchId) return r
      return { ...r, ...patch }
    })
  }

  async function deleteSingle(promptId) {
    await api.deleteHistorySingle(promptId)
    if (selected.value?.prompt_id === promptId || selected.value?.id === promptId) {
      clearDetailSelection()
    }
    removeRecordFromList(promptId, 'single')
  }

  async function deleteBatch(batchId) {
    await api.deleteHistoryBatch(batchId)
    if (selected.value?.batch_id === batchId || selected.value?.id === batchId) {
      clearDetailSelection()
    }
    removeRecordFromList(batchId, 'batch')
  }

  async function deleteBatchItems(batchId, indices) {
    const res = await api.deleteHistoryBatchItems(batchId, indices)
    const idxSet = new Set(indices.map((i) => Number(i)))
    const batchFullyGone =
      res.remaining === 0 ||
      (res.removed == null && res.remaining == null)

    if (batchFullyGone) {
      if (selected.value?.batch_id === batchId || selected.value?.id === batchId) {
        clearDetailSelection()
      }
      removeRecordFromList(batchId, 'batch')
      return res
    }

    if (
      batchDetail.value &&
      (batchDetail.value.batch_id === batchId || batchDetail.value.id === batchId)
    ) {
      const items = (batchDetail.value.items || []).filter(
        (it) => !idxSet.has(Number(it.index)),
      )
      const plan = batchDetail.value.plan || {}
      const grid = {
        ...(plan.grid || batchDetail.value.grid || {}),
        total: items.length,
      }
      const completed = items.filter(
        (it) => it.status === 'completed' && (it.images?.length),
      ).length
      batchDetail.value = {
        ...batchDetail.value,
        items,
        completed,
        total: items.length,
        plan: { ...plan, grid },
        grid,
      }
      if (selected.value?.type === 'batch') {
        selected.value = {
          ...selected.value,
          completed,
          total: items.length,
        }
      }
    }

    const removed = res.removed ?? indices.length
    const total = res.remaining
    const listRec = records.value.find(
      (r) => r.type === 'batch' && (r.batch_id || r.id) === batchId,
    )
    if (listRec) {
      patchBatchRecordInList(batchId, {
        total,
        completed: Math.max(0, (listRec.completed ?? 0) - removed),
      })
    }

    return res
  }

  function recordKey(rec) {
    if (!rec) return ''
    if (rec.type === 'batch') return `batch:${rec.batch_id || rec.id}`
    return `single:${rec.prompt_id || rec.id}`
  }

  function isSelected(rec) {
    return selectedKeys.value.has(recordKey(rec))
  }

  function toggleSelect(rec) {
    const key = recordKey(rec)
    if (!key) return
    const next = new Set(selectedKeys.value)
    if (next.has(key)) next.delete(key)
    else next.add(key)
    selectedKeys.value = next
  }

  function selectAllVisible() {
    selectedKeys.value = new Set(records.value.map((r) => recordKey(r)).filter(Boolean))
  }

  function clearBulkSelection() {
    selectedKeys.value = new Set()
  }

  function toggleBulkSelectMode() {
    bulkSelectMode.value = !bulkSelectMode.value
    if (!bulkSelectMode.value) clearBulkSelection()
  }

  function exitBulkSelectMode() {
    bulkSelectMode.value = false
    clearBulkSelection()
  }

  async function deleteSelected() {
    const singles = []
    const batches = []
    for (const rec of records.value) {
      if (!isSelected(rec)) continue
      if (rec.type === 'batch') batches.push(rec.batch_id || rec.id)
      else singles.push(rec.prompt_id || rec.id)
    }
    if (!singles.length && !batches.length) {
      return { ok: false, message: '请先勾选要删除的记录' }
    }
    bulkDeleting.value = true
    try {
      const res = await api.deleteHistoryBulk({ singles, batches })
      const n = (res.deleted_singles?.length || 0) + (res.deleted_batches?.length || 0)
      const failN = res.failed?.length || 0
      if (selected.value && isSelected(selected.value)) {
        clearDetailSelection()
      }
      clearBulkSelection()
      bulkSelectMode.value = false
      await refresh()
      return {
        ok: true,
        message:
          failN > 0
            ? `已删除 ${n} 条，${failN} 条失败`
            : `已删除 ${n} 条记录`,
        result: res,
      }
    } finally {
      bulkDeleting.value = false
    }
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
    selectedKeys,
    bulkSelectMode,
    bulkDeleting,
    refresh,
    loadFilterOptions,
    resetFilters,
    selectRecord,
    clearDetailSelection,
    clearSelection: clearDetailSelection,
    loraWeightsForName,
    deleteSingle,
    deleteBatch,
    deleteBatchItems,
    recordKey,
    isSelected,
    toggleSelect,
    selectAllVisible,
    clearBulkSelection,
    toggleBulkSelectMode,
    exitBulkSelectMode,
    deleteSelected,
  })

  provide(HISTORY_STORE, store)
  return store
}

export function useHistoryStore() {
  const store = inject(HISTORY_STORE)
  if (!store) throw new Error('useHistoryStore must be used within AppLayout')
  return store
}
