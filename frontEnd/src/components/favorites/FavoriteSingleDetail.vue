<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useFavoritesPageStore } from '@/stores/useFavoritesPageStore.js'
import { useAppStore } from '@/stores/useAppStore.js'
import { favoriteSourceLabel, favoriteToDetailMeta, isFromBatchGrid } from '@/lib/favoriteMeta.js'
import HistoryMetaPanel from '@/components/history/HistoryMetaPanel.vue'
import HistoryImageDetailModal from '@/components/history/HistoryImageDetailModal.vue'
import Button from '@/components/ui/Button.vue'
import Badge from '@/components/ui/Badge.vue'
import IconDeleteButton from '@/components/ui/IconDeleteButton.vue'
import { api } from '@/api/client.js'
import { ArrowLeft, Star } from 'lucide-vue-next'

const emit = defineEmits(['back', 'preview'])

const fav = useFavoritesPageStore()
const app = useAppStore()
const router = useRouter()

const entry = computed(() => fav.selected)
const detailMeta = computed(() => (entry.value ? favoriteToDetailMeta(entry.value) : null))
const detailOpen = ref(false)

async function applyGenerate() {
  if (!entry.value) return
  const ok = await app.applyFavorite(entry.value)
  if (ok) router.push('/generate')
}

async function removeFavorite() {
  if (!entry.value) return
  if (!confirm('取消收藏？')) return
  try {
    await api.deleteFavorite(entry.value.id)
    fav.removeFromList(entry.value.id)
    app.setMessage('已取消收藏')
    emit('back')
  } catch (e) {
    app.setMessage(e.message, true)
  }
}
</script>

<template>
  <div v-if="entry" class="flex w-full flex-col gap-4">
    <Button variant="outline" size="sm" class="w-fit gap-1.5" @click="emit('back')">
      <ArrowLeft class="h-4 w-4" />
      返回列表
    </Button>

    <div
      class="rounded-xl border-2 border-amber-500/35 bg-gradient-to-br from-amber-500/8 to-transparent p-4 md:p-6"
    >
      <div class="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <Badge
            :class="
              isFromBatchGrid(entry)
                ? 'mb-2 gap-1 border-0 bg-violet-600 text-white'
                : 'mb-2 gap-1 border-0 bg-amber-600 text-white'
            "
          >
            {{ favoriteSourceLabel(entry) }}
          </Badge>
          <p class="text-sm font-medium">{{ entry.label || entry.workflow_id }}</p>
          <p class="font-mono text-xs text-muted-foreground">{{ entry.id }}</p>
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <Button variant="outline" size="sm" @click="detailOpen = true">参数详情</Button>
          <Button size="sm" @click="applyGenerate">以此配置生成</Button>
          <IconDeleteButton title="取消收藏" @click="removeFavorite" />
        </div>
      </div>

      <div class="grid gap-6 lg:grid-cols-[minmax(260px,1fr)_minmax(280px,1.2fr)]">
        <div
          v-if="entry.image?.url"
          class="relative flex min-h-[240px] items-center justify-center rounded-lg border border-border bg-muted/25 p-3"
        >
          <img
            :src="entry.image.url"
            class="max-h-[min(72vh,900px)] max-w-full cursor-zoom-in object-contain"
            @click="emit('preview', entry.image.url)"
          />
        </div>
        <div
          v-else
          class="flex min-h-[200px] items-center justify-center rounded-lg border border-dashed text-sm text-muted-foreground"
        >
          原图文件已不存在
        </div>
        <HistoryMetaPanel :meta="detailMeta" :workflow-id="entry.workflow_id" />
      </div>
    </div>

    <HistoryImageDetailModal
      :open="detailOpen"
      :meta="detailMeta"
      :image-url="entry.image?.url || ''"
      title="收藏参数详情"
      @close="detailOpen = false"
    />
  </div>
</template>
