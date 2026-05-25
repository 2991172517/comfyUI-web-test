<script setup>
import { computed, ref } from 'vue'
import { Loader2, Sparkles } from 'lucide-vue-next'
import ModelVisualPicker from '@/components/models/ModelVisualPicker.vue'
import { useAppStore } from '@/stores/useAppStore.js'
import { useInpaintStore } from '@/stores/useInpaintStore.js'
import MaskPaintEditor from '@/components/inpaint/MaskPaintEditor.vue'
import ImageBeforeAfterCompare from '@/components/media/ImageBeforeAfterCompare.vue'
import Button from '@/components/ui/Button.vue'
import Card from '@/components/ui/Card.vue'
import CardContent from '@/components/ui/CardContent.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import CardTitle from '@/components/ui/CardTitle.vue'
import Input from '@/components/ui/Input.vue'
import Label from '@/components/ui/Label.vue'
import Textarea from '@/components/ui/Textarea.vue'
import Progress from '@/components/ui/Progress.vue'
import Badge from '@/components/ui/Badge.vue'
import ImageMagnifierPreview from '@/components/media/ImageMagnifierPreview.vue'
import { INPAINT_RTX_UI_ENABLED } from '@/lib/inpaintWorkflow.js'
import { useImageDownload } from '@/composables/useImageDownload.js'
import { hasSingleQuotaLeft } from '@/composables/useAuth.js'

const props = defineProps({
  healthOk: { type: Boolean, default: true },
})

const app = useAppStore()
const inpaint = useInpaintStore()
const editorRef = ref(null)
const { saveOne } = useImageDownload()

const runDisabled = computed(
  () => inpaint.loading || inpaint.isGenerating || !props.healthOk,
)

const canCompare = computed(
  () =>
    inpaint.showCompare &&
    inpaint.compareBeforeUrl &&
    inpaint.compareAfterUrl,
)

function resolveWorkflowId() {
  return app.selectedId || inpaint.workflowId
}

function onGenerate() {
  inpaint.submitInpaint(editorRef.value, { workflowId: resolveWorkflowId() })
}
</script>

<template>
  <div class="space-y-4">
    <p
      v-if="inpaint.error"
      class="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive"
    >
      {{ inpaint.error }}
    </p>
    <p
      v-else-if="inpaint.message"
      class="rounded-md border border-border bg-muted/30 px-3 py-2 text-sm text-muted-foreground"
    >
      {{ inpaint.message }}
    </p>

    <div class="grid gap-4 lg:grid-cols-[1fr_22rem]">
      <Card>
        <CardHeader class="pb-2">
          <CardTitle class="text-sm">原图与蒙版</CardTitle>
        </CardHeader>
        <CardContent>
          <MaskPaintEditor ref="editorRef" :disabled="runDisabled" />
        </CardContent>
      </Card>

      <div class="space-y-4">
        <Card>
          <CardHeader class="pb-2">
            <CardTitle class="text-sm">Checkpoint 模型</CardTitle>
          </CardHeader>
          <CardContent>
            <ModelVisualPicker
              v-model="inpaint.checkpoint"
              folder="checkpoints"
              label="底模"
              :options="app.modelLists.checkpoints"
              :catalog="app.modelLists.checkpointCatalog"
              :loading="app.modelsLoading"
              :disabled="runDisabled"
            />
            <p
              v-if="inpaint.bootstrapSourceWorkflowId"
              class="mt-2 text-[10px] text-muted-foreground leading-relaxed"
            >
              参数来源：{{ inpaint.bootstrapSourceWorkflowId }}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader class="pb-2">
            <CardTitle class="text-sm">提示词与采样</CardTitle>
          </CardHeader>
          <CardContent class="space-y-3">
            <div class="space-y-1">
              <Label class="text-xs">正向提示词</Label>
              <Textarea
                v-model="inpaint.positive"
                rows="4"
                class="text-xs"
                :disabled="runDisabled"
              />
            </div>
            <div class="space-y-1">
              <Label class="text-xs">负向提示词</Label>
              <Textarea
                v-model="inpaint.negative"
                rows="3"
                class="text-xs"
                :disabled="runDisabled"
              />
            </div>
            <div class="grid grid-cols-2 gap-2">
              <div class="space-y-1">
                <Label class="text-xs">Seed</Label>
                <div class="flex gap-1">
                  <Input
                    v-model.number="inpaint.seed"
                    type="number"
                    class="h-8 text-xs"
                    :disabled="runDisabled"
                  />
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    class="shrink-0 px-2"
                    :disabled="runDisabled"
                    @click="inpaint.randomizeSeed()"
                  >
                    随机
                  </Button>
                </div>
              </div>
              <div class="space-y-1">
                <Label class="text-xs">重绘强度 denoise</Label>
                <Input
                  v-model.number="inpaint.denoise"
                  type="number"
                  step="0.05"
                  min="0.1"
                  max="1"
                  class="h-8 text-xs"
                  :disabled="runDisabled"
                />
              </div>
              <div class="space-y-1">
                <Label class="text-xs">步数</Label>
                <Input
                  v-model.number="inpaint.steps"
                  type="number"
                  min="1"
                  max="60"
                  class="h-8 text-xs"
                  :disabled="runDisabled"
                />
              </div>
              <div class="space-y-1">
                <Label class="text-xs">CFG</Label>
                <Input
                  v-model.number="inpaint.cfg"
                  type="number"
                  step="0.5"
                  min="1"
                  max="20"
                  class="h-8 text-xs"
                  :disabled="runDisabled"
                />
              </div>
            </div>

            <label
              v-if="INPAINT_RTX_UI_ENABLED"
              class="flex cursor-pointer items-start gap-2 rounded-md border border-border/70 bg-muted/20 px-3 py-2"
            >
              <input
                v-model="inpaint.rtxUpscale"
                type="checkbox"
                class="mt-0.5 rounded border-border"
                :disabled="runDisabled"
              />
              <span class="text-xs leading-relaxed text-muted-foreground">
                <span class="font-medium text-foreground">完成后 RTX 放大 1.5×</span>
                （需 RTX 显卡与插件）
              </span>
            </label>
          </CardContent>
        </Card>

        <Button
          type="button"
          class="w-full"
          size="lg"
          :disabled="runDisabled || !hasSingleQuotaLeft()"
          @click="inpaint.isGenerating ? inpaint.cancelJob() : onGenerate()"
        >
          <Loader2 v-if="inpaint.loading" class="mr-2 h-4 w-4 animate-spin" />
          <Sparkles v-else class="mr-2 h-4 w-4" />
          {{
            inpaint.isGenerating
              ? '取消生成'
              : inpaint.loading
                ? '上传并提交…'
                : '开始局部重绘'
          }}
        </Button>
      </div>
    </div>

    <Card v-if="canCompare">
      <CardHeader class="pb-2">
        <CardTitle class="text-sm">重绘前后对比</CardTitle>
      </CardHeader>
      <CardContent>
        <ImageBeforeAfterCompare
          :before-src="inpaint.compareBeforeUrl"
          :after-src="inpaint.compareAfterUrl"
        />
      </CardContent>
    </Card>

    <Card v-if="inpaint.job.status !== 'idle'">
      <CardHeader class="flex flex-row items-center gap-2 pb-2">
        <CardTitle class="text-sm">任务状态</CardTitle>
        <Badge variant="secondary">{{ inpaint.job.statusText }}</Badge>
      </CardHeader>
      <CardContent class="space-y-3">
        <p v-if="inpaint.job.promptId" class="text-xs text-muted-foreground">
          任务 ID: {{ inpaint.job.promptId }}
        </p>
        <p v-if="inpaint.job.message" class="text-sm text-muted-foreground">
          {{ inpaint.job.message }}
        </p>
        <Progress
          v-if="inpaint.progressPercent != null && inpaint.isGenerating"
          :value="inpaint.progressPercent"
        />
        <div
          v-if="inpaint.job.images.length && !canCompare"
          class="grid gap-3 sm:grid-cols-2"
        >
          <figure
            v-for="img in inpaint.job.images"
            :key="img.id || img.filename"
            class="overflow-hidden rounded-lg border border-border"
          >
            <div class="aspect-square bg-muted/30">
              <ImageMagnifierPreview fill :src="img.url" :alt="img.filename" />
            </div>
            <figcaption class="flex items-center justify-between p-2 text-xs">
              <span class="truncate text-muted-foreground">{{ img.filename }}</span>
              <Button variant="ghost" size="sm" @click="saveOne(img)">保存</Button>
            </figcaption>
          </figure>
        </div>
        <div
          v-else-if="inpaint.job.images.length && canCompare"
          class="flex flex-wrap items-center gap-2"
        >
          <Button variant="outline" size="sm" @click="saveOne(inpaint.job.images[0])">
            保存结果图
          </Button>
        </div>
      </CardContent>
    </Card>
  </div>
</template>
