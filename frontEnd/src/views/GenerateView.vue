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
import { allowsBatch, hasSingleQuotaLeft } from '@/composables/useAuth.js'

const store = useAppStore()
const batch = useBatchStore()
const route = useRoute()
const router = useRouter()

const isSweep = computed(() => allowsBatch() && route.query.mode === 'sweep')
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
  <!-- 单张 / 批量同一页面、同一内容宽度（仅 ?mode=sweep 切换逻辑，不改布局） -->
  <div class="mx-auto w-full max-w-7xl space-y-4 pb-24">
    <div class="space-y-2">
      <RunModeBar />
      <p class="min-h-10 text-xs text-muted-foreground leading-relaxed">
        <template v-if="isSweep">
          批量模式：可 LoRA 权重扫参（A×B），或不扫参时连续生成最多 12 张。
        </template>
        <template v-else>
          单张模式：按当前工作流与提示词生成一张。
          <template v-if="!allowsBatch()">
            <span v-if="hasSingleQuotaLeft()">（邀请码用户，本次登录额度内可用）</span>
            <span v-else class="text-destructive">（本次登录单图额度已用尽）</span>
          </template>
        </template>
      </p>
    </div>

    <RunConfigShell :loading="store.loading && !store.state.nodes.length">
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
        <JobOutput v-else />
      </template>
    </RunConfigShell>

    <GenerateActionBar v-if="batchReady" :sweep="isSweep" />

    <section v-if="isSweep && batchReady" class="w-full space-y-4">
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
