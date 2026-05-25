<script setup>
import { ref } from 'vue'
import { useHistoryStore } from '@/stores/useHistoryStore.js'
import { useAppStore } from '@/stores/useAppStore.js'
import { isAdmin } from '@/composables/useAuth.js'
import { statusLabel } from '@/api/client.js'
import Badge from '@/components/ui/Badge.vue'
import IconDeleteButton from '@/components/ui/IconDeleteButton.vue'
import { cn } from '@/lib/utils'
import { Check, Grid3x3, ImageIcon } from 'lucide-vue-next'
import ImageMagnifierPreview from '@/components/media/ImageMagnifierPreview.vue'
import InpaintJumpButton from '@/components/inpaint/InpaintJumpButton.vue'
import { buildInpaintPayloadFromHistory } from '@/lib/inpaintBootstrap.js'
import { useConfirmDialog } from '@/composables/useConfirmDialog.js'
import {
  historyCardGridStyle,
  historyCardImgClass,
  historyCardIsNatural,
  historyCardThumbBoxStyle,
} from '@/composables/useHistoryCardLayout.js'

const history = useHistoryStore()
const { confirmDelete } = useConfirmDialog()
const app = useAppStore()
const deleting = ref(false)

const emit = defineEmits(['preview-image'])

async function deleteRecord(ev, rec) {
  ev.stopPropagation()
  if (rec.type === 'batch') {
    const id = rec.batch_id || rec.id
    if (
      !(await confirmDelete({
        message: `删除整批「${id}」？将移除该批次下所有图片与记录。`,
      }))
    )
      return
    deleting.value = true
    try {
      await history.deleteBatch(id)
      app.setMessage('已删除批量记录')
    } catch (e) {
      app.setMessage(e.message, true)
    } finally {
      deleting.value = false
    }
    return
  }
  const pid = rec.prompt_id || rec.id
  if (
    !(await confirmDelete({
      message: '删除该单抽记录？图片文件将一并移除。',
    }))
  )
    return
  deleting.value = true
  try {
    await history.deleteSingle(pid)
    app.setMessage('已删除单抽记录')
  } catch (e) {
    app.setMessage(e.message, true)
  } finally {
    deleting.value = false
  }
}

function formatTime(iso) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString('zh-CN', { hour12: false })
  } catch {
    return iso
  }
}

function select(rec) {
  if (history.bulkSelectMode) {
    history.toggleSelect(rec)
    return
  }
  history.selectRecord(rec)
}

function previewImage(ev, rec) {
  ev.stopPropagation()
  if (history.bulkSelectMode) {
    history.toggleSelect(rec)
    return
  }
  const url = rec.thumbnail_url || rec.images?.[0]?.url
  if (url) emit('preview-image', rec)
}

function toggleSelect(ev, rec) {
  ev.stopPropagation()
  history.toggleSelect(rec)
}

function showImageStatus(rec) {
  if (rec.status && rec.status !== 'completed') return true
  if (rec.type === 'batch' && rec.total != null && rec.completed < rec.total) return true
  return false
}

function statusBadgeVariant(status) {
  if (status === 'completed') return 'outline'
  if (['failed', 'cancelled', 'deleted'].includes(status)) return 'destructive'
  return 'default'
}
</script>

<template>
  <p v-if="!history.records.length && !history.loading" class="py-12 text-center text-sm text-muted-foreground">
    暂无历史记录。完成单抽或批量后会出现在这里。
  </p>
  <p
    v-else-if="history.bulkSelectMode"
    class="text-[11px] text-muted-foreground"
  >
    多选模式：点击图片或卡片勾选；已选 {{ history.selectedKeys.size }} 条。
  </p>
  <TransitionGroup
    v-if="history.records.length || history.loading"
    tag="div"
    name="history-card"
    class="history-feed-grid grid gap-4"
    :style="historyCardGridStyle"
  >
    <article
      v-for="rec in history.records"
      :key="rec.id"
      :class="
        cn(
          'group relative w-full max-w-full overflow-visible rounded-xl border-2 bg-card transition-[box-shadow,border-color] duration-200 hover:shadow-md',
          rec.type === 'batch'
            ? 'border-violet-500/40 hover:border-violet-500/70'
            : 'border-sky-500/35 hover:border-sky-500/60',
          history.bulkSelectMode && history.isSelected(rec)
            ? 'border-violet-500 ring-2 ring-violet-500/35'
            : '',
        )
      "
    >
      <div
        class="relative overflow-hidden rounded-t-[10px] bg-muted/40 flex items-center justify-center"
        :class="[
          history.bulkSelectMode ? 'cursor-pointer' : 'cursor-zoom-in',
          historyCardIsNatural ? 'min-h-[8rem]' : '',
        ]"
        :style="historyCardThumbBoxStyle"
        @click.stop="previewImage($event, rec)"
      >
        <ImageMagnifierPreview
          v-if="rec.thumbnail_url"
          :fill="!historyCardIsNatural"
          :src="rec.thumbnail_url"
          :img-class="historyCardImgClass"
          :root-class="historyCardIsNatural ? 'relative w-full' : ''"
          :disabled="history.bulkSelectMode"
        />
        <span
          v-else
          class="flex h-full w-full items-center justify-center text-xs text-muted-foreground"
        >
          无预览
        </span>
        <div class="pointer-events-none absolute left-2 top-2 flex items-center gap-1">
          <Badge
            :class="
              cn(
                'gap-1 text-[10px] font-semibold',
                rec.type === 'batch'
                  ? 'bg-violet-600/90 text-white border-0'
                  : 'bg-sky-600/90 text-white border-0',
              )
            "
          >
            <Grid3x3 v-if="rec.type === 'batch'" class="h-3 w-3" />
            <ImageIcon v-else class="h-3 w-3" />
            {{ rec.type === 'batch' ? '批量' : '单抽' }}
          </Badge>
        </div>

        <div
          v-if="showImageStatus(rec)"
          class="pointer-events-none absolute bottom-2 left-2 z-20 flex flex-wrap gap-1"
        >
          <Badge
            v-if="rec.status && rec.status !== 'completed'"
            :variant="statusBadgeVariant(rec.status)"
            class="text-[10px] bg-background/90 shadow-sm"
          >
            {{ statusLabel(rec.status) }}
          </Badge>
          <Badge
            v-if="rec.type === 'batch' && rec.total != null && rec.completed < rec.total"
            variant="outline"
            class="text-[10px] bg-background/90 shadow-sm tabular-nums"
          >
            {{ rec.completed }}/{{ rec.total }}
          </Badge>
        </div>

        <div
          v-if="
            rec.type === 'single' &&
            (rec.thumbnail_url || rec.images?.[0]?.url) &&
            !history.bulkSelectMode
          "
          class="absolute right-2 bottom-2 z-20 pointer-events-auto"
        >
          <InpaintJumpButton
            size="sm"
            :get-payload="() => buildInpaintPayloadFromHistory(rec)"
          />
        </div>

        <button
          v-if="isAdmin() && history.bulkSelectMode"
          type="button"
          class="absolute right-2 top-2 z-30 flex h-7 w-7 items-center justify-center rounded-full border-2 shadow-md transition-colors"
          :class="
            history.isSelected(rec)
              ? 'border-violet-500 bg-violet-600 text-white'
              : 'border-white/90 bg-background/90 text-transparent hover:border-violet-400'
          "
          :aria-label="history.isSelected(rec) ? '取消选择' : '选择'"
          @click="toggleSelect($event, rec)"
        >
          <Check class="h-4 w-4" :class="history.isSelected(rec) ? 'opacity-100' : 'opacity-0'" />
        </button>

        <IconDeleteButton
          v-else-if="isAdmin()"
          size="sm"
          class="history-thumb-delete absolute right-2 top-2 z-20 opacity-0 pointer-events-none group-hover:opacity-100 group-hover:pointer-events-auto transition-opacity"
          :disabled="deleting"
          :title="rec.type === 'batch' ? '删除整批' : '删除'"
          @click="deleteRecord($event, rec)"
        />
      </div>
      <div
        class="cursor-pointer space-y-1 rounded-b-[10px] p-3 transition-colors hover:bg-accent/40"
        @click="select(rec)"
      >
        <p class="truncate font-mono text-[10px] text-muted-foreground">
          {{ rec.type === 'batch' ? rec.batch_id : rec.prompt_id }}
        </p>
        <p class="text-xs font-medium truncate">{{ rec.workflow_id || '?' }}</p>
        <p v-if="rec.type === 'batch'" class="text-[11px] text-muted-foreground">
          {{ rec.completed }}/{{ rec.total }}
          <template v-if="rec.grid"> · {{ rec.grid.a_count }}×{{ rec.grid.b_count }}</template>
        </p>
        <p v-else-if="rec.meta?.loras?.length" class="text-[11px] text-primary/90 truncate">
          {{ rec.meta.loras.map((l) => l.short_name).join(' × ') }}
        </p>
        <p class="text-[10px] text-muted-foreground">{{ formatTime(rec.started_at) }}</p>
        <Badge
          v-if="!showImageStatus(rec)"
          variant="outline"
          class="text-[10px]"
        >
          {{ statusLabel(rec.status) }}
        </Badge>
      </div>
    </article>
  </TransitionGroup>
</template>

<style scoped>
.history-card-leave-active {
  transition: opacity 0.15s ease;
}
.history-card-leave-to {
  opacity: 0;
}

/* TransitionGroup 根节点需占满宽，列宽由 gridTemplateColumns 控制 */
.history-feed-grid {
  width: 100%;
}
</style>
