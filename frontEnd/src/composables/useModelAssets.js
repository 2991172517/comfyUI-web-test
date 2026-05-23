import { ref, unref, watch } from 'vue'
import { api } from '@/api/client.js'

/** 加载模型参考图 + 同名目录下首个 txt 说明；enabled 为 false 时不请求（配合可见性懒加载） */
export function useModelAssets(folder, modelName, options = {}) {
  const enabled = options.enabled ?? ref(true)
  const previews = ref([])
  const summary = ref(null)
  const loading = ref(false)
  const previewIndex = ref(0)

  async function load() {
    const f = unref(folder)
    const name = unref(modelName)
    if (!f || !name) {
      previews.value = []
      summary.value = null
      return
    }
    loading.value = true
    try {
      const res = await api.getModelPreviews(f, name)
      previews.value = res.previews || []
      summary.value = res.summary || null
      if (previewIndex.value >= previews.value.length) previewIndex.value = 0
    } catch (e) {
      previews.value = []
      summary.value = null
      if (import.meta.env.DEV) {
        console.warn('[useModelAssets] load failed', f, name, e)
      }
    } finally {
      loading.value = false
    }
  }

  watch(
    () => [unref(folder), unref(modelName), unref(enabled)],
    ([f, name, en]) => {
      if (!en || !f || !name) return
      load()
    },
    { immediate: true },
  )

  return { previews, summary, loading, previewIndex, reload: load }
}
