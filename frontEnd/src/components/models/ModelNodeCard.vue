<script setup>
import { computed, ref, toRef } from 'vue'
import { useIntersectionObserver } from '@vueuse/core'
import { FileText } from 'lucide-vue-next'
import Card from '@/components/ui/Card.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import CardTitle from '@/components/ui/CardTitle.vue'
import CardContent from '@/components/ui/CardContent.vue'
import Label from '@/components/ui/Label.vue'
import Input from '@/components/ui/Input.vue'
import Button from '@/components/ui/Button.vue'
import IconDeleteButton from '@/components/ui/IconDeleteButton.vue'
import ModelPreviewPanel from '@/components/models/ModelPreviewPanel.vue'
import ModelDescriptionEditModal from '@/components/models/ModelDescriptionEditModal.vue'
import CheckpointLoraCompatPanel from '@/components/models/CheckpointLoraCompatPanel.vue'
import { useModelAssets } from '@/composables/useModelAssets.js'
import { splitSourceUrl } from '@/lib/modelDescription.js'
import { isAdmin } from '@/composables/useAuth.js'

const props = defineProps({
  folder: { type: String, required: true },
  name: { type: String, required: true },
  kind: { type: String, default: 'checkpoint' },
  strengthModel: { type: Number, default: null },
  strengthClip: { type: Number, default: null },
  /** 模型管理页：显示删除与编辑说明 */
  manage: { type: Boolean, default: false },
  deleting: { type: Boolean, default: false },
  allLoras: { type: Array, default: () => [] },
  loraCatalog: { type: Array, default: () => [] },
  recommendedLoras: { type: Array, default: () => [] },
  notRecommendedLoras: { type: Array, default: () => [] },
})

const emit = defineEmits([
  'update:strengthModel',
  'update:strengthClip',
  'strengthBlur',
  'update:recommendedLoras',
  'update:notRecommendedLoras',
  'delete',
  'description-saved',
])

const editOpen = ref(false)
const cardRoot = ref(null)
const assetsVisible = ref(false)

useIntersectionObserver(
  cardRoot,
  ([entry]) => {
    if (entry?.isIntersecting) assetsVisible.value = true
  },
  { rootMargin: '240px 0px' },
)

const { previews, summary, loading, previewIndex, reload } = useModelAssets(
  props.folder,
  toRef(props, 'name'),
  { enabled: assetsVisible },
)

const summaryDisplay = computed(() => {
  if (!summary.value) return null
  const fromApi = summary.value.sourceUrl
  if (fromApi) {
    return {
      sourceUrl: fromApi,
      content: summary.value.content || '',
      truncated: summary.value.truncated,
    }
  }
  const split = splitSourceUrl(summary.value.content || '')
  return { ...split, truncated: summary.value.truncated }
})

const strengthModelLocal = computed({
  get: () => props.strengthModel,
  set: (v) => emit('update:strengthModel', v === '' || v == null ? null : Number(v)),
})

const strengthClipLocal = computed({
  get: () => props.strengthClip,
  set: (v) => emit('update:strengthClip', v === '' || v == null ? null : Number(v)),
})

function requestDelete() {
  if (props.deleting) return
  const label = props.folder === 'checkpoints' ? 'Checkpoint' : 'LoRA'
  const msg = `确定删除 ${label}「${props.name}」？\n将删除权重文件及同名资源文件夹（含说明与预览图），且不可恢复。`
  if (!confirm(msg)) return
  emit('delete', props.name)
}

function onDescriptionSaved() {
  reload()
  emit('description-saved', props.name)
}
</script>

<template>
  <div ref="cardRoot" class="min-h-0">
    <Card class="flex flex-col overflow-hidden transition-shadow h-full">
    <CardHeader class="pb-2 space-y-1">
      <div class="flex items-start gap-2">
        <div class="min-w-0 flex-1">
          <CardTitle class="text-sm font-mono leading-snug break-all" :title="name">
            {{ name }}
          </CardTitle>
          <p class="text-[10px] text-muted-foreground">
            {{ folder === 'checkpoints' ? 'Checkpoint' : 'LoRA' }}
          </p>
        </div>
        <div v-if="manage" class="flex shrink-0 gap-1">
          <Button
            variant="outline"
            size="sm"
            class="h-7 px-2 text-[10px] gap-1"
            :disabled="deleting"
            @click="editOpen = true"
          >
            <FileText class="h-3.5 w-3.5" />
            说明
          </Button>
          <IconDeleteButton
            v-if="isAdmin()"
            size="sm"
            title="删除模型"
            :disabled="deleting"
            @click="requestDelete"
          />
        </div>
      </div>
    </CardHeader>

    <CardContent class="flex-1 flex flex-col gap-3 pt-0">
      <ModelPreviewPanel
        v-if="assetsVisible && (previews.length || loading)"
        :folder="folder"
        :model-name="name"
        :previews="previews"
        :loading="loading"
        v-model:index="previewIndex"
        size="md"
      />
      <div
        v-else-if="!assetsVisible"
        class="h-40 rounded-md border border-dashed border-border flex items-center justify-center text-[10px] text-muted-foreground px-3 text-center"
      >
        预览待加载…
      </div>
      <div
        v-else
        class="h-40 rounded-md border border-dashed border-border flex items-center justify-center text-[10px] text-muted-foreground px-3 text-center"
      >
        暂无参考图
      </div>

      <div
        v-if="summaryDisplay"
        class="rounded-md border border-border bg-muted/20 p-2.5 max-h-32 overflow-auto text-xs text-muted-foreground leading-relaxed"
      >
        <p class="text-[10px] font-medium text-foreground mb-1">模型说明</p>
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
        <p v-if="summaryDisplay.truncated" class="text-[10px] mt-1 opacity-70">（已截断）</p>
      </div>
      <p v-else-if="assetsVisible && !loading" class="text-[10px] text-muted-foreground">
        <template v-if="manage">暂无说明，点击「说明」编辑并保存。</template>
        <template v-else>
          在 models/{{ folder }}/ 下建立与主文件名同名的文件夹，放入预览图与 模型说明.txt。
        </template>
      </p>

      <CheckpointLoraCompatPanel
        v-if="manage && kind === 'checkpoint'"
        :checkpoint-name="name"
        :all-loras="allLoras"
        :lora-catalog="loraCatalog"
        :recommended="recommendedLoras"
        :not-recommended="notRecommendedLoras"
        @update:recommended="emit('update:recommendedLoras', $event)"
        @update:not-recommended="emit('update:notRecommendedLoras', $event)"
      />

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

    <ModelDescriptionEditModal
      v-if="manage"
      v-model:open="editOpen"
      :folder="folder"
      :name="name"
      :initial-summary="summaryDisplay"
      @saved="onDescriptionSaved"
    />
  </Card>
  </div>
</template>
