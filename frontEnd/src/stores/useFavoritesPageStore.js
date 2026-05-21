import { computed, inject, onUnmounted, provide, reactive, ref } from 'vue'
import { api } from '@/api/client.js'
import { buildFavoriteFilterOptions, filterFavorites } from '@/lib/favoriteMeta.js'

const FAVORITES_PAGE_STORE = Symbol('favoritesPageStore')

export function createFavoritesPageStore() {
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

  const store = reactive({
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

  provide(FAVORITES_PAGE_STORE, store)
  onUnmounted(() => {
    /* page-scoped */
  })

  return store
}

export function useFavoritesPageStore() {
  const store = inject(FAVORITES_PAGE_STORE, null)
  if (!store) {
    throw new Error('useFavoritesPageStore() 需在 FavoritesView 内使用 createFavoritesPageStore()')
  }
  return store
}
