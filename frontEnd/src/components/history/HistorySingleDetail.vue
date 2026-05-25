<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useHistoryStore } from '@/stores/useHistoryStore.js'
import { useAppStore } from '@/stores/useAppStore.js'
import { buildRegenerateRestoreRoute } from '@/lib/regenerateFromImage.js'
import HistoryMetaPanel from '@/components/history/HistoryMetaPanel.vue'
import HistoryImageDetailModal from '@/components/history/HistoryImageDetailModal.vue'
import Button from '@/components/ui/Button.vue'
import Badge from '@/components/ui/Badge.vue'
import FavoriteStar from '@/components/FavoriteStar.vue'
import ImageMagnifierPreview from '@/components/media/ImageMagnifierPreview.vue'
import { buildSingleFavoritePayload } from '@/utils/favoritePayload.js'
import { ArrowLeft } from 'lucide-vue-next'
import { isAdmin } from '@/composables/useAuth.js'
import { useImageDownload } from '@/composables/useImageDownload.js'
import { useConfirmDialog } from '@/composables/useConfirmDialog.js'

const emit = defineEmits(['back', 'preview', 'deleted'])

const history = useHistoryStore()
const { confirmDelete } = useConfirmDialog()
const app = useAppStore()
const router = useRouter()
const deleting = ref(false)
const { saveOne } = useImageDownload()

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

async function regenerate() {
  const e = entry.value
  if (!e) return
  try {
    const route = await buildRegenerateRestoreRoute({
      cell: {
        images: e.images,
        workflow_snapshot: e.workflow_snapshot,
        overrides: e.overrides,
        index: 0,
        seed: e.meta?.sampler?.seed,
      },
      runConfig: { workflow_id: e.workflow_id },
      batchId: e.prompt_id,
      cellIndex: 0,
    })
    if (!route) {
      app.setMessage('缺少工作流信息，无法恢复', true)
      return
    }
    if (route.message) app.setMessage(route.message)
    router.push({ path: '/generate', query: route.query })
  } catch (err) {
    app.setMessage(err.message || '无法从图片恢复工作流', true)
  }
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
    emit('deleted')
  } catch (e) {
    app.setMessage(e.message, true)
  } finally {
    deleting.value = false
  }
}

function openDetailModal(ev) {
  if (ev.target.closest('button, textarea, input, a, select, label')) return
  detailOpen.value = true
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
          <Button
            v-if="img?.url"
            variant="outline"
            size="sm"
            @click="saveOne(img)"
          >
            保存
          </Button>
          <Button size="sm" @click="regenerate">以此生成</Button>
          <Button
            v-if="isAdmin()"
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
          class="relative flex min-h-[240px] cursor-zoom-in items-center justify-center rounded-lg border border-border bg-muted/25"
          @click="emit('preview', img.url)"
        >
          <ImageMagnifierPreview
            fill
            :src="img.url"
            :lens-size="220"
            :zoom="2.2"
          />
          <FavoriteStar
            v-if="favPayload()"
            :payload="favPayload()"
            class="absolute right-2 top-2 z-10"
          />
        </div>
        <div
          class="cursor-pointer rounded-lg transition-colors hover:bg-accent/30"
          @click="openDetailModal"
        >
          <HistoryMetaPanel :meta="entry.meta" :workflow-id="entry.workflow_id" />
        </div>
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
