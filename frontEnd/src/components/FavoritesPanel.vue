<script setup>
import { onMounted, ref } from 'vue'
import ImageLightbox from '@/components/ImageLightbox.vue'
import Card from '@/components/ui/Card.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import CardTitle from '@/components/ui/CardTitle.vue'
import CardContent from '@/components/ui/CardContent.vue'
import Button from '@/components/ui/Button.vue'
import Badge from '@/components/ui/Badge.vue'
import { api } from '@/api/client.js'
import { useAppStore } from '@/stores/useAppStore.js'
import { useFavorites } from '@/composables/useFavorites.js'
import { favoriteEntryToTogglePayload } from '@/lib/favoriteToggle.js'

const emit = defineEmits(['apply'])

const app = useAppStore()
const favorites = ref([])
const loading = ref(false)
const lightboxRef = ref(null)
const { refreshFavorites } = useFavorites()

async function load() {
  loading.value = true
  try {
    favorites.value = await refreshFavorites()
  } catch (e) {
    app.setMessage(e.message, true)
  } finally {
    loading.value = false
  }
}

function applyToWorkflow(fav) {
  emit('apply', fav)
}

async function remove(id) {
  if (!confirm('取消收藏？（仅删除记录，不删原图）')) return
  const entry = favorites.value.find((f) => f.id === id)
  const body = favoriteEntryToTogglePayload(entry)
  if (!body?.image?.filename) {
    app.setMessage('无法取消收藏：缺少图片信息', true)
    return
  }
  try {
    await api.toggleFavorite(body)
    await load()
    app.setMessage('已取消收藏')
  } catch (e) {
    app.setMessage(e.message, true)
  }
}

function openPreview(index) {
  const list = favorites.value.map((f) => ({
    url: f.image?.url,
    title: f.label || f.params?.checkpoint || f.id,
  }))
  lightboxRef.value?.open(list, index)
}

function formatLoras(params) {
  const loras = params?.loras || []
  return loras
    .map(
      (l) =>
        `${l.short_name || l.lora_name}: m${l.strength_model} c${l.strength_clip}`,
    )
    .join(' · ')
}

onMounted(load)

defineExpose({ load })
</script>

<template>
  <Card>
    <CardHeader class="flex flex-row items-center justify-between space-y-0 pb-2">
      <CardTitle class="text-base">收藏</CardTitle>
      <Button variant="outline" size="sm" :disabled="loading" @click="load">
        {{ loading ? '加载中…' : '刷新' }}
      </Button>
    </CardHeader>
    <CardContent class="space-y-4">
      <p class="text-sm text-muted-foreground">
        仅保存参数到 <code class="rounded bg-muted px-1">favorites.json</code>（不复制图片）。点击「用此配置生成」会跳转到抽卡页并加载参数。
      </p>
      <p v-if="loading" class="text-sm text-muted-foreground">加载中…</p>
      <p v-else-if="!favorites.length" class="text-sm text-muted-foreground">
        暂无收藏，在生成结果或批量网格点击 ☆ 收藏。
      </p>
      <div v-else class="grid gap-4 sm:grid-cols-2">
        <article
          v-for="(fav, idx) in favorites"
          :key="fav.id"
          class="flex gap-3 rounded-lg border border-border bg-background p-3"
        >
          <div
            class="h-24 w-24 shrink-0 cursor-zoom-in overflow-hidden rounded-md bg-black/40"
            @click="fav.image?.url && openPreview(idx)"
          >
            <img
              v-if="fav.image?.url"
              :src="fav.image.url"
              class="h-full w-full object-cover"
              loading="lazy"
            />
            <span v-else class="flex h-full items-center justify-center p-2 text-center text-xs text-muted-foreground">
              原图已删除
            </span>
          </div>
          <div class="min-w-0 flex-1 space-y-1.5 text-sm">
            <div class="truncate font-medium">{{ fav.label || fav.workflow_id }}</div>
            <div class="flex flex-wrap gap-1">
              <Badge v-if="fav.params?.checkpoint" variant="secondary" class="text-xs">
                CKPT: {{ fav.params.checkpoint }}
              </Badge>
              <Badge v-if="fav.params?.seed != null" variant="outline" class="text-xs">
                seed: {{ fav.params.seed }}
              </Badge>
            </div>
            <p v-if="formatLoras(fav.params)" class="text-xs text-primary/90">
              {{ formatLoras(fav.params) }}
            </p>
            <p class="text-xs text-muted-foreground">
              {{ fav.created_at?.slice(0, 19).replace('T', ' ') }}
            </p>
            <div class="flex flex-wrap gap-2 pt-1">
              <Button size="sm" @click="applyToWorkflow(fav)">用此配置生成</Button>
              <Button variant="destructive" size="sm" @click="remove(fav.id)">取消收藏</Button>
            </div>
          </div>
        </article>
      </div>
    </CardContent>
    <ImageLightbox ref="lightboxRef" />
  </Card>
</template>
