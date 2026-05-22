import { computed, reactive, ref } from 'vue'
import { api } from '@/api/client.js'
import { buildFavoriteFilterOptions, filterFavorites } from '@/lib/favoriteMeta.js'

/** 收藏页全局 store（单例，避免 RouterView 与 provide/inject 层级问题） */
let favoritesPageStore = null

export function createFavoritesPageStore() {
  if (favoritesPageStore) return favoritesPageStore

  const allItems = ref([])
  const loading = ref(false)
  const selected = ref(null)

  const filters = reactive({
    checkpoint: '',
    lora_name: '',
    lora_weight: '',
    workflow_id: '',
  })

  const filterOptions = computed(() => buildFavoriteFilterOptions(allItems.value))

  const records = computed(() => filterFavorites(allItems.value, filters))

  function loraWeightsForName(name) {
    const row = filterOptions.value.loras.find((l) => l.lora_name === name)
    return row?.weights || []
  }

  function resetFilters() {
    filters.checkpoint = ''
    filters.lora_name = ''
    filters.lora_weight = ''
    filters.workflow_id = ''
  }

  async function refresh() {
    loading.value = true
    try {
      const res = await api.listFavorites()
      allItems.value = res.favorites || []
    } finally {
      loading.value = false
    }
  }

  function selectFavorite(fav) {
    selected.value = fav
  }

  function clearSelection() {
    selected.value = null
  }

  function removeFromList(id) {
    allItems.value = allItems.value.filter((f) => f.id !== id)
    if (selected.value?.id === id) selected.value = null
  }

  favoritesPageStore = reactive({
    allItems,
    loading,
    selected,
    filters,
    filterOptions,
    records,
    loraWeightsForName,
    resetFilters,
    refresh,
    selectFavorite,
    clearSelection,
    removeFromList,
  })

  return favoritesPageStore
}

export function useFavoritesPageStore() {
  return createFavoritesPageStore()
}
