<script setup>
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAppStore } from '@/stores/useAppStore.js'
import { useBatchStore } from '@/stores/useBatchStore.js'
import { encodeWorkflowSnapshot, persistRestoreSnapshot } from '@/lib/workflowRestore.js'
import Card from '@/components/ui/Card.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import CardTitle from '@/components/ui/CardTitle.vue'
import CardDescription from '@/components/ui/CardDescription.vue'
import CardContent from '@/components/ui/CardContent.vue'
import Button from '@/components/ui/Button.vue'
import Badge from '@/components/ui/Badge.vue'
import Label from '@/components/ui/Label.vue'
import FavoriteStar from '@/components/FavoriteStar.vue'
import ImageLightbox from '@/components/ImageLightbox.vue'
import { cn } from '@/lib/utils'

const STORAGE_KEY = 'batch-grid-cell-size'

const props = defineProps({
  showSizeControls: { type: Boolean, default: false },
  initialCellSize: { type: Number, default: 160 },
  showMeta: { type: Boolean, default: true },
})

const emit = defineEmits(['favorite-toggled'])

const app = useAppStore()
const batch = useBatchStore()
const router = useRouter()
const lightboxRef = ref(null)

async function regenerateFromCell(cell) {
  const snap = batch.workflowSnapshotForCell(cell)
  if (!snap?.workflow_id && !batch.runConfig.value?.workflow_id) {
    app.setMessage('缺少工作流信息，无法恢复', true)
    return
  }
  const wid = snap.workflow_id || batch.runConfig.value?.workflow_id
  const encoded = encodeWorkflowSnapshot(snap)
  const restoreKey = persistRestoreSnapshot(batch.batch.batchId, cell.index, snap)
  const query = { workflow: wid }
  if (restoreKey) {
    query.restoreKey = restoreKey
  }
  if (encoded && encoded.length < 2400) {
    query.restore = encoded
  } else if (!restoreKey) {
    app.setMessage('快照过大且无法缓存，请刷新后重试', true)
    return
  }
  router.push({ path: '/generate', query })
}

function readStoredSize() {
  const n = Number(localStorage.getItem(STORAGE_KEY))
  return Number.isFinite(n) && n >= 64 && n <= 480 ? n : props.initialCellSize
}

const cellSize = ref(readStoredSize())

const sizePresets = [
  { label: '小', value: 96 },
  { label: '中', value: 140 },
  { label: '大', value: 200 },
  { label: '特大', value: 280 },
]

watch(cellSize, (v) => {
  localStorage.setItem(STORAGE_KEY, String(Math.round(v)))
})

const gridStyle = computed(() => ({
  gridTemplateColumns: `2.75rem repeat(${batch.gridCells.cols}, ${cellSize.value}px)`,
}))

const imageHeight = computed(() => Math.max(64, cellSize.value - (props.showMeta ? 36 : 0)))

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

        <div
          v-if="showSizeControls"
          class="flex flex-wrap items-center gap-3 rounded-lg border border-border bg-muted/40 px-3 py-2"
        >
          <Label class="text-xs text-muted-foreground shrink-0">缩略图尺寸</Label>
          <div class="flex gap-1">
            <Button
              v-for="p in sizePresets"
              :key="p.value"
              type="button"
              :variant="cellSize === p.value ? 'default' : 'outline'"
              size="sm"
              class="h-7 min-w-9 px-2 text-xs"
              @click="cellSize = p.value"
            >
              {{ p.label }}
            </Button>
          </div>
          <input
            v-model.number="cellSize"
            type="range"
            min="64"
            max="480"
            step="8"
            class="h-2 w-28 cursor-pointer accent-primary"
          />
          <span class="w-12 text-right font-mono text-xs text-muted-foreground">{{ cellSize }}px</span>
        </div>
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
              :style="{ width: cellSize + 'px' }"
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
                class="overflow-hidden rounded-md border border-border bg-background"
                :style="{ width: cellSize + 'px' }"
              >
                <template v-if="cell && batch.cellImage(cell)">
                  <div class="relative bg-black/40">
                    <FavoriteStar
                      v-if="batch.batchFavoritePayload(cell)"
                      :payload="batch.batchFavoritePayload(cell)"
                      size="small"
                      class="absolute right-1 top-1 z-10"
                      @toggled="emit('favorite-toggled', $event)"
                    />
                    <img
                      :src="batch.cellImage(cell).url"
                      loading="lazy"
                      :style="{ height: imageHeight + 'px' }"
                      class="w-full cursor-zoom-in object-contain hover:opacity-90"
                      @click="openBatchImagePreview(cell)"
                    />
                  </div>
                  <div
                    v-if="showMeta"
                    :class="
                      cn(
                        'space-y-0.5 border-t border-border/50 p-1.5 text-muted-foreground',
                        cellSize < 120 ? 'text-[9px]' : 'text-[10px]',
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
                        :class="cn('h-6 px-2', cellSize < 120 && 'h-5 px-1 text-[9px]')"
                        @click.stop="regenerateFromCell(cell)"
                      >
                        以此生成
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        :class="cn('h-6 px-2', cellSize < 120 && 'h-5 px-1 text-[9px]')"
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
                  :style="{ height: imageHeight + 'px', minHeight: '4rem' }"
                >
                  {{ cell.status }}
                </span>
                <span
                  v-else
                  class="flex items-center justify-center text-muted-foreground/30"
                  :style="{ height: imageHeight + 'px', minHeight: '4rem' }"
                >
                  —
                </span>
              </div>
            </template>
          </div>
        </div>
      </div>
      <p v-if="showSizeControls" class="border-t border-border px-4 py-2 text-xs text-muted-foreground">
        网格较宽时可横向滚动；缩略图尺寸会保存在本地浏览器。
      </p>
    </CardContent>
    <ImageLightbox ref="lightboxRef" />
  </Card>
</template>
