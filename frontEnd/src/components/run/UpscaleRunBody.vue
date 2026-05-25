<script setup>
import { computed, onUnmounted, ref } from 'vue'
import { Loader2, Sparkles, Upload } from 'lucide-vue-next'
import { useAppStore } from '@/stores/useAppStore.js'
import { useUpscaleStore } from '@/stores/useUpscaleStore.js'
import ImageBeforeAfterCompare from '@/components/media/ImageBeforeAfterCompare.vue'
import Button from '@/components/ui/Button.vue'
import Card from '@/components/ui/Card.vue'
import CardContent from '@/components/ui/CardContent.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import CardTitle from '@/components/ui/CardTitle.vue'
import Input from '@/components/ui/Input.vue'
import Label from '@/components/ui/Label.vue'
import Progress from '@/components/ui/Progress.vue'
import Badge from '@/components/ui/Badge.vue'
import ImageMagnifierPreview from '@/components/media/ImageMagnifierPreview.vue'
import { UPSCALE_WORKFLOW_ID } from '@/lib/upscaleWorkflow.js'
import { useImageDownload } from '@/composables/useImageDownload.js'
import { hasSingleQuotaLeft } from '@/composables/useAuth.js'

const props = defineProps({
  healthOk: { type: Boolean, default: true },
})

const app = useAppStore()
const upscale = useUpscaleStore()
const sourceFile = ref(null)
const previewUrl = ref('')
const imageMeta = ref({ w: 0, h: 0 })
const fileInput = ref(null)
const { saveOne } = useImageDownload()

const runDisabled = computed(
  () => upscale.loading || upscale.isGenerating || !props.healthOk,
)

const outputHint = computed(() => {
  const { w, h } = imageMeta.value
  const s = Number(upscale.scale)
  if (!w || !h || !Number.isFinite(s)) return ''
  return `预计约 ${Math.round(w * s)}×${Math.round(h * s)}（倍数 ${s}）`
})

const canCompare = computed(
  () =>
    upscale.showCompare &&
    upscale.compareBeforeUrl &&
    upscale.compareAfterUrl,
)

function revokePreview() {
  if (previewUrl.value) {
    URL.revokeObjectURL(previewUrl.value)
    previewUrl.value = ''
  }
}

function pickFile() {
  if (runDisabled.value) return
  fileInput.value?.click()
}

async function onFileChange(ev) {
  const file = ev.target.files?.[0]
  ev.target.value = ''
  if (!file) return
  if (!file.type.startsWith('image/')) {
    upscale.setMessage('请选择图片文件', true)
    return
  }
  revokePreview()
  sourceFile.value = file
  previewUrl.value = URL.createObjectURL(file)
  const bmp = await createImageBitmap(file)
  imageMeta.value = { w: bmp.width, h: bmp.height }
  bmp.close?.()
  upscale.setMessage('')
}

function resolveWorkflowId() {
  return app.selectedId || UPSCALE_WORKFLOW_ID
}

function onSubmit() {
  upscale.submitUpscale(sourceFile.value, { workflowId: resolveWorkflowId() })
}

onUnmounted(revokePreview)
</script>

<template>
  <div class="space-y-4">
    <p
      v-if="upscale.error"
      class="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive"
    >
      {{ upscale.error }}
    </p>
    <p
      v-else-if="upscale.message"
      class="rounded-md border border-border bg-muted/30 px-3 py-2 text-sm text-muted-foreground"
    >
      {{ upscale.message }}
    </p>

    <div class="grid gap-4 md:grid-cols-[1fr_16rem]">
      <Card>
        <CardHeader class="pb-2">
          <CardTitle class="text-sm">原图</CardTitle>
        </CardHeader>
        <CardContent class="space-y-3">
          <input
            ref="fileInput"
            type="file"
            accept="image/png,image/jpeg,image/webp"
            class="hidden"
            @change="onFileChange"
          />
          <Button
            type="button"
            variant="outline"
            size="sm"
            :disabled="runDisabled"
            @click="pickFile"
          >
            <Upload class="mr-1 h-3.5 w-3.5" />
            选择图片
          </Button>
          <div
            class="flex min-h-[240px] items-center justify-center rounded-md border border-border/60 bg-muted/20 p-2"
          >
            <img
              v-if="previewUrl"
              :src="previewUrl"
              alt="preview"
              class="max-h-[min(60vh,640px)] max-w-full object-contain"
            />
            <p v-else class="text-sm text-muted-foreground text-center px-4">
              支持 PNG / JPEG / WebP
            </p>
          </div>
          <p
            v-if="imageMeta.w"
            class="text-[11px] text-muted-foreground tabular-nums"
          >
            当前 {{ imageMeta.w }}×{{ imageMeta.h }}
            <span v-if="outputHint"> → {{ outputHint }}</span>
          </p>
        </CardContent>
      </Card>

      <div class="space-y-4">
        <Card>
          <CardHeader class="pb-2">
            <CardTitle class="text-sm">参数</CardTitle>
          </CardHeader>
          <CardContent class="space-y-3">
            <div class="space-y-1">
              <Label class="text-xs">放大倍数</Label>
              <Input
                v-model.number="upscale.scale"
                type="number"
                step="0.1"
                min="1.05"
                max="4"
                class="h-9"
                :disabled="runDisabled"
              />
            </div>
            <p class="text-[11px] text-muted-foreground leading-relaxed">
              默认 1.5。原图已很大时建议降低倍数。
            </p>
          </CardContent>
        </Card>

        <Button
          type="button"
          class="w-full"
          size="lg"
          :disabled="runDisabled || !sourceFile || !hasSingleQuotaLeft()"
          @click="upscale.isGenerating ? upscale.cancelJob() : onSubmit()"
        >
          <Loader2 v-if="upscale.loading" class="mr-2 h-4 w-4 animate-spin" />
          <Sparkles v-else class="mr-2 h-4 w-4" />
          {{
            upscale.isGenerating
              ? '取消'
              : upscale.loading
                ? '上传并提交…'
                : '开始放大'
          }}
        </Button>
      </div>
    </div>

    <Card v-if="canCompare">
      <CardHeader class="pb-2">
        <CardTitle class="text-sm">放大前后对比</CardTitle>
      </CardHeader>
      <CardContent>
        <ImageBeforeAfterCompare
          :before-src="upscale.compareBeforeUrl"
          :after-src="upscale.compareAfterUrl"
          before-label="原图"
          after-label="放大后"
        />
      </CardContent>
    </Card>

    <Card v-if="upscale.job.status !== 'idle'">
      <CardHeader class="flex flex-row items-center gap-2 pb-2">
        <CardTitle class="text-sm">任务状态</CardTitle>
        <Badge variant="secondary">{{ upscale.job.statusText }}</Badge>
      </CardHeader>
      <CardContent class="space-y-3">
        <p v-if="upscale.job.promptId" class="text-xs text-muted-foreground">
          任务 ID: {{ upscale.job.promptId }}
        </p>
        <Progress
          v-if="upscale.progressPercent != null && upscale.isGenerating"
          :value="upscale.progressPercent"
        />
        <div v-if="upscale.job.images.length && !canCompare" class="max-w-md">
          <ImageMagnifierPreview
            :src="upscale.job.images[0].url"
            :alt="upscale.job.images[0].filename"
            class="rounded-lg border border-border"
          />
          <Button variant="outline" size="sm" class="mt-2" @click="saveOne(upscale.job.images[0])">
            保存
          </Button>
        </div>
        <Button
          v-else-if="upscale.job.images.length && canCompare"
          variant="outline"
          size="sm"
          @click="saveOne(upscale.job.images[0])"
        >
          保存放大图
        </Button>
      </CardContent>
    </Card>
  </div>
</template>
