<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { animateBatchCellImage, resetBatchCellSeen } from '@/lib/gsap/batchCell.js'
import { useRouter } from 'vue-router'
import { useAppStore } from '@/stores/useAppStore.js'
import { useBatchStore } from '@/stores/useBatchStore.js'
import { buildRegenerateRestoreRoute } from '@/lib/regenerateFromImage.js'
import {
  historyBatchCellImageHeight,
  historyBatchMatrixGridStyle,
  historyCardImgClass,
  historyCardIsNatural,
  historyCardLayout,
  historyCardThumbBoxStyle,
} from '@/composables/useHistoryCardLayout.js'
import Card from '@/components/ui/Card.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import CardTitle from '@/components/ui/CardTitle.vue'
import CardDescription from '@/components/ui/CardDescription.vue'
import CardContent from '@/components/ui/CardContent.vue'
import Button from '@/components/ui/Button.vue'
import Badge from '@/components/ui/Badge.vue'
import MediaCardLayoutControls from '@/components/shared/MediaCardLayoutControls.vue'
import FavoriteStar from '@/components/FavoriteStar.vue'
import InpaintJumpButton from '@/components/inpaint/InpaintJumpButton.vue'
import { buildInpaintPayloadFromBatchCell } from '@/lib/inpaintBootstrap.js'
import ImageLightbox from '@/components/ImageLightbox.vue'
import ImageMagnifierPreview from '@/components/media/ImageMagnifierPreview.vue'
import { cn } from '@/lib/utils'

const props = defineProps({
  showSizeControls: { type: Boolean, default: false },
  showMeta: { type: Boolean, default: true },
})

const emit = defineEmits(['favorite-toggled'])

const app = useAppStore()
const batch = useBatchStore()
const router = useRouter()
const lightboxRef = ref(null)

async function regenerateFromCell(cell) {
  try {
    const route = await buildRegenerateRestoreRoute({
      cell,
      runConfig: batch.runConfig.value,
      batchId: batch.batch.batchId,
      cellIndex: cell.index,
    })
    if (!route) {
      app.setMessage('缺少工作流信息，无法恢复', true)
      return
    }
    if (route.message) app.setMessage(route.message)
    router.push({ path: '/generate', query: route.query })
  } catch (e) {
    app.setMessage(e.message || '无法从图片恢复工作流', true)
  }
}

watch(
  () => batch.batch.batchId,
  (id) => {
    resetBatchCellSeen(id || 'default')
  },
)

watch(
  () =>
    batch.batch.items
      .map((i) => `${i.index}:${i.url || ''}`)
      .join('|'),
  async () => {
    await nextTick()
    document.querySelectorAll('[data-batch-cell]').forEach((el) => {
      const key = el.getAttribute('data-batch-cell')
      if (key && el.querySelector('img')) animateBatchCellImage(el, key)
    })
  },
)

const gridStyle = computed(() =>
  historyBatchMatrixGridStyle(batch.gridCells.cols),
)

const cellWidthPx = computed(() => historyCardLayout.cardWidth)

const imageBoxStyle = computed(() => {
  const h = historyBatchCellImageHeight.value
  if (h == null) return { minHeight: '4rem' }
  return { height: `${h}px` }
})

function openBatchImagePreview(cell) {
  const img = batch.cellImage(cell)
  if (!img?.url) return
  const picks = (cell.prompt_picks || [])
    .map((p) => `${p.group_name || ''}: ${p.text || ''}`)
    .filter(Boolean)
    .join(' · ')
  const title = [cell.label || img.filename, picks].filter(Boolean).join('\n')
  lightboxRef.value?.openOne(img.url, title)
}
</script>

<template>
  <Card v-if="batch.batch.items.length" class="overflow-hidden">
    <CardHeader class="space-y-3 pb-3">
      <div class="flex flex-wrap items-start justify-between gap-3">
        <div>
          <CardTitle class="text-base">结果网格</CardTitle>
          <CardDescription>
            行 = LoRA A · 列 = LoRA B · {{ batch.gridCells.rows }}×{{ batch.gridCells.cols }} =
            {{ batch.gridCells.rows * batch.gridCells.cols }} 格
          </CardDescription>
          <Badge v-if="batch.batch.batchId" variant="outline" class="mt-2 w-fit font-mono text-xs">
            {{ batch.batch.batchId }}
          </Badge>
        </div>

        <MediaCardLayoutControls v-if="showSizeControls" compact />
      </div>
    </CardHeader>

    <CardContent class="p-0 sm:p-0">
      <div class="overflow-x-auto border-t border-border">
        <div class="inline-block min-w-full p-3 sm:p-4">
          <div class="grid gap-1.5" :style="gridStyle">
            <div />
            <div
              v-for="ib in batch.gridCells.cols"
              :key="'h' + ib"
              class="flex items-center justify-center rounded-md bg-muted py-1 text-center text-xs font-medium text-muted-foreground"
              :style="{ width: cellWidthPx + 'px' }"
            >
              B{{ ib - 1 }}
            </div>
            <template v-for="(row, ia) in batch.gridCells.matrix" :key="'r' + ia">
              <div
                class="flex items-center justify-center rounded-md bg-muted text-xs font-medium text-muted-foreground"
              >
                A{{ ia }}
              </div>
              <div
                v-for="(cell, ib) in row"
                :key="'c' + ia + '-' + ib"
                :data-batch-cell="cell ? `c-${cell.index ?? `${ia}-${ib}`}` : undefined"
                class="overflow-visible rounded-md border border-border bg-background w-full"
                :style="{ width: cellWidthPx + 'px', maxWidth: cellWidthPx + 'px' }"
              >
                <template v-if="cell && batch.cellImage(cell)">
                  <div
                    class="relative overflow-hidden rounded-t-md bg-black/40 flex items-center justify-center"
                    :class="historyCardIsNatural ? '' : ''"
                    :style="[imageBoxStyle, historyCardIsNatural ? {} : historyCardThumbBoxStyle]"
                  >
                    <ImageMagnifierPreview
                      :fill="!historyCardIsNatural"
                      :src="batch.cellImage(cell).url"
                      :img-class="historyCardImgClass"
                      :root-class="historyCardIsNatural ? 'relative w-full' : ''"
                      @click="openBatchImagePreview(cell)"
                    >
                      <template #overlay>
                        <div class="absolute right-1 top-1 z-10 flex gap-0.5">
                          <InpaintJumpButton
                            size="sm"
                            :get-payload="
                              () =>
                                buildInpaintPayloadFromBatchCell(
                                  cell,
                                  batch.runConfig.value,
                                )
                            "
                          />
                          <FavoriteStar
                            v-if="batch.batchFavoritePayload(cell)"
                            :payload="batch.batchFavoritePayload(cell)"
                            size="small"
                            @click.stop
                            @toggled="emit('favorite-toggled', $event)"
                          />
                        </div>
                      </template>
                    </ImageMagnifierPreview>
                  </div>
                  <div
                    v-if="showMeta"
                    :class="
                      cn(
                        'space-y-0.5 border-t border-border/50 p-1.5 text-muted-foreground',
                        cellWidthPx < 120 ? 'text-[9px]' : 'text-[10px]',
                      )
                    "
                  >
                    <div class="truncate" :title="`A=${cell.loras?.A?.strength_model} B=${cell.loras?.B?.strength_model}`">
                      A={{ cell.loras?.A?.strength_model }} · B={{ cell.loras?.B?.strength_model }}
                    </div>
                    <p
                      v-if="cell.prompt_picks?.length"
                      class="truncate text-[9px] opacity-80"
                      :title="cell.prompt_picks.map((p) => p.text || p.tokens?.join(', ')).join(' | ')"
                    >
                      参考：{{ cell.prompt_picks.map((p) => p.text || p.tokens?.join(', ')).join(' | ') }}
                    </p>
                    <div class="flex flex-wrap gap-1">
                      <Button
                        variant="secondary"
                        size="sm"
                        :class="cn('h-6 px-2', cellWidthPx < 120 && 'h-5 px-1 text-[9px]')"
                        @click.stop="regenerateFromCell(cell)"
                      >
                        以此生成
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        :class="cn('h-6 px-2', cellWidthPx < 120 && 'h-5 px-1 text-[9px]')"
                        @click.stop="batch.downloadImage(batch.cellImage(cell))"
                      >
                        保存
                      </Button>
                    </div>
                  </div>
                </template>
                <span
                  v-else-if="cell"
                  class="flex items-center justify-center text-xs text-muted-foreground"
                  :style="imageBoxStyle"
                >
                  {{ cell.status }}
                </span>
                <span
                  v-else
                  class="flex items-center justify-center text-muted-foreground/30"
                  :style="imageBoxStyle"
                >
                  —
                </span>
              </div>
            </template>
          </div>
        </div>
      </div>
      <p v-if="showSizeControls" class="border-t border-border px-4 py-2 text-xs text-muted-foreground">
        与历史记录共用卡片宽度与图片适配；A×B 网格可横向滚动。
      </p>
    </CardContent>
    <ImageLightbox ref="lightboxRef" />
  </Card>
</template>
