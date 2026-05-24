<script setup>
import { computed, ref } from 'vue'
import { api } from '@/api/client.js'
import { useAppStore } from '@/stores/useAppStore.js'
import Button from '@/components/ui/Button.vue'
import Progress from '@/components/ui/Progress.vue'
import {
  hasCivitaiApiKey,
  loadCivitaiApiKey,
} from '@/composables/useCivitaiApiKey.js'
import { FileDown, FileUp, Loader2 } from 'lucide-vue-next'
import { useConfirmDialog } from '@/composables/useConfirmDialog.js'

const app = useAppStore()
const { confirm } = useConfirmDialog()
const emit = defineEmits(['done'])

const exporting = ref(false)
const importing = ref(false)
const batchJob = ref(null)
const lastStats = ref(null)

const civitaiKey = computed(() => loadCivitaiApiKey())

const batchProgress = computed(() => {
  const j = batchJob.value
  if (!j) return 0
  if (j.status === 'completed' || j.status === 'completed_with_errors') return 100
  if (j.total > 0 && j.index > 0) {
    return Math.min(99, Math.round((j.index / j.total) * 100))
  }
  return j.progress || 5
})

const batchMessage = computed(() => batchJob.value?.message || '')

async function doExport() {
  exporting.value = true
  try {
    const res = await api.exportModelsManifest(true, true)
    lastStats.value = res.stats || null
    const path = res.savedPath || 'config/models_manifest.json'
    app.setMessage(
      `已导出清单：Checkpoint ${res.stats?.checkpoints_total ?? 0}，LoRA ${res.stats?.loras_total ?? 0}（${path}）`,
    )
    const url = api.downloadModelsManifestUrl()
    window.open(url, '_blank')
  } catch (e) {
    app.setMessage(e.message, true)
  } finally {
    exporting.value = false
  }
}

async function doImportAll() {
  if (!hasCivitaiApiKey(civitaiKey.value)) {
    app.setMessage('批量下载 Civitai 模型需先在「粘贴链接」或 C 站页配置 API Key', true)
    return
  }
  if (
    !(await confirm({
      title: '批量下载模型',
      message:
        '将按 config/models_manifest.json 批量下载缺失模型；本地已有文件会跳过。体积大、耗时长，是否继续？',
      confirmText: '开始下载',
      variant: 'default',
    }))
  ) {
    return
  }
  importing.value = true
  batchJob.value = { phase: 'pending', message: '正在启动…', progress: 0 }
  try {
    const summary = await api.importManifestAllWithProgress(
      {
        skip_existing: true,
        civitai_api_token: civitaiKey.value.trim(),
      },
      (job) => {
        batchJob.value = job
      },
    )
    const c = summary?.counts || {}
    app.setMessage(
      `批量完成：下载 ${c.downloaded ?? 0}，跳过 ${c.skipped ?? 0}，无链接 ${c.no_source ?? 0}，失败 ${c.failed ?? 0}`,
      (c.failed ?? 0) > 0,
    )
    emit('done')
  } catch (e) {
    app.setMessage(e.message, true)
  } finally {
    importing.value = false
  }
}

</script>

<template>
  <div class="flex flex-col gap-2 w-full sm:w-auto">
    <div class="flex flex-wrap items-center gap-2">
      <Button
        variant="outline"
        size="sm"
        class="gap-1.5"
        :disabled="exporting || importing"
        @click="doExport"
      >
        <Loader2 v-if="exporting" class="h-4 w-4 animate-spin" />
        <FileDown v-else class="h-4 w-4" />
        导出清单
      </Button>
      <Button
        variant="outline"
        size="sm"
        class="gap-1.5"
        :disabled="exporting || importing"
        @click="doImportAll"
      >
        <Loader2 v-if="importing" class="h-4 w-4 animate-spin" />
        <FileUp v-else class="h-4 w-4" />
        一键下载全部
      </Button>
    </div>
    <p v-if="lastStats" class="text-[10px] text-muted-foreground max-w-xs">
      上次导出：{{ lastStats.checkpoints_total }} CKPT / {{ lastStats.loras_total }} LoRA，{{
        lastStats.with_source_url
      }}
      条含 C 站链接
    </p>
    <div v-if="importing && batchJob" class="space-y-1 max-w-md">
      <Progress :model-value="batchProgress" class="h-1.5" />
      <p class="text-[10px] text-muted-foreground truncate">{{ batchMessage }}</p>
    </div>
  </div>
</template>
