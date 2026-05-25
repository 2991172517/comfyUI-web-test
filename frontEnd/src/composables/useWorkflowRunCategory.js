import { computed } from 'vue'
import { useAppStore } from '@/stores/useAppStore.js'
import {
  categoryLabel,
  inferCategoryFromWorkflowId,
  normalizeCategory,
} from '@/lib/workflowCategories.js'

/** 当前选中工作流的运行分类（文生图 / 局部重绘 / 高清放大） */
export function useWorkflowRunCategory() {
  const app = useAppStore()

  const category = computed(() => {
    const metaCat = app.workflowMeta?.category
    if (metaCat) return normalizeCategory(metaCat)
    const entry = app.workflows.find((w) => w.id === app.selectedId)
    if (entry?.category) return normalizeCategory(entry.category)
    return inferCategoryFromWorkflowId(app.selectedId)
  })

  const isInpaint = computed(() => category.value === 'inpaint')
  const isUpscale = computed(() => category.value === 'upscale')
  const isGenerateLike = computed(
    () => category.value === 'generate' || category.value === 'other',
  )

  return {
    category,
    categoryLabel: computed(() => categoryLabel(category.value)),
    isInpaint,
    isUpscale,
    isGenerateLike,
  }
}
