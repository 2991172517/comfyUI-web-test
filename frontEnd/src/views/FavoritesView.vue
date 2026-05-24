<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useFavoritesPageStore } from '@/stores/useFavoritesPageStore.js'
import PageAlert from '@/components/layout/PageAlert.vue'
import FavoritesFilters from '@/components/favorites/FavoritesFilters.vue'
import FavoritesFeed from '@/components/favorites/FavoritesFeed.vue'
import FavoriteSingleDetail from '@/components/favorites/FavoriteSingleDetail.vue'
import ImageLightbox from '@/components/ImageLightbox.vue'

const route = useRoute()
const router = useRouter()
const fav = useFavoritesPageStore()
const feedLightbox = ref(null)

const inDetail = computed(() => !!fav.selected)

async function init() {
  await fav.refresh()
  await openFromQuery()
}

async function openFromQuery() {
  const id = route.query.id
  if (!id || typeof id !== 'string') return
  let f = fav.records.find((x) => x.id === id)
  if (!f) f = fav.allItems.find((x) => x.id === id)
  if (f) fav.selectFavorite(f)
}

function onPreview(f) {
  if (f?.image?.url) feedLightbox.value?.openOne(f.image.url, f.label || f.id)
}

function onPreviewUrl(url) {
  feedLightbox.value?.openOne(url)
}

function goBackToList() {
  fav.clearSelection()
  router.replace({ path: '/favorites' })
}

onMounted(init)

watch(
  () => fav.records,
  () => {
    if (route.query.id && !fav.selected) openFromQuery()
  },
)

watch(
  () => fav.selected,
  (sel) => {
    if (!sel) {
      if (route.query.id) router.replace({ path: '/favorites' })
      return
    }
    if (route.query.id !== sel.id) {
      router.replace({ path: '/favorites', query: { id: sel.id } })
    }
  },
)

watch(
  () => route.query.id,
  async (id) => {
    if (!id) {
      if (fav.selected) fav.clearSelection()
      return
    }
    if (fav.selected?.id === id) return
    await openFromQuery()
  },
)
</script>

<template>
  <div class="flex w-full min-h-0 flex-col gap-4" data-route-stagger>
    <PageAlert />

    <template v-if="!inDetail">
      <p class="text-xs text-muted-foreground px-0.5">
        每条收藏对应一张图（含批量扫参中的某一格）。点击卡片查看参数，可筛选 Checkpoint / LoRA / 工作流。
      </p>
      <FavoritesFilters />
      <FavoritesFeed @preview="onPreview" />
    </template>

    <FavoriteSingleDetail
      v-else
      @back="goBackToList"
      @preview="onPreviewUrl"
    />

    <ImageLightbox ref="feedLightbox" />
  </div>
</template>
