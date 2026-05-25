<script setup>
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useHistoryStore } from '@/stores/useHistoryStore.js'
import { useAppStore } from '@/stores/useAppStore.js'
import { buildRegenerateRestoreRoute } from '@/lib/regenerateFromImage.js'
import { statusLabel } from '@/api/client.js'
import HistoryMetaPanel from '@/components/history/HistoryMetaPanel.vue'
import HistoryBatchCellCard from '@/components/history/HistoryBatchCellCard.vue'
import HistoryImageDetailModal from '@/components/history/HistoryImageDetailModal.vue'
import HistoryPromptCompareModal from '@/components/history/HistoryPromptCompareModal.vue'
import ImageLightbox from '@/components/ImageLightbox.vue'
import Button from '@/components/ui/Button.vue'
import Badge from '@/components/ui/Badge.vue'
import Label from '@/components/ui/Label.vue'
import SelectNative from '@/components/ui/SelectNative.vue'
import { buildCellDetailMeta } from '@/lib/cellDetailMeta.js'
import { cellSelectionKey, cellSelectionLabel } from '@/lib/promptCompare.js'
import { buildBatchFavoritePayload } from '@/utils/favoritePayload.js'
import AnimatedCollapse from '@/components/ui/AnimatedCollapse.vue'
import { ArrowLeft, ChevronDown, ChevronUp, GitCompare, Trash2 } from 'lucide-vue-next'
import { isAdmin } from '@/composables/useAuth.js'
import { useImageDownload } from '@/composables/useImageDownload.js'
import { useConfirmDialog } from '@/composables/useConfirmDialog.js'
import {
  historyBatchMatrixGridStyle,
  historyCardLayout,
} from '@/composables/useHistoryCardLayout.js'
import MediaCardLayoutControls from '@/components/shared/MediaCardLayoutControls.vue'

const emit = defineEmits(['back', 'deleted'])

const history = useHistoryStore()
const { confirmDelete } = useConfirmDialog()
const app = useAppStore()
const router = useRouter()
const deleting = ref(false)
const batchInfoOpen = ref(false)
const lightboxRef = ref(null)
const detailOpen = ref(false)
const detailMeta = ref(null)
const detailImageUrl = ref('')
const selectMode = ref(false)
const selectedKeys = ref(new Set())
const compareOpen = ref(false)
const { saveOne, saveAll } = useImageDownload()

const colsPerRow = ref(5)

const entry = computed(() => history.batchDetail)
const items = computed(() => entry.value?.items || [])
const gridInfo = computed(() => entry.value?.plan?.grid || entry.value?.grid)

const sweepCols = computed(() => gridInfo.value?.b_count || 1)
const sweepRows = computed(() => gridInfo.value?.a_count || 1)

/** 每行列数 = B 轴档位数 → A×B 矩阵布局 */
const isMatrixLayout = computed(() => colsPerRow.value === sweepCols.value)

const matrix = computed(() => {
  const rows = sweepRows.value
  const cols = sweepCols.value
  const map = new Map()
  for (const it of items.value) {
    map.set(`${it.ia}-${it.ib}`, it)
  }
  const cells = []
  for (let ia = 0; ia < rows; ia++) {
    const row = []
    for (let ib = 0; ib < cols; ib++) {
      row.push(map.get(`${ia}-${ib}`) || null)
    }
    cells.push(row)
  }
  return { rows, cols, cells }
})

const flatCells = computed(() => {
  const list = []
  for (let ia = 0; ia < matrix.value.rows; ia++) {
    for (let ib = 0; ib < matrix.value.cols; ib++) {
      list.push({
        cell: matrix.value.cells[ia][ib],
        ia,
        ib,
      })
    }
  }
  return list
})

const gridColumnsStyle = computed(() => {
  if (isMatrixLayout.value) {
    return historyBatchMatrixGridStyle(colsPerRow.value)
  }
  const w = historyCardLayout.cardWidth
  const cols = Math.max(1, colsPerRow.value)
  return {
    gridTemplateColumns: `repeat(${cols}, ${w}px)`,
    justifyContent: 'start',
  }
})

const colOptions = computed(() => {
  const max = Math.max(sweepCols.value, 12)
  return Array.from({ length: max }, (_, i) => i + 1)
})

watch(
  () => gridInfo.value?.b_count,
  (b) => {
    if (b && b > 0) colsPerRow.value = b
  },
  { immediate: true },
)

watch(
  () => entry.value?.batch_id,
  () => {
    batchInfoOpen.value = false
    selectMode.value = false
    selectedKeys.value = new Set()
    compareOpen.value = false
  },
)

const selectedCount = computed(() => selectedKeys.value.size)

const compareItems = computed(() => {
  const list = []
  for (const { cell, ia, ib } of flatCells.value) {
    if (!cell || !cellImage(cell)) continue
    const key = cellSelectionKey(cell, ia, ib)
    if (!selectedKeys.value.has(key)) continue
    const meta = buildCellDetailMeta(cell, {
      workflow_id: entry.value?.workflow_id,
      run_config: entry.value?.run_config,
      batch_meta: entry.value?.meta,
    })
    list.push({
      key,
      label: cellSelectionLabel(cell, ia, ib, matrix.value.cols),
      meta,
    })
  }
  return list
})

function resetColsToSweep() {
  colsPerRow.value = sweepCols.value
}

function cellImage(cell) {
  return cell?.images?.[0]
}

function cellTitle(cell) {
  const picks = (cell.prompt_picks || [])
    .map((p) => p.text || p.group_name)
    .filter(Boolean)
    .join(' · ')
  return [cell.label, picks].filter(Boolean).join('\n')
}

function openCellLightbox(cell) {
  const img = cellImage(cell)
  if (!img?.url) return
  lightboxRef.value?.openOne(img.url, cellTitle(cell))
}

async function regenerateFromCell(cell) {
  try {
    const route = await buildRegenerateRestoreRoute({
      cell,
      runConfig: entry.value?.run_config,
      batchId: entry.value?.batch_id,
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

function favoritePayload(cell) {
  return buildBatchFavoritePayload(
    entry.value?.workflow_id,
    cell,
    entry.value?.batch_id,
    cell.overrides,
  )
}

function openCellDetail(cell, ia, ib) {
  const meta = buildCellDetailMeta(cell, {
    workflow_id: entry.value?.workflow_id,
    run_config: entry.value?.run_config,
    batch_meta: entry.value?.meta,
  })
  if (!meta) return
  meta.ia = ia
  meta.ib = ib
  detailMeta.value = meta
  detailImageUrl.value = cellImage(cell)?.url || ''
  detailOpen.value = true
}

function closeCellDetail() {
  detailOpen.value = false
}

function toggleSelectMode() {
  selectMode.value = !selectMode.value
  if (!selectMode.value) selectedKeys.value = new Set()
}

function isCellSelected(cell, ia, ib) {
  if (!cell) return false
  return selectedKeys.value.has(cellSelectionKey(cell, ia, ib))
}

function toggleCellSelect(cell, ia, ib) {
  if (!cell) return
  const key = cellSelectionKey(cell, ia, ib)
  const next = new Set(selectedKeys.value)
  if (next.has(key)) next.delete(key)
  else next.add(key)
  selectedKeys.value = next
}

function selectAllWithImages() {
  const next = new Set()
  for (const { cell, ia, ib } of flatCells.value) {
    if (cell && cellImage(cell)) next.add(cellSelectionKey(cell, ia, ib))
  }
  selectedKeys.value = next
}

function clearSelection() {
  selectedKeys.value = new Set()
}

function openCompare() {
  if (compareItems.value.length >= 2) compareOpen.value = true
}

function selectedIndices() {
  const indices = []
  for (const { cell, ia, ib } of flatCells.value) {
    if (!cell || cell.index == null || !cellImage(cell)) continue
    if (!selectedKeys.value.has(cellSelectionKey(cell, ia, ib))) continue
    indices.push(cell.index)
  }
  return indices
}

async function deleteSelectedCells() {
  const indices = selectedIndices()
  if (!indices.length) {
    app.setMessage('请先勾选要删除的图片', true)
    return
  }
  if (
    !(await confirmDelete({
      message: `确定删除选中的 ${indices.length} 张？对应输出文件将移除。`,
    }))
  )
    return
  deleting.value = true
  try {
    const res = await history.deleteBatchItems(entry.value.batch_id, indices)
    selectedKeys.value = new Set()
    app.setMessage(`已删除 ${res.removed ?? indices.length} 张`)
    if (!res.remaining) {
      emit('deleted')
      return
    }
  } catch (e) {
    app.setMessage(e.message, true)
  } finally {
    deleting.value = false
  }
}

function batchImagesForDownload() {
  return flatCells.value
    .map(({ cell }) => cellImage(cell))
    .filter((img) => img?.url)
}

function saveAllBatchImages() {
  saveAll(batchImagesForDownload(), entry.value?.batch_id || 'batch')
}

function saveCellImage(cell) {
  const img = cellImage(cell)
  if (img?.url) saveOne(img)
}

async function deleteWholeBatch() {
  const id = entry.value?.batch_id
  if (!id) return
  if (
    !(await confirmDelete({
      message: `删除整批「${id}」？将移除该批次下所有图片与记录。`,
    }))
  )
    return
  deleting.value = true
  try {
    await history.deleteBatch(id)
    app.setMessage('已删除整批记录')
    emit('deleted')
  } catch (e) {
    app.setMessage(e.message, true)
  } finally {
    deleting.value = false
  }
}
</script>

<template>
  <div class="flex w-full flex-col gap-4">
    <Button variant="outline" size="sm" class="w-fit gap-1.5" @click="emit('back')">
      <ArrowLeft class="h-4 w-4" />
      返回列表
    </Button>

    <div v-if="history.detailLoading" class="py-16 text-center text-sm text-muted-foreground">
      加载批量详情…
    </div>

    <template v-else-if="entry">
      <header
        class="rounded-xl border-2 border-violet-500/35 bg-gradient-to-br from-violet-500/8 to-transparent p-4 md:p-5"
      >
        <div class="flex flex-wrap items-center gap-2">
          <Badge class="border-0 bg-violet-600 text-white">批量生成</Badge>
          <Badge variant="outline">{{ statusLabel(entry.status) }}</Badge>
        </div>
        <h2 class="mt-2 truncate font-mono text-sm">{{ entry.batch_id }}</h2>
        <p v-if="entry.task_name" class="text-sm text-muted-foreground">{{ entry.task_name }}</p>
        <p v-if="entry.strategy_summary" class="mt-1 text-xs text-muted-foreground">
          {{ entry.strategy_summary }}
        </p>
        <p class="mt-1 text-xs text-muted-foreground">
          {{ entry.completed }}/{{ entry.total }}
          <template v-if="gridInfo">
            · 扫参 {{ sweepRows }}×{{ sweepCols }}（行=A · 列=B）
          </template>
        </p>
        <div v-if="entry.meta" class="mt-3 border-t border-violet-500/20 pt-3">
          <button
            type="button"
            class="flex w-full items-center justify-between gap-2 text-left text-sm font-medium hover:text-primary transition-colors"
            @click="batchInfoOpen = !batchInfoOpen"
          >
            <span>批量生成信息</span>
            <span class="flex items-center gap-1.5 text-xs font-normal text-muted-foreground">
              {{ batchInfoOpen ? '收起' : '展开' }}
              <component
                :is="batchInfoOpen ? ChevronUp : ChevronDown"
                class="h-4 w-4 shrink-0"
              />
            </span>
          </button>
          <AnimatedCollapse v-model="batchInfoOpen">
            <HistoryMetaPanel class="mt-3" :meta="entry.meta" :workflow-id="entry.workflow_id" />
          </AnimatedCollapse>
        </div>
        <div class="mt-3 flex flex-wrap gap-2">
          <Button
            v-if="isAdmin()"
            variant="destructive"
            size="sm"
            class="gap-1.5"
            :disabled="deleting"
            @click="deleteWholeBatch"
          >
            <Trash2 class="h-3.5 w-3.5" />
            删除整批
          </Button>
        </div>
      </header>

      <section class="w-full space-y-3">
        <div
          class="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border bg-card px-4 py-3"
        >
          <div>
            <h3 class="text-sm font-medium">扫参结果</h3>
            <p class="text-[11px] text-muted-foreground">
              <template v-if="isMatrixLayout">
                A×B 矩阵：{{ sweepRows }} 行 × 每行 {{ sweepCols }} 列
              </template>
              <template v-else>
                平铺：每行 {{ colsPerRow }} 张
              </template>
            </p>
          </div>
          <div class="flex flex-wrap items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              class="text-xs"
              :disabled="!batchImagesForDownload().length"
              @click="saveAllBatchImages"
            >
              全部保存
            </Button>
            <Button
              :variant="selectMode ? 'default' : 'outline'"
              size="sm"
              class="gap-1 text-xs"
              @click="toggleSelectMode"
            >
              {{ selectMode ? '取消多选' : '多选' }}
            </Button>
            <template v-if="selectMode">
              <span class="text-xs text-muted-foreground">已选 {{ selectedCount }} 张</span>
              <Button variant="outline" size="sm" class="text-xs" @click="selectAllWithImages">
                全选
              </Button>
              <Button
                variant="outline"
                size="sm"
                class="text-xs"
                :disabled="!selectedCount"
                @click="clearSelection"
              >
                清空
              </Button>
              <Button
                v-if="isAdmin()"
                variant="destructive"
                size="sm"
                class="gap-1 text-xs"
                :disabled="!selectedCount || deleting"
                @click="deleteSelectedCells"
              >
                <Trash2 class="h-3 w-3" />
                删除选中
              </Button>
              <Button
                variant="outline"
                size="sm"
                class="gap-1 text-xs"
                :disabled="selectedCount < 2"
                @click="openCompare"
              >
                <GitCompare class="h-3.5 w-3.5" />
                对比提示词
              </Button>
            </template>
            <Label class="shrink-0 text-xs">每行张数</Label>
            <SelectNative v-model.number="colsPerRow" class="w-20">
              <option v-for="n in colOptions" :key="n" :value="n">{{ n }}</option>
            </SelectNative>
            <Button
              variant="outline"
              size="sm"
              class="text-xs"
              :disabled="isMatrixLayout"
              @click="resetColsToSweep"
            >
              恢复 {{ sweepRows }}×{{ sweepCols }}
            </Button>
          </div>
        </div>
        <p v-if="selectMode" class="text-[11px] text-muted-foreground">
          可全选后删除多张，或勾选至少 2 张后「对比提示词」。
        </p>

        <MediaCardLayoutControls class="mb-1" />

        <div class="w-full overflow-x-auto rounded-lg border border-border bg-card/40 p-3 md:p-4">
          <!-- 默认 A×B：行=A 档，列=B 档 -->
          <div v-if="isMatrixLayout" class="grid gap-2 w-max min-w-full" :style="gridColumnsStyle">
            <div />
            <div
              v-for="ib in matrix.cols"
              :key="'h-' + ib"
              class="flex items-center justify-center py-1 text-center text-[10px] font-medium text-muted-foreground"
              :style="{ width: historyCardLayout.cardWidth + 'px' }"
            >
              B{{ ib }}
            </div>
            <template v-for="(row, ia) in matrix.cells" :key="'row-' + ia">
              <div
                class="flex items-center justify-center text-[10px] font-medium text-violet-600/90"
              >
                A{{ ia }}
              </div>
              <HistoryBatchCellCard
                v-for="(cell, ib) in row"
                :key="`${ia}-${ib}`"
                :cell="cell"
                :ia="ia"
                :ib="ib"
                :select-mode="selectMode"
                :selected="isCellSelected(cell, ia, ib)"
                :favorite-payload="cell && !selectMode ? favoritePayload(cell) : null"
                @preview="cell && openCellLightbox(cell)"
                @detail="cell && openCellDetail(cell, ia, ib)"
                @regenerate="cell && regenerateFromCell(cell)"
                @save="cell && saveCellImage(cell)"
                @toggle-select="toggleCellSelect(cell, ia, ib)"
              />
            </template>
          </div>

          <!-- 自定义每行张数：按序号平铺 -->
          <div v-else class="grid gap-3 w-max min-w-full" :style="gridColumnsStyle">
            <HistoryBatchCellCard
              v-for="{ cell, ia, ib } in flatCells"
              :key="`${ia}-${ib}`"
              :cell="cell"
              :ia="ia"
              :ib="ib"
              :show-axis="false"
              :matrix-cols="matrix.cols"
              :select-mode="selectMode"
              :selected="isCellSelected(cell, ia, ib)"
              :favorite-payload="cell && !selectMode ? favoritePayload(cell) : null"
              @preview="cell && openCellLightbox(cell)"
              @detail="cell && openCellDetail(cell, ia, ib)"
              @regenerate="cell && regenerateFromCell(cell)"
              @save="cell && saveCellImage(cell)"
              @toggle-select="toggleCellSelect(cell, ia, ib)"
            />
          </div>
        </div>
      </section>
    </template>

    <ImageLightbox ref="lightboxRef" />
    <HistoryImageDetailModal
      :open="detailOpen"
      :meta="detailMeta"
      :image-url="detailImageUrl"
      @close="closeCellDetail"
    />
    <HistoryPromptCompareModal
      :open="compareOpen"
      :items="compareItems"
      @close="compareOpen = false"
    />
  </div>
</template>
