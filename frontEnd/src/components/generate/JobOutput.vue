<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { staggerReveal } from '@/lib/gsap/motion.js'
import { useAppStore } from '@/stores/useAppStore.js'
import { useHistoryStore } from '@/stores/useHistoryStore.js'
import { buildSingleFavoritePayload } from '@/utils/favoritePayload.js'
import { useImageDownload } from '@/composables/useImageDownload.js'
import { useFavorites } from '@/composables/useFavorites.js'
import Card from '@/components/ui/Card.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import CardTitle from '@/components/ui/CardTitle.vue'
import CardContent from '@/components/ui/CardContent.vue'
import Button from '@/components/ui/Button.vue'
import Badge from '@/components/ui/Badge.vue'
import FavoriteStar from '@/components/FavoriteStar.vue'
import InpaintJumpButton from '@/components/inpaint/InpaintJumpButton.vue'
import { buildInpaintPayloadFromGenerate } from '@/lib/inpaintBootstrap.js'
import ImageLightbox from '@/components/ImageLightbox.vue'
import ImageMagnifierPreview from '@/components/media/ImageMagnifierPreview.vue'
import Progress from '@/components/ui/Progress.vue'
import { isAdmin } from '@/composables/useAuth.js'
import { useGenerateStageLog } from '@/composables/useGenerateStageLog.js'
import PipelineFlowStrip from '@/components/workflow/PipelineFlowStrip.vue'
import LastQueuedPromptsPanel from '@/components/generate/LastQueuedPromptsPanel.vue'

const store = useAppStore()
const history = useHistoryStore()
const { prepActive, stageLogs } = useGenerateStageLog()
const imageLightboxRef = ref(null)
const resultsGridRef = ref(null)
let lastImageCount = 0

const showPipelineProgress = computed(
  () =>
    store.job.trackPipelineNodes?.length > 0 &&
    ['pending', 'in_progress', 'finalizing', 'completed'].includes(store.job.status),
)

const trackNodes = computed(() => store.job.trackPipelineNodes || [])

/** 本次进度条中的预览节点 ID */
const previewNodeIdSet = computed(
  () => new Set(trackNodes.value.filter((n) => n.is_preview).map((n) => String(n.node_id))),
)

/** 按节点分组的所有输出（含预览） */
const jobImagesByNode = computed(() => {
  /** @type {Record<string, typeof store.job.images>} */
  const map = {}
  for (const img of store.job.images || []) {
    const id = String(img.node_id)
    if (!map[id]) map[id] = []
    map[id].push(img)
  }
  return map
})

/** 生成结果区：仅终图等非预览节点输出 */
const jobFinalImages = computed(() =>
  (store.job.images || []).filter((img) => !previewNodeIdSet.value.has(String(img.node_id))),
)

watch(
  () => jobFinalImages.value.length,
  async (n) => {
    if (n <= lastImageCount) {
      lastImageCount = n
      return
    }
    lastImageCount = n
    await nextTick()
    const grid = resultsGridRef.value
    if (!grid) return
    const figures = grid.querySelectorAll('[data-stagger-item]')
    if (figures.length) staggerReveal(figures)
  },
)

const { refreshFavorites } = useFavorites()
const { saveOne, saveAll } = useImageDownload()

watch(
  () => store.job.status,
  (st) => {
    if (st === 'completed') history.refresh()
  },
)

function singleFavoritePayload(img) {
  return buildSingleFavoritePayload(
    store.selectedId,
    img,
    store.overrides,
    store.job.promptId,
  )
}

function openImageList(images, startIndex = 0) {
  const list = images.map((img) => ({
    url: img.url,
    title: store.previewNodeLabel(img.node_id) || img.filename,
  }))
  imageLightboxRef.value?.open(list, startIndex)
}

function openFinalImagePreview(index) {
  openImageList(jobFinalImages.value, index)
}

function onViewNodeImages({ images }) {
  if (images?.length) openImageList(images, 0)
}

function downloadImage(img) {
  saveOne(img)
}

function downloadAllFinalImages() {
  saveAll(jobFinalImages.value)
}

async function deleteJobOutputs() {
  const ok = await store.deleteOutputs()
  if (ok) await history.refresh()
}

function onFavoriteToggled() {
  refreshFavorites()
}
</script>

<template>
  <Card
    v-if="store.job.status !== 'idle' || prepActive"
    data-generate-status="single"
    class="mb-6 scroll-mt-20"
  >
    <CardHeader class="flex flex-row flex-wrap items-center gap-3 space-y-0 pb-2">
      <CardTitle class="text-base">生成状态</CardTitle>
      <Button
        v-if="store.isGenerating"
        variant="secondary"
        size="sm"
        class="ml-auto shrink-0"
        @click="store.cancelWorkflow"
      >
        取消生成
      </Button>
      <Badge
        :variant="
          store.job.status === 'completed'
            ? 'success'
            : ['failed', 'cancelled'].includes(store.job.status)
              ? 'destructive'
              : 'secondary'
        "
      >
        {{ store.job.statusText }}
      </Badge>
    </CardHeader>
    <CardContent class="space-y-3">
      <div
        v-if="stageLogs.length"
        class="rounded-md border border-border/70 bg-muted/25 px-3 py-2.5"
      >
        <p class="mb-2 text-xs font-medium text-muted-foreground">准备日志</p>
        <ul class="max-h-36 space-y-1 overflow-y-auto">
          <li
            v-for="line in stageLogs"
            :key="line.id"
            class="flex gap-2 text-xs leading-relaxed"
          >
            <span class="shrink-0 tabular-nums text-muted-foreground">{{ line.time }}</span>
            <span class="text-foreground">{{ line.text }}</span>
          </li>
        </ul>
      </div>

      <LastQueuedPromptsPanel />

      <p v-if="store.job.promptId" class="text-sm text-muted-foreground">
        任务 ID: {{ store.job.promptId }}
      </p>
      <p v-if="store.job.message" class="text-sm text-muted-foreground">{{ store.job.message }}</p>

      <div
        v-if="showPipelineProgress"
        class="rounded-lg border border-border bg-muted/20 px-3 py-3 space-y-2"
      >
        <p class="text-xs font-medium text-muted-foreground">
          节点进度 · 预览图请在对应节点下方「点击查看」
        </p>
        <PipelineFlowStrip
          mode="progress"
          :nodes="trackNodes"
          :current-node-id="store.job.currentNode"
          :completed-node-ids="store.job.completedNodeIds"
          :job-status="store.job.status"
          :images-by-node="jobImagesByNode"
          @view-node-images="onViewNodeImages"
        />
      </div>

      <div
        v-if="store.progressPercent != null && store.isGenerating"
        class="relative space-y-1"
      >
        <Progress :value="store.progressPercent" />
        <span class="block text-right text-xs text-muted-foreground tabular-nums">
          {{ store.progressPercent }}%
        </span>
      </div>
      <p v-else-if="store.isGenerating" class="flex items-center gap-2 text-sm text-muted-foreground">
        <span
          class="inline-block h-4 w-4 animate-spin rounded-full border-2 border-muted-foreground border-t-primary"
        />
        正在执行工作流…
      </p>

      <div v-if="jobFinalImages.length" class="space-y-3 border-t border-border pt-4">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <h4 class="text-sm font-medium">生成结果（{{ jobFinalImages.length }}）</h4>
          <div class="flex gap-2">
            <Button variant="outline" size="sm" @click="downloadAllFinalImages">全部保存</Button>
            <Button
              v-if="isAdmin()"
              variant="destructive"
              size="sm"
              @click="deleteJobOutputs"
            >
              删除服务器图片
            </Button>
          </div>
        </div>
        <div
          ref="resultsGridRef"
          class="grid gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4"
        >
          <figure
            v-for="(img, idx) in jobFinalImages"
            :key="img.id"
            data-stagger-item
            class="overflow-visible rounded-lg border border-border bg-background"
          >
            <div class="overflow-hidden rounded-t-lg">
              <div class="relative aspect-square w-full bg-muted/30">
                <ImageMagnifierPreview
                  fill
                  :src="img.url"
                  :alt="img.filename"
                  @click="openFinalImagePreview(idx)"
                >
                  <template #overlay>
                    <div class="absolute right-2 top-2 z-10 flex gap-1">
                      <InpaintJumpButton
                        size="sm"
                        :get-payload="() => buildInpaintPayloadFromGenerate(store, img)"
                      />
                      <FavoriteStar
                        :payload="singleFavoritePayload(img)"
                        size="small"
                        @toggled="onFavoriteToggled"
                      />
                    </div>
                  </template>
                </ImageMagnifierPreview>
              </div>
            </div>
            <figcaption class="flex flex-col gap-1 p-2 text-xs">
              <span
                class="truncate font-medium text-foreground"
                :title="store.previewNodeLabel(img.node_id)"
              >
                {{ store.previewNodeLabel(img.node_id) }}
              </span>
              <span class="flex items-center justify-between gap-2">
                <span class="truncate text-muted-foreground" :title="img.filename">{{
                  img.filename
                }}</span>
                <Button variant="ghost" size="sm" @click="downloadImage(img)">保存</Button>
              </span>
            </figcaption>
          </figure>
        </div>
      </div>
    </CardContent>
  </Card>
  <ImageLightbox ref="imageLightboxRef" />
</template>
