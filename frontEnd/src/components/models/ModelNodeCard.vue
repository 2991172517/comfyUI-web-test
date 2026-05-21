<script setup>
import { computed, toRef } from 'vue'
import Card from '@/components/ui/Card.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import CardTitle from '@/components/ui/CardTitle.vue'
import CardContent from '@/components/ui/CardContent.vue'
import Label from '@/components/ui/Label.vue'
import Input from '@/components/ui/Input.vue'
import ModelPreviewPanel from '@/components/models/ModelPreviewPanel.vue'
import { useModelAssets } from '@/composables/useModelAssets.js'
import { splitSourceUrl } from '@/lib/modelDescription.js'

const props = defineProps({
  folder: { type: String, required: true },
  name: { type: String, required: true },
  kind: { type: String, default: 'checkpoint' },
  strengthModel: { type: Number, default: null },
  strengthClip: { type: Number, default: null },
})

const emit = defineEmits(['update:strengthModel', 'update:strengthClip', 'strengthBlur'])

const { previews, summary, loading, previewIndex } = useModelAssets(
  props.folder,
  toRef(props, 'name'),
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

const strengthModelLocal = computed({
  get: () => props.strengthModel,
  set: (v) => emit('update:strengthModel', v === '' || v == null ? null : Number(v)),
})

const strengthClipLocal = computed({
  get: () => props.strengthClip,
  set: (v) => emit('update:strengthClip', v === '' || v == null ? null : Number(v)),
})
</script>

<template>
  <Card class="flex flex-col overflow-hidden transition-shadow">
    <CardHeader class="pb-2 space-y-1">
      <CardTitle class="text-sm font-mono leading-snug break-all" :title="name">
        {{ name }}
      </CardTitle>
      <p class="text-[10px] text-muted-foreground">
        {{ folder === 'checkpoints' ? 'Checkpoint' : 'LoRA' }}
      </p>
    </CardHeader>

    <CardContent class="flex-1 flex flex-col gap-3 pt-0">
      <ModelPreviewPanel
        v-if="previews.length || loading"
        :folder="folder"
        :model-name="name"
        :previews="previews"
        :loading="loading"
        v-model:index="previewIndex"
        size="md"
      />
      <div
        v-else
        class="h-40 rounded-md border border-dashed border-border flex items-center justify-center text-[10px] text-muted-foreground px-3 text-center"
      >
        暂无参考图
      </div>

      <div
        v-if="summary"
        class="rounded-md border border-border bg-muted/20 p-2.5 max-h-32 overflow-auto text-xs text-muted-foreground leading-relaxed"
      >
        <p class="text-[10px] font-medium text-foreground mb-1">参考说明</p>
        <a
          v-if="summaryDisplay.sourceUrl"
          :href="summaryDisplay.sourceUrl"
          target="_blank"
          rel="noopener noreferrer"
          class="text-primary hover:underline block mb-2 break-all"
        >
          {{ summaryDisplay.sourceUrl }}
        </a>
        <pre class="whitespace-pre-wrap break-words">{{ summaryDisplay.content }}</pre>
        <p v-if="summary.truncated" class="text-[10px] mt-1 opacity-70">（已截断）</p>
      </div>
      <p v-else-if="!hasAssets && !loading" class="text-[10px] text-muted-foreground">
        在 <code class="text-[10px]">models/{{ folder }}/</code> 下建立与主文件名同名的文件夹，放入预览图与 txt 说明。
      </p>

      <div v-if="kind === 'lora'" class="grid grid-cols-2 gap-2 mt-auto pt-1">
        <div class="space-y-1">
          <Label class="text-[10px]">strength_model</Label>
          <Input
            v-model.number="strengthModelLocal"
            type="number"
            step="0.05"
            class="h-8 text-xs"
            placeholder="—"
            @blur="emit('strengthBlur')"
          />
        </div>
        <div class="space-y-1">
          <Label class="text-[10px]">strength_clip</Label>
          <Input
            v-model.number="strengthClipLocal"
            type="number"
            step="0.05"
            class="h-8 text-xs"
            placeholder="—"
            @blur="emit('strengthBlur')"
          />
        </div>
      </div>
    </CardContent>
  </Card>
</template>
