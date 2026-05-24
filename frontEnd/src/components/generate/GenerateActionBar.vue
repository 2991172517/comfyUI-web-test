<script setup>
import { computed, ref } from 'vue'
import { Eye, BookmarkPlus } from 'lucide-vue-next'
import { useAppStore } from '@/stores/useAppStore.js'
import { useBatchStore } from '@/stores/useBatchStore.js'
import { useGenerateRunMode } from '@/composables/useGenerateRunMode.js'
import { useGenerateWithTagFX } from '@/composables/useGenerateWithTagFX.js'
import { useConfirmDialog } from '@/composables/useConfirmDialog.js'
import { api } from '@/api/client.js'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import Label from '@/components/ui/Label.vue'
import GenerateLaunchButton from '@/components/generate/GenerateLaunchButton.vue'
import {
  allowsBatch,
  authSingleQuota,
  authSingleRemaining,
  hasSingleQuotaLeft,
} from '@/composables/useAuth.js'

const app = useAppStore()
const batch = useBatchStore()
const barRef = ref(null)
const { confirm } = useConfirmDialog()
const { usesBatchApi, generateLabel, plannedTotal } = useGenerateRunMode()

const { animating, stageMessage, generateWithFX } = useGenerateWithTagFX({
  getTargetEl: () =>
    barRef.value?.querySelector('[data-generate-main-btn]') ?? null,
})

const runDisabled = computed(() =>
  usesBatchApi.value ? batch.isBatchRunning : app.isGenerating,
)

const isRunning = computed(() =>
  usesBatchApi.value ? batch.isBatchRunning : app.isGenerating,
)

const buttonMode = computed(() => {
  if (isRunning.value && !animating.value) return 'cancel'
  if (animating.value) return 'launch'
  return 'idle'
})

const canGenerate = computed(() => {
  if (app.loading || !app.selectedId || !app.healthOk) return false
  if (usesBatchApi.value) {
    return allowsBatch() && plannedTotal.value > 0 && !batch.isBatchRunning
  }
  return !app.isGenerating && hasSingleQuotaLeft()
})

const quotaHint = computed(() => {
  void authSingleQuota.value
  void authSingleRemaining.value
  if (allowsBatch() || usesBatchApi.value) return ''
  const total = authSingleQuota.value
  const left = authSingleRemaining.value
  if (total == null || left == null) return ''
  return `剩余 ${left}/${total} 张`
})

const saveName = ref('')
const saveOpen = ref(false)
const saving = ref(false)

function openSave() {
  if (!plannedTotal.value) {
    app.setMessage('请先配置生成参数并确保计划张数 > 0', true)
    return
  }
  saveName.value = `${app.workflowMeta?.display_name || app.selectedId} · ${plannedTotal.value}张`
  saveOpen.value = true
}

async function confirmSave() {
  if (!saveName.value.trim()) return
  saving.value = true
  try {
    const body = batch.buildBatchBody()
    await api.saveBatchTask({
      name: saveName.value.trim(),
      workflow_id: app.selectedId,
      workflow_display_name: app.workflowMeta?.display_name || app.selectedId,
      planned_total: plannedTotal.value,
      batch_payload: body,
    })
    saveOpen.value = false
    app.setMessage('已保存为批量任务，可在任务计划中多选执行')
  } catch (e) {
    app.setMessage(e.message, true)
  } finally {
    saving.value = false
  }
}

async function onGenerate() {
  if (buttonMode.value !== 'idle' || !canGenerate.value) return
  await generateWithFX()
}

async function onCancel() {
  if (usesBatchApi.value) {
    if (
      !(await confirm({
        title: '取消生成',
        message: '确定取消当前任务？已完成的图片会保留。',
        confirmText: '取消任务',
        variant: 'destructive',
      }))
    ) {
      return
    }
    await batch.cancelBatch()
    return
  }
  await app.cancelWorkflow()
}

const busyLabel = computed(() => stageMessage.value || '准备中…')
</script>

<template>
  <Teleport to="body">
    <div
      ref="barRef"
      class="fixed bottom-0 left-0 right-0 z-40 flex flex-col items-center pointer-events-none px-4 pb-4 pt-2 max-w-[100vw] gap-2"
      aria-label="生成操作栏"
    >
      <div
        v-if="usesBatchApi && saveOpen"
        class="pointer-events-auto w-full max-w-md rounded-lg border border-border bg-card px-3 py-2 shadow-lg flex flex-wrap items-end gap-2"
      >
        <div class="flex-1 min-w-[10rem] space-y-1">
          <Label class="text-xs">任务名称</Label>
          <Input v-model="saveName" class="h-8 text-sm" />
        </div>
        <Button size="sm" :disabled="saving" @click="confirmSave">保存</Button>
        <Button size="sm" variant="ghost" @click="saveOpen = false">取消</Button>
      </div>

      <div
        class="pointer-events-auto flex flex-wrap items-center justify-center gap-2 sm:gap-3 rounded-2xl border border-primary/50 bg-card/95 px-3 py-2.5 sm:px-5 shadow-[0_-4px_24px_rgba(0,0,0,0.45)] backdrop-blur-md"
      >
        <Button
          v-if="!app.isMasterWorkflow"
          variant="outline"
          size="sm"
          class="shrink-0 border-border/80"
          :disabled="app.loading || !app.selectedId"
          @click="app.saveWorkflow"
        >
          保存工作流
        </Button>

        <Button
          v-if="usesBatchApi"
          variant="outline"
          size="sm"
          class="shrink-0"
          :disabled="runDisabled || !plannedTotal"
          @click="batch.previewPlan"
        >
          <Eye class="h-4 w-4" />
          预览 {{ plannedTotal || 0 }} 张
        </Button>

        <span
          v-if="quotaHint"
          class="text-xs text-muted-foreground tabular-nums shrink-0"
        >
          {{ quotaHint }}
        </span>

        <GenerateLaunchButton
          data-generate-main-btn
          :label="generateLabel"
          :busy-label="busyLabel"
          cancel-label="取消生成"
          :mode="buttonMode"
          :disabled="buttonMode === 'idle' && !canGenerate"
          :title="
            buttonMode === 'idle' && !hasSingleQuotaLeft() && !allowsBatch()
              ? '本次登录单图额度已用尽'
              : app.isMasterWorkflow
                ? '母版试跑；另存参数请在工作流配置页复制子工作流'
                : undefined
          "
          class="min-w-[8rem]"
          @generate="onGenerate"
          @cancel="onCancel"
        />

        <Button
          v-if="usesBatchApi"
          variant="outline"
          size="sm"
          class="shrink-0 gap-1"
          :disabled="runDisabled || !plannedTotal || saving"
          @click="openSave"
        >
          <BookmarkPlus class="h-4 w-4" />
          保存为任务
        </Button>
      </div>
    </div>
  </Teleport>
</template>
