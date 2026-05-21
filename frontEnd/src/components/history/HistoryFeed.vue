<script setup>
import { ref } from 'vue'
import { useHistoryStore } from '@/stores/useHistoryStore.js'
import { useAppStore } from '@/stores/useAppStore.js'
import { statusLabel } from '@/api/client.js'
import Badge from '@/components/ui/Badge.vue'
import IconDeleteButton from '@/components/ui/IconDeleteButton.vue'
import { cn } from '@/lib/utils'
import { Grid3x3, ImageIcon } from 'lucide-vue-next'

const history = useHistoryStore()
const app = useAppStore()
const deleting = ref(false)
const emit = defineEmits(['preview-single'])

async function deleteRecord(ev, rec) {
  ev.stopPropagation()
  if (rec.type === 'batch') {
    const id = rec.batch_id || rec.id
    if (!confirm(`删除整批「${id}」？将移除该批次下所有图片与记录。`)) return
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
  if (!confirm('删除该单抽记录？图片文件将一并移除。')) return
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
  history.selectRecord(rec)
}

function previewSingle(ev, rec) {
  ev.stopPropagation()
  emit('preview-single', rec)
}
</script>

<template>
  <p v-if="!history.records.length && !history.loading" class="py-12 text-center text-sm text-muted-foreground">
    暂无历史记录。完成单抽或批量后会出现在这里。
  </p>
  <div
    v-else
    class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5"
  >
    <article
      v-for="rec in history.records"
      :key="rec.id"
      :class="
        cn(
          'group cursor-pointer overflow-hidden rounded-xl border-2 bg-card transition-all hover:shadow-md',
          rec.type === 'batch'
            ? 'border-violet-500/40 hover:border-violet-500/70'
            : 'border-sky-500/35 hover:border-sky-500/60',
        )
      "
      @click="select(rec)"
    >
      <div class="relative flex aspect-[4/5] items-center justify-center bg-muted/40 p-1">
        <img
          v-if="rec.thumbnail_url"
          :src="rec.thumbnail_url"
          class="max-h-full max-w-full object-contain"
          loading="lazy"
          alt=""
        />
        <span
          v-else
          class="flex h-full items-center justify-center text-xs text-muted-foreground"
        >
          无预览
        </span>
        <div class="absolute left-2 top-2 flex items-center gap-1">
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
        <IconDeleteButton
          size="sm"
          class="absolute right-2 top-2 opacity-0 group-hover:opacity-100 transition-opacity"
          :disabled="deleting"
          :title="rec.type === 'batch' ? '删除整批' : '删除'"
          @click="deleteRecord($event, rec)"
        />
        <button
          v-if="rec.type === 'single' && rec.thumbnail_url"
          type="button"
          class="absolute inset-0 flex items-center justify-center bg-black/0 opacity-0 transition group-hover:bg-black/30 group-hover:opacity-100"
          @click="previewSingle($event, rec)"
        >
          <span class="rounded-md bg-background/90 px-2 py-1 text-xs font-medium">放大</span>
        </button>
      </div>
      <div class="space-y-1 p-3">
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
        <Badge variant="outline" class="text-[10px]">{{ statusLabel(rec.status) }}</Badge>
      </div>
    </article>
  </div>
</template>
