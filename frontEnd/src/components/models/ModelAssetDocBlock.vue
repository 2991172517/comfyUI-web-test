<script setup>
import { computed, toRef } from 'vue'
import { useModelAssets } from '@/composables/useModelAssets.js'
import ModelPreviewPanel from '@/components/models/ModelPreviewPanel.vue'
import { splitSourceUrl } from '@/lib/modelDescription.js'

const props = defineProps({
  folder: { type: String, required: true },
  modelName: { type: String, default: '' },
  previewSize: { type: String, default: 'sm' },
})

const { previews, summary, loading, previewIndex } = useModelAssets(
  props.folder,
  toRef(props, 'modelName'),
)

const hasAssets = computed(() => previews.value.length > 0 || !!summary.value)

const summaryDisplay = computed(() => {
  if (!summary.value?.content && !summary.value?.sourceUrl) return { sourceUrl: null, content: '' }
  const fromApi = summary.value.sourceUrl
  if (fromApi) {
    return { sourceUrl: fromApi, content: summary.value.content || '' }
  }
  return splitSourceUrl(summary.value.content || '')
})
</script>

<template>
  <div v-if="modelName" class="mt-3">
    <div
      v-if="hasAssets"
      :class="[
        'grid gap-3 items-start',
        previews.length && summary ? 'md:grid-cols-[minmax(160px,220px)_1fr]' : 'max-w-2xl',
      ]"
    >
      <ModelPreviewPanel
        v-if="previews.length || loading"
        :folder="folder"
        :model-name="modelName"
        :previews="previews"
        :loading="loading"
        v-model:index="previewIndex"
        :size="previewSize"
      />
      <div
        v-if="summary"
        class="rounded-md border border-border bg-muted/20 p-2.5 max-h-36 overflow-auto text-xs text-muted-foreground leading-relaxed"
      >
        <p class="text-[10px] font-medium text-foreground mb-1">{{ summary.filename }}</p>
        <a
          v-if="summaryDisplay.sourceUrl"
          :href="summaryDisplay.sourceUrl"
          target="_blank"
          rel="noopener noreferrer"
          class="text-primary hover:underline block mb-2 break-all font-medium"
        >
          访问链接：{{ summaryDisplay.sourceUrl }}
        </a>
        <pre class="whitespace-pre-wrap break-words">{{ summaryDisplay.content }}</pre>
        <p v-if="summary.truncated" class="text-[10px] mt-1 opacity-70">（内容已截断）</p>
      </div>
    </div>
    <p v-else class="text-[10px] text-muted-foreground leading-relaxed">
      未找到参考图或说明。请在
      <code class="text-[10px]">ComfyUI/models/{{ folder }}/</code>
      下为模型建立与主文件名同名的文件夹，放入预览图与 txt 说明（导入模型时会自动写入）。
    </p>
  </div>
</template>
