<script setup>
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAppStore } from '@/stores/useAppStore.js'
import { useBatchStore } from '@/stores/useBatchStore.js'
import { useGenerateRunMode } from '@/composables/useGenerateRunMode.js'
import { decodeWorkflowSnapshot, loadRestoreSnapshot } from '@/lib/workflowRestore.js'
import RunConfigShell from '@/components/run/RunConfigShell.vue'
import PromptModulePanel from '@/components/run/modules/PromptModulePanel.vue'
import LoraModulePanel from '@/components/run/modules/LoraModulePanel.vue'
import OtherModulePanel from '@/components/run/modules/OtherModulePanel.vue'
import GenerateRunSettings from '@/components/generate/GenerateRunSettings.vue'
import GenerateActionBar from '@/components/generate/GenerateActionBar.vue'
import JobOutput from '@/components/generate/JobOutput.vue'
import BatchProgress from '@/components/batch/BatchProgress.vue'
import BatchPreviewTable from '@/components/batch/BatchPreviewTable.vue'
import BatchResultGrid from '@/components/batch/BatchResultGrid.vue'
import Alert from '@/components/ui/Alert.vue'
import { allowsBatch, hasSingleQuotaLeft } from '@/composables/useAuth.js'

const store = useAppStore()
const batch = useBatchStore()
const route = useRoute()
const router = useRouter()
const { showBatchResults, showSingleOutput } = useGenerateRunMode()

const runDisabled = computed(() => batch.isBatchRunning || store.isGenerating)
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
      router.replace({ path: '/generate', query: { workflow: store.selectedId } })
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
  if (allowsBatch() && store.selectedId && store.state.format === 'api') {
    batch.syncLoraAxisState()
    batch.loadBatchPromptConfig().catch(() => {})
  }
})
</script>

<template>
  <div class="mx-auto w-full max-w-7xl space-y-4 pb-24" data-route-stagger>
    <p class="min-h-10 text-xs text-muted-foreground leading-relaxed">
      按当前工作流与提示词生成；张数与 Seed 在下方设置，LoRA 扫参开启后张数由档位数决定。
      <template v-if="!allowsBatch()">
        <span v-if="hasSingleQuotaLeft()">（邀请码用户，本次登录额度内可用）</span>
        <span v-else class="text-destructive">（本次登录单图额度已用尽）</span>
      </template>
    </p>

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
            :batch-mode="allowsBatch()"
            :disabled="runDisabled"
          />
          <OtherModulePanel v-show="activeModule === 'other'" :disabled="runDisabled" />
        </template>
      </template>
      <template v-if="batchReady" #footer>
        <GenerateRunSettings v-if="allowsBatch()" class="mb-4" :disabled="runDisabled" />
        <JobOutput v-if="showSingleOutput" />
      </template>
    </RunConfigShell>

    <GenerateActionBar v-if="batchReady" />

    <section
      v-if="showBatchResults && batchReady"
      data-generate-status="batch"
      class="w-full space-y-4 scroll-mt-20"
    >
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
