<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useHistoryStore } from '@/stores/useHistoryStore.js'
import PageAlert from '@/components/layout/PageAlert.vue'
import HistoryFilters from '@/components/history/HistoryFilters.vue'
import HistoryFeed from '@/components/history/HistoryFeed.vue'
import HistoryBatchDetail from '@/components/history/HistoryBatchDetail.vue'
import HistorySingleDetail from '@/components/history/HistorySingleDetail.vue'
import ImageLightbox from '@/components/ImageLightbox.vue'

const route = useRoute()
const router = useRouter()
const history = useHistoryStore()
const feedLightbox = ref(null)

const inDetail = computed(() => !!history.selected)

async function init() {
  await history.loadFilterOptions()
  await history.refresh()
  await openFromQuery()
}

async function openFromQuery() {
  const id = route.query.id
  let type = route.query.type
  if (!id || typeof id !== 'string') return
  if (!type) {
    const found = history.records.find(
      (r) => r.id === id || r.batch_id === id || r.prompt_id === id,
    )
    type = found?.type || 'batch'
  }
  let rec = history.records.find(
    (r) => (type === 'batch' ? r.batch_id : r.prompt_id) === id || r.id === id,
  )
  if (!rec) {
    rec =
      type === 'batch'
        ? { type: 'batch', batch_id: id, id }
        : { type: 'single', prompt_id: id, id }
  }
  await history.selectRecord(rec)
}

function onPreviewSingle(rec) {
  const url = rec.thumbnail_url || rec.images?.[0]?.url
  if (url) feedLightbox.value?.openOne(url, rec.prompt_id)
}

function onPreviewSingleDetail(url) {
  feedLightbox.value?.openOne(url)
}

function goBackToList() {
  history.clearSelection()
  router.replace({ path: '/history' })
}

onMounted(init)
watch(() => [route.query.id, route.query.type], async () => {
  if (!route.query.id) {
    if (history.selected) history.clearSelection()
    return
  }
  const sid = history.selected
    ? history.selected.type === 'batch'
      ? history.selected.batch_id
      : history.selected.prompt_id
    : null
  if (route.query.id === sid) return
  await openFromQuery()
})

watch(
  () => history.selected,
  (sel) => {
    if (!sel) {
      if (route.query.id) router.replace({ path: '/history' })
      return
    }
    const q = {
      id: sel.type === 'batch' ? sel.batch_id || sel.id : sel.prompt_id || sel.id,
      type: sel.type,
    }
    if (route.query.id !== q.id || route.query.type !== q.type) {
      router.replace({ path: '/history', query: q })
    }
  },
)
</script>

<template>
  <div class="flex w-full min-h-0 flex-col gap-4">
    <PageAlert />

    <!-- 列表视图：时间线卡片 -->
    <template v-if="!inDetail">
      <HistoryFilters />
      <HistoryFeed @preview-single="onPreviewSingle" />
    </template>

    <!-- 详情视图：整页切换，不再在列表下方展开 -->
    <template v-else>
      <HistoryBatchDetail
        v-if="history.selected?.type === 'batch'"
        @back="goBackToList"
        @deleted="goBackToList"
      />
      <HistorySingleDetail
        v-else-if="history.selected?.type === 'single'"
        @back="goBackToList"
        @preview="onPreviewSingleDetail"
        @deleted="goBackToList"
      />
    </template>

    <ImageLightbox ref="feedLightbox" />
  </div>
</template>
