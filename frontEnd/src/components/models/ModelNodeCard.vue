<script setup>
import { computed, ref, toRef } from 'vue'
import { useIntersectionObserver } from '@vueuse/core'
import Card from '@/components/ui/Card.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import CardTitle from '@/components/ui/CardTitle.vue'
import CardContent from '@/components/ui/CardContent.vue'
import Label from '@/components/ui/Label.vue'
import Input from '@/components/ui/Input.vue'
import IconDeleteButton from '@/components/ui/IconDeleteButton.vue'
import ModelPreviewPanel from '@/components/models/ModelPreviewPanel.vue'
import ModelDescriptionEditModal from '@/components/models/ModelDescriptionEditModal.vue'
import CheckpointLoraCompatPanel from '@/components/models/CheckpointLoraCompatPanel.vue'
import { api } from '@/api/client.js'
import { useModelAssets } from '@/composables/useModelAssets.js'
import { useAppStore } from '@/stores/useAppStore.js'
import { splitSourceUrl } from '@/lib/modelDescription.js'
import { modelDisplayTitle } from '@/lib/modelDisplay.js'
import ModelDescriptionText from '@/components/models/ModelDescriptionText.vue'
import { isAdmin } from '@/composables/useAuth.js'
import { useConfirmDialog } from '@/composables/useConfirmDialog.js'

const { confirmDelete } = useConfirmDialog()
const app = useAppStore()
const uploadingPreview = ref(false)
const deletingPreview = ref(false)

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
  'preview-updated',
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

async function requestDelete() {
  if (props.deleting) return
  const label = props.folder === 'checkpoints' ? 'Checkpoint' : 'LoRA'
  const msg = `确定删除 ${label}「${props.name}」？将删除权重文件及同名资源文件夹（含说明与预览图），且不可恢复。`
  if (!(await confirmDelete({ message: msg }))) return
  emit('delete', props.name)
}

function onDescriptionSaved() {
  reload()
  emit('description-saved', props.name)
}

async function onUploadPreviews(files) {
  if (!files?.length || uploadingPreview.value) return
  uploadingPreview.value = true
  try {
    const res = await api.uploadModelPreviews(props.folder, props.name, files)
    await reload()
    await app.loadModelLists().catch(() => {})
    const n = res.saved?.length ?? files.length
    app.setMessage(`已上传 ${n} 张参考图`)
    emit('preview-updated', props.name)
  } catch (e) {
    app.setMessage(e.message || '上传失败', true)
  } finally {
    uploadingPreview.value = false
  }
}

async function onDeletePreview(preview) {
  if (!preview?.relative_path || deletingPreview.value || uploadingPreview.value) return
  const msg = `确定删除参考图「${preview.filename}」？此操作不可恢复。`
  if (!(await confirmDelete({ message: msg }))) return
  deletingPreview.value = true
  try {
    await api.removeModelPreview(props.folder, props.name, preview.relative_path)
    await reload()
    await app.loadModelLists().catch(() => {})
    app.setMessage('已删除参考图')
    emit('preview-updated', props.name)
  } catch (e) {
    app.setMessage(e.message || '删除失败', true)
  } finally {
    deletingPreview.value = false
  }
}

function openDescriptionEditor(ev) {
  if (!props.manage) return
  if (ev?.target?.closest('a')) return
  editOpen.value = true
}

const displayTitle = computed(() => modelDisplayTitle(props.name))
</script>

<template>
  <div ref="cardRoot" class="min-h-0">
    <Card class="flex flex-col overflow-hidden transition-shadow h-full">
    <CardHeader class="pb-2 space-y-1 min-h-[4.5rem]">
      <div class="flex items-start gap-2">
        <div class="min-w-0 flex-1">
          <CardTitle class="text-sm leading-snug line-clamp-2 min-h-[2.5rem]" :title="name">
            {{ displayTitle }}
          </CardTitle>
          <p class="text-[10px] text-muted-foreground font-mono truncate mt-0.5" :title="name">
            {{ name }}
          </p>
        </div>
        <div v-if="manage" class="flex shrink-0 gap-1">
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
        v-if="assetsVisible"
        :folder="folder"
        :model-name="name"
        :previews="previews"
        :loading="loading"
        :editable="manage"
        :uploading="uploadingPreview"
        :deleting="deletingPreview"
        v-model:index="previewIndex"
        size="md"
        @upload="onUploadPreviews"
        @delete="onDeletePreview"
      />
      <div
        v-else
        class="h-40 rounded-md border border-dashed border-border flex items-center justify-center text-[10px] text-muted-foreground px-3 text-center"
      >
        预览待加载…
      </div>

      <div
        v-if="summaryDisplay"
        :class="[
          'h-28 shrink-0 overflow-auto rounded-md border border-border bg-muted/20 p-2.5 text-xs text-muted-foreground leading-relaxed',
          manage
            ? 'cursor-pointer transition-colors hover:border-primary/35 hover:bg-muted/35'
            : '',
        ]"
        @click="openDescriptionEditor"
      >
        <p class="text-[10px] font-medium text-foreground mb-1">模型说明</p>
        <a
          v-if="summaryDisplay.sourceUrl"
          :href="summaryDisplay.sourceUrl"
          target="_blank"
          rel="noopener noreferrer"
          class="text-primary hover:underline block mb-2 break-all"
          @click.stop
        >
          {{ summaryDisplay.sourceUrl }}
        </a>
        <ModelDescriptionText :text="summaryDisplay.content" />
        <p v-if="summaryDisplay.truncated" class="text-[10px] mt-1 opacity-70">（已截断）</p>
      </div>
      <div
        v-else-if="assetsVisible && !loading"
        :class="[
          'h-28 shrink-0 flex items-center rounded-md border border-dashed border-border px-3 text-[10px] text-muted-foreground',
          manage
            ? 'cursor-pointer transition-colors hover:border-primary/35 hover:bg-muted/20'
            : '',
        ]"
        @click="openDescriptionEditor"
      >
        <template v-if="manage">暂无说明，点击此处编辑并保存。</template>
        <template v-else>
          在 models/{{ folder }}/ 下建立与主文件名同名的文件夹，放入预览图与 模型说明.txt。
        </template>
      </div>

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
