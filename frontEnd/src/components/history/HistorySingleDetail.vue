<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useHistoryStore } from '@/stores/useHistoryStore.js'
import { useAppStore } from '@/stores/useAppStore.js'
import { encodeWorkflowSnapshot, persistRestoreSnapshot } from '@/lib/workflowRestore.js'
import HistoryMetaPanel from '@/components/history/HistoryMetaPanel.vue'
import HistoryImageDetailModal from '@/components/history/HistoryImageDetailModal.vue'
import Button from '@/components/ui/Button.vue'
import Badge from '@/components/ui/Badge.vue'
import FavoriteStar from '@/components/FavoriteStar.vue'
import { buildSingleFavoritePayload } from '@/utils/favoritePayload.js'
import { ArrowLeft } from 'lucide-vue-next'

const emit = defineEmits(['back', 'preview', 'deleted'])

const history = useHistoryStore()
const app = useAppStore()
const router = useRouter()
const deleting = ref(false)

const entry = computed(() => history.singleDetail)
const img = computed(() => entry.value?.images?.[0])
const detailOpen = ref(false)

const detailMeta = computed(() => {
  const e = entry.value
  if (!e?.meta) return null
  return {
    ...e.meta,
    workflow_id: e.workflow_id || e.workflow_snapshot?.workflow_id,
  }
})

function regenerate() {
  const snap = entry.value?.workflow_snapshot
  if (!snap?.workflow_id) return
  const restoreKey = persistRestoreSnapshot(entry.value.prompt_id, 0, snap)
  const query = { workflow: snap.workflow_id }
  if (restoreKey) query.restoreKey = restoreKey
  const encoded = encodeWorkflowSnapshot(snap)
  if (encoded && encoded.length < 2400) query.restore = encoded
  router.push({ path: '/generate', query })
}

function favPayload() {
  if (!img.value) return null
  return buildSingleFavoritePayload(
    entry.value.workflow_id,
    img.value,
    entry.value.workflow_snapshot?.overrides || {},
    entry.value.prompt_id,
  )
}

async function removeRecord() {
  const pid = entry.value?.prompt_id
  if (!pid) return
  if (!confirm('删除该单抽记录？图片文件将一并移除。')) return
  deleting.value = true
  try {
    await history.deleteSingle(pid)
    app.setMessage('已删除单抽记录')
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
      加载中…
    </div>

    <div
      v-else-if="entry"
      class="rounded-xl border-2 border-sky-500/35 bg-gradient-to-br from-sky-500/8 to-transparent p-4 md:p-6"
    >
      <div class="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <Badge class="mb-2 border-0 bg-sky-600 text-white">单抽</Badge>
          <p class="font-mono text-xs text-muted-foreground">{{ entry.prompt_id }}</p>
        </div>
        <div class="flex flex-wrap gap-2">
          <Button variant="outline" size="sm" @click="detailOpen = true">详情</Button>
          <Button size="sm" @click="regenerate">以此生成</Button>
          <Button
            variant="destructive"
            size="sm"
            :disabled="deleting"
            @click="removeRecord"
          >
            {{ deleting ? '删除中…' : '删除记录' }}
          </Button>
        </div>
      </div>

      <div class="grid gap-6 lg:grid-cols-[minmax(260px,1fr)_minmax(280px,1.2fr)]">
        <div
          v-if="img?.url"
          class="relative flex min-h-[240px] items-center justify-center rounded-lg border border-border bg-muted/25 p-3"
        >
          <img
            :src="img.url"
            class="max-h-[min(72vh,900px)] max-w-full cursor-zoom-in object-contain"
            @click="emit('preview', img.url)"
          />
          <FavoriteStar
            v-if="favPayload()"
            :payload="favPayload()"
            class="absolute right-2 top-2"
          />
        </div>
        <HistoryMetaPanel :meta="entry.meta" :workflow-id="entry.workflow_id" />
      </div>
    </div>

    <HistoryImageDetailModal
      :open="detailOpen"
      :meta="detailMeta"
      :image-url="img?.url || ''"
      title="单抽生成参数"
      @close="detailOpen = false"
    />
  </div>
</template>
