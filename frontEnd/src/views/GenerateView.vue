<script setup>
import { computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAppStore } from '@/stores/useAppStore.js'
import { useBatchStore } from '@/stores/useBatchStore.js'
import { decodeWorkflowSnapshot, loadRestoreSnapshot } from '@/lib/workflowRestore.js'
import RunConfigShell from '@/components/run/RunConfigShell.vue'
import RunModeBar from '@/components/run/RunModeBar.vue'
import PromptModulePanel from '@/components/run/modules/PromptModulePanel.vue'
import LoraModulePanel from '@/components/run/modules/LoraModulePanel.vue'
import OtherModulePanel from '@/components/run/modules/OtherModulePanel.vue'
import GenerateActionBar from '@/components/generate/GenerateActionBar.vue'
import JobOutput from '@/components/generate/JobOutput.vue'
import BatchRunPanel from '@/components/run/BatchRunPanel.vue'
import BatchProgress from '@/components/batch/BatchProgress.vue'
import BatchPreviewTable from '@/components/batch/BatchPreviewTable.vue'
import BatchResultGrid from '@/components/batch/BatchResultGrid.vue'
import Alert from '@/components/ui/Alert.vue'

const store = useAppStore()
const batch = useBatchStore()
const route = useRoute()
const router = useRouter()

const isSweep = computed(() => route.query.mode === 'sweep')
const runDisabled = computed(() =>
  isSweep.value ? batch.isBatchRunning : store.isGenerating,
)
const batchReady = computed(() => store.selectedId && store.state.format === 'api')

onMounted(async () => {
  const restoreKey = route.query.restoreKey
  let snap = null
  if (typeof restoreKey === 'string' && restoreKey) {
    snap = loadRestoreSnapshot(restoreKey)
  }
  const restoreRaw = route.query.restore
  if (!snap && typeof restoreRaw === 'string' && restoreRaw) {
    snap = decodeWorkflowSnapshot(restoreRaw)
  }
  if (snap) {
    const ok = await store.applyWorkflowSnapshot(snap)
    if (ok) {
      const query = { workflow: store.selectedId }
      if (isSweep.value) query.mode = 'sweep'
      router.replace({ path: '/generate', query })
    }
    return
  }
  if ((restoreKey || restoreRaw) && !snap) {
    store.setMessage('无法解析工作流快照', true)
  }
  const wid = route.query.workflow
  if (typeof wid === 'string' && wid && wid !== store.selectedId) {
    await store.loadWorkflow(wid)
  } else if (!store.workflows.length) {
    await store.loadWorkflowList()
  } else if (store.selectedId && !store.state.nodes.length) {
    await store.loadWorkflow(store.selectedId)
  } else if (!store.selectedId && store.workflows.length) {
    await store.loadWorkflow(store.workflows[0].id)
  }
  if (isSweep.value) {
    batch.syncLoraAxisState()
    batch.loadBatchPromptConfig().catch(() => {})
  }
})

watch(isSweep, (sweep) => {
  if (!sweep || !store.selectedId || store.state.format !== 'api') return
  batch.syncLoraAxisState()
  batch.loadBatchPromptConfig().catch(() => {})
})
</script>

<template>
  <div class="space-y-4 pb-24">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <RunModeBar />
      <p class="text-xs text-muted-foreground max-w-xl">
        <template v-if="isSweep">开启 LoRA 扫参后按网格批量入队；未扫参的 LoRA 使用固定权重。</template>
        <template v-else>不扫参，按当前表单生成一张（等同 1×1 批量）。</template>
      </p>
    </div>

    <RunConfigShell :wide="isSweep" :loading="store.loading && !store.state.nodes.length">
      <template #default="{ activeModule }">
        <Alert v-if="!store.selectedId" variant="default">请选择工作流。</Alert>
        <Alert v-else-if="store.state.format !== 'api'" variant="default">
          仅支持 API 格式工作流。
        </Alert>
        <template v-else-if="batchReady">
          <PromptModulePanel v-show="activeModule === 'prompt'" :disabled="runDisabled" />
          <LoraModulePanel
            v-show="activeModule === 'lora'"
            :key="`lora-panel-${store.restoreEpoch}`"
            :batch-mode="isSweep"
            :disabled="runDisabled"
          />
          <OtherModulePanel v-show="activeModule === 'other'" :disabled="runDisabled" />
        </template>
      </template>
      <template v-if="batchReady" #footer>
        <BatchRunPanel v-if="isSweep" :disabled="store.loading || !store.healthOk" />
        <JobOutput v-if="!isSweep" />
      </template>
    </RunConfigShell>

    <GenerateActionBar v-if="batchReady" :sweep="isSweep" />

    <section v-if="isSweep && batchReady" class="max-w-7xl mx-auto w-full space-y-4 px-0">
      <BatchProgress />
      <BatchPreviewTable />
      <BatchResultGrid
        show-size-controls
        :initial-cell-size="160"
        @favorite-toggled="store.setMessage('收藏已更新')"
      />
    </section>

  </div>
</template>
