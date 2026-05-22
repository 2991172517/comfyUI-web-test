<script setup>
import { useFavoritesPageStore } from '@/stores/useFavoritesPageStore.js'
import Badge from '@/components/ui/Badge.vue'
import IconDeleteButton from '@/components/ui/IconDeleteButton.vue'
import { cn } from '@/lib/utils'
import { favoriteSourceLabel, isFromBatchGrid } from '@/lib/favoriteMeta.js'
import { Grid3x3, ImageIcon, Star } from 'lucide-vue-next'
import { api } from '@/api/client.js'
import { useAppStore } from '@/stores/useAppStore.js'
import { favoriteEntryToTogglePayload } from '@/lib/favoriteToggle.js'
import { useImageDownload } from '@/composables/useImageDownload.js'

const emit = defineEmits(['preview'])

const fav = useFavoritesPageStore()
const app = useAppStore()
const { saveOne } = useImageDownload()

function formatTime(iso) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString('zh-CN', { hour12: false })
  } catch {
    return iso
  }
}

function select(f) {
  fav.selectFavorite(f)
}

function preview(ev, f) {
  ev.stopPropagation()
  if (f.image?.url) emit('preview', f)
}

function saveImage(ev, f) {
  ev.stopPropagation()
  if (f.image?.url) saveOne(f.image)
}

async function remove(ev, f) {
  ev.stopPropagation()
  if (!confirm('取消收藏？（仅删除记录，不删原图）')) return
  try {
    const body = favoriteEntryToTogglePayload(f)
    if (!body?.image?.filename) {
      app.setMessage('无法取消收藏：缺少图片信息', true)
      return
    }
    await api.toggleFavorite(body)
    fav.removeFromList(f.id)
    app.setMessage('已取消收藏')
  } catch (e) {
    app.setMessage(e.message, true)
  }
}
</script>

<template>
  <p
    v-if="fav.loading"
    class="py-12 text-center text-sm text-muted-foreground"
  >
    加载收藏中…
  </p>
  <p
    v-else-if="!fav.records.length"
    class="py-12 text-center text-sm text-muted-foreground"
  >
    暂无收藏。在抽卡结果、批量网格或历史记录中点击 ☆ 收藏。
  </p>
  <div
    v-else
    class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5"
  >
    <article
      v-for="f in fav.records"
      :key="f.id"
      :class="
        cn(
          'group cursor-pointer overflow-hidden rounded-xl border-2 bg-card transition-all hover:shadow-md',
          fav.selected?.id === f.id
            ? 'border-amber-500/70 ring-1 ring-amber-500/30'
            : 'border-amber-500/35 hover:border-amber-500/55',
        )
      "
      @click="select(f)"
    >
      <div class="relative flex aspect-[4/5] items-center justify-center bg-muted/40 p-1">
        <img
          v-if="f.image?.url"
          :src="f.image.url"
          class="max-h-full max-w-full object-contain"
          loading="lazy"
          alt=""
        />
        <span
          v-else
          class="flex h-full items-center justify-center px-2 text-center text-xs text-muted-foreground"
        >
          原图已删除
        </span>
        <Badge
          :class="
            cn(
              'absolute left-2 top-2 gap-1 border-0 text-[10px] font-semibold text-white',
              isFromBatchGrid(f)
                ? 'bg-violet-600/90'
                : 'bg-amber-600/90',
            )
          "
        >
          <Grid3x3 v-if="isFromBatchGrid(f)" class="h-3 w-3" />
          <Star v-else class="h-3 w-3 fill-current" />
          {{ favoriteSourceLabel(f) }}
        </Badge>
        <div
          class="absolute right-2 top-2 flex gap-1 opacity-0 transition group-hover:opacity-100"
        >
          <button
            v-if="f.image?.url"
            type="button"
            class="rounded-md bg-background/90 px-2 py-1 text-[10px] font-medium shadow"
            @click="preview($event, f)"
          >
            放大
          </button>
          <button
            v-if="f.image?.url"
            type="button"
            class="rounded-md bg-background/90 px-2 py-1 text-[10px] font-medium shadow"
            @click="saveImage($event, f)"
          >
            保存
          </button>
          <IconDeleteButton size="sm" title="取消收藏" @click="remove($event, f)" />
        </div>
        <Badge
          v-if="!f.image?.url"
          variant="outline"
          class="absolute bottom-2 left-2 text-[10px] bg-background/80"
        >
          <ImageIcon class="h-3 w-3 mr-0.5" />
          无预览
        </Badge>
      </div>
      <div class="space-y-1 p-3">
        <p class="truncate text-xs font-medium">{{ f.label || f.workflow_id }}</p>
        <p v-if="f.params?.checkpoint" class="truncate font-mono text-[10px] text-muted-foreground">
          {{ f.params.checkpoint }}
        </p>
        <p
          v-if="f.params?.loras?.length"
          class="text-[11px] text-primary/90 truncate"
        >
          {{ f.params.loras.map((l) => l.short_name || l.lora_name).join(' × ') }}
        </p>
        <p class="text-[10px] text-muted-foreground">{{ formatTime(f.created_at) }}</p>
      </div>
    </article>
  </div>
</template>
