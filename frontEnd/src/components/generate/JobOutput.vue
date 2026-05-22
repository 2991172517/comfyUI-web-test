<script setup>
import { ref } from 'vue'
import { watch } from 'vue'
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
import ImageLightbox from '@/components/ImageLightbox.vue'
import { isAdmin } from '@/composables/useAuth.js'

const store = useAppStore()
const history = useHistoryStore()
const imageLightboxRef = ref(null)
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

function openJobImagePreview(index) {
  const list = store.job.images.map((img) => ({
    url: img.url,
    title: img.filename,
  }))
  imageLightboxRef.value?.open(list, index)
}

function downloadImage(img) {
  saveOne(img)
}

function downloadAllImages() {
  saveAll(store.job.images)
}

async function onFavoriteToggled() {
  await refreshFavorites()
}
</script>

<template>
  <Card v-if="store.job.status !== 'idle'" class="mb-6">
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
      <p v-if="store.job.promptId" class="text-sm text-muted-foreground">
        任务 ID: {{ store.job.promptId }}
      </p>
      <p v-if="store.job.currentNode" class="text-sm text-muted-foreground">
        当前节点: #{{ store.job.currentNode }}
      </p>
      <p v-if="store.job.message" class="text-sm text-muted-foreground">{{ store.job.message }}</p>

      <div
        v-if="store.progressPercent != null && store.isGenerating"
        class="relative h-2 overflow-hidden rounded-full bg-secondary"
      >
        <div
          class="h-full bg-primary transition-all duration-300"
          :style="{ width: store.progressPercent + '%' }"
        />
        <span class="absolute right-0 -top-5 text-xs text-muted-foreground">
          {{ store.progressPercent }}%
        </span>
      </div>
      <p v-else-if="store.isGenerating" class="flex items-center gap-2 text-sm text-muted-foreground">
        <span
          class="inline-block h-4 w-4 animate-spin rounded-full border-2 border-muted-foreground border-t-primary"
        />
        正在执行工作流…
      </p>

      <div v-if="store.job.images.length" class="space-y-3 border-t border-border pt-4">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <h4 class="text-sm font-medium">生成结果（{{ store.job.images.length }}）</h4>
          <div class="flex gap-2">
            <Button variant="outline" size="sm" @click="downloadAllImages">全部保存</Button>
            <Button
              v-if="isAdmin()"
              variant="destructive"
              size="sm"
              @click="store.deleteOutputs"
            >
              删除服务器图片
            </Button>
          </div>
        </div>
        <div class="grid gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
          <figure
            v-for="(img, idx) in store.job.images"
            :key="img.id"
            class="overflow-hidden rounded-lg border border-border bg-background"
          >
            <div class="relative">
              <FavoriteStar
                :payload="singleFavoritePayload(img)"
                size="small"
                class="absolute right-2 top-2 z-10"
                @toggled="onFavoriteToggled"
              />
              <img
                :src="img.url"
                :alt="img.filename"
                loading="lazy"
                class="aspect-square w-full cursor-zoom-in object-contain bg-black/40 hover:opacity-90"
                title="点击查看大图"
                @click="openJobImagePreview(idx)"
              />
            </div>
            <figcaption class="flex items-center justify-between gap-2 p-2 text-xs">
              <span class="truncate text-muted-foreground" :title="img.filename">{{
                img.filename
              }}</span>
              <Button variant="ghost" size="sm" @click="downloadImage(img)">保存</Button>
            </figcaption>
          </figure>
        </div>
      </div>
    </CardContent>
  </Card>
  <ImageLightbox ref="imageLightboxRef" />
</template>
