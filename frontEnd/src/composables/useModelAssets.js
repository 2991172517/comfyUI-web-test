import { ref, unref, watch } from 'vue'
import { api } from '@/api/client.js'

/** 加载模型参考图 + 同名目录下首个 txt 说明 */
export function useModelAssets(folder, modelName) {
  const previews = ref([])
  const summary = ref(null)
  const loading = ref(false)
  const previewIndex = ref(0)

  async function load() {
    const name = unref(modelName)
    if (!name) {
      previews.value = []
      summary.value = null
      return
    }
    loading.value = true
    try {
      const res = await api.getModelPreviews(folder, name)
      previews.value = res.previews || []
      summary.value = res.summary || null
      if (previewIndex.value >= previews.value.length) previewIndex.value = 0
    } catch {
      previews.value = []
      summary.value = null
    } finally {
      loading.value = false
    }
  }

  watch(
    () => [folder, unref(modelName)],
    load,
    { immediate: true },
  )

  return { previews, summary, loading, previewIndex, reload: load }
}
