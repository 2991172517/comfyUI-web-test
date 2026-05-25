<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAppStore } from '@/stores/useAppStore.js'
import { useBatchStore } from '@/stores/useBatchStore.js'
import { useGenerateRunMode } from '@/composables/useGenerateRunMode.js'
import { useWorkflowRunCategory } from '@/composables/useWorkflowRunCategory.js'
import { decodeWorkflowSnapshot, loadRestoreSnapshot } from '@/lib/workflowRestore.js'
import { provideInpaintStore } from '@/stores/useInpaintStore.js'
import { provideUpscaleStore } from '@/stores/useUpscaleStore.js'
import RunConfigShell from '@/components/run/RunConfigShell.vue'
import WorkflowRunHeader from '@/components/run/WorkflowRunHeader.vue'
import InpaintRunBody from '@/components/run/InpaintRunBody.vue'
import UpscaleRunBody from '@/components/run/UpscaleRunBody.vue'
import PromptModulePanel from '@/components/run/modules/PromptModulePanel.vue'
import LoraModulePanel from '@/components/run/modules/LoraModulePanel.vue'
import OtherModulePanel from '@/components/run/modules/OtherModulePanel.vue'
import PreviewModulePanel from '@/components/run/modules/PreviewModulePanel.vue'
import GenerateRunSettings from '@/components/generate/GenerateRunSettings.vue'
import GenerateActionBar from '@/components/generate/GenerateActionBar.vue'
import JobOutput from '@/components/generate/JobOutput.vue'
import BatchProgress from '@/components/batch/BatchProgress.vue'
import BatchResultGrid from '@/components/batch/BatchResultGrid.vue'
import Alert from '@/components/ui/Alert.vue'
import { api } from '@/api/client.js'
import { allowsBatch, hasSingleQuotaLeft } from '@/composables/useAuth.js'

const store = useAppStore()
const batch = useBatchStore()
const route = useRoute()
const router = useRouter()
const { showBatchResults, showSingleOutput } = useGenerateRunMode()
const { isInpaint, isUpscale, isGenerateLike, categoryLabel } = useWorkflowRunCategory()

const inpaint = provideInpaintStore()
provideUpscaleStore()

const healthOk = ref(false)

const runDisabled = computed(() => batch.isBatchRunning || store.isGenerating)
const batchReady = computed(() => store.selectedId && store.state.format === 'api')

const pageIntro = computed(() => {
  if (isInpaint.value) {
    return '当前为局部重绘工作流：上传原图、涂抹蒙版后生成。与文生图批量流程独立。'
  }
  if (isUpscale.value) {
    return '当前为高清放大工作流：上传成图后 RTX 超分放大，不修改提示词。'
  }
  return '按当前工作流与提示词生成；张数与 Seed 在下方设置，LoRA 扫参开启后张数由档位数决定。LoRA 增删与顺序仅对本次生成生效。'
})

function afterWorkflowReady() {
  if (!isGenerateLike.value) {
    syncSpecializedFromStore()
    return
  }
  store.initSessionLoraChain()
  if (allowsBatch()) {
    batch.syncLoraAxisState()
    batch.loadBatchPromptConfig().catch(() => {})
  }
}

function syncSpecializedFromStore() {
  const bp = store.sessionPrompts
  if (isInpaint.value) {
    if (bp.positive) inpaint.positive = bp.positive
    if (bp.negative) inpaint.negative = bp.negative
    const ckpt = store.overrides?.['1']?.ckpt_name || store.overrides?.['1']?.ckpt
    if (ckpt) inpaint.checkpoint = String(ckpt)
    if (store.overrides?.['30']?.seed != null) {
      inpaint.seed = Number(store.overrides['30'].seed)
    }
    inpaint.bootstrapSourceWorkflowId = store.temporaryWorkflowHint || store.selectedId || ''
  }
}

watch(
  () => store.selectedId,
  (id, prev) => {
    if (id && id !== prev) {
      if (isGenerateLike.value && store.state.format === 'api' && store.state.nodes.length) {
        afterWorkflowReady()
      } else if (!isGenerateLike.value) {
        afterWorkflowReady()
      }
    }
  },
)

watch(
  () => [store.restoreEpoch, store.selectedId, isInpaint.value],
  () => syncSpecializedFromStore(),
)

onMounted(async () => {
  try {
    const h = await api.health()
    healthOk.value = !!h.ok
    if (h.ok) await store.loadModelLists().catch(() => {})
  } catch {
    healthOk.value = false
  }

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
      afterWorkflowReady()
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
    const pick =
      store.workflows.find((w) => w.category === 'generate') || store.workflows[0]
    await store.loadWorkflow(pick.id)
  }
  afterWorkflowReady()
})
</script>

<template>
  <div class="mx-auto w-full max-w-7xl space-y-4 pb-24" data-route-stagger>
    <p class="min-h-10 text-xs text-muted-foreground leading-relaxed">
      {{ pageIntro }}
      <span class="ml-1 text-foreground/70">（{{ categoryLabel }}）</span>
      <template v-if="!allowsBatch()">
        <span v-if="hasSingleQuotaLeft()">（邀请码用户，本次登录额度内可用）</span>
        <span v-else class="text-destructive">（本次登录单图额度已用尽）</span>
      </template>
    </p>

    <WorkflowRunHeader />

    <InpaintRunBody v-if="isInpaint" :health-ok="healthOk" />

    <UpscaleRunBody v-else-if="isUpscale" :health-ok="healthOk" />

    <template v-else>
      <RunConfigShell :show-header="false" :loading="store.loading && !store.state.nodes.length">
        <template #default="{ activeModule }">
          <Alert v-if="!store.selectedId" variant="default">请选择工作流。</Alert>
          <Alert v-else-if="store.state.format !== 'api'" variant="default">
            仅支持 API 格式工作流。
          </Alert>
          <template v-else-if="batchReady">
            <PromptModulePanel v-if="activeModule === 'prompt'" :disabled="runDisabled" />
            <LoraModulePanel
              v-else-if="activeModule === 'lora'"
              session-only
              manage-chain
              reorderable
              :batch-mode="allowsBatch()"
              :disabled="runDisabled"
            />
            <OtherModulePanel v-else-if="activeModule === 'other'" :disabled="runDisabled" />
            <PreviewModulePanel v-else-if="activeModule === 'preview'" :disabled="runDisabled" />
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
        <BatchResultGrid
          show-size-controls
          @favorite-toggled="store.setMessage('收藏已更新')"
        />
      </section>
    </template>
  </div>
</template>
