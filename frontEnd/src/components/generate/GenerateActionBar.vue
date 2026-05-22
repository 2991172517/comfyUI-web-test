<script setup>
import { computed, ref } from 'vue'
import { Sparkles, Layers, Eye, BookmarkPlus } from 'lucide-vue-next'
import { useAppStore } from '@/stores/useAppStore.js'
import { useBatchStore } from '@/stores/useBatchStore.js'
import { api } from '@/api/client.js'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import Label from '@/components/ui/Label.vue'
import { cn } from '@/lib/utils'
import {
  allowsBatch,
  authSingleQuota,
  authSingleRemaining,
  hasSingleQuotaLeft,
} from '@/composables/useAuth.js'

const props = defineProps({
  sweep: { type: Boolean, default: false },
})

const app = useAppStore()
const batch = useBatchStore()

const runDisabled = computed(() =>
  props.sweep ? batch.isBatchRunning : app.isGenerating,
)

const canGenerate = computed(() => {
  if (app.loading || !app.selectedId || !app.healthOk) return false
  if (props.sweep) return allowsBatch() && batch.plannedTotal > 0 && !batch.isBatchRunning
  return !app.isGenerating && hasSingleQuotaLeft()
})

const quotaHint = computed(() => {
  void authSingleQuota.value
  void authSingleRemaining.value
  if (allowsBatch() || props.sweep) return ''
  const total = authSingleQuota.value
  const left = authSingleRemaining.value
  if (total == null || left == null) return ''
  return `剩余 ${left}/${total} 张`
})

const saveName = ref('')
const saveOpen = ref(false)
const saving = ref(false)

function openSave() {
  if (!batch.plannedTotal) {
    app.setMessage('请先配置批量参数并确保计划张数 > 0', true)
    return
  }
  saveName.value = `${app.workflowMeta?.display_name || app.selectedId} · ${batch.plannedTotal}张`
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
      planned_total: batch.plannedTotal,
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
</script>

<template>
  <Teleport to="body">
    <div
      class="fixed bottom-0 left-0 right-0 z-40 flex flex-col items-center pointer-events-none px-4 pb-4 pt-2 max-w-[100vw] gap-2"
      aria-label="生成操作栏"
    >
      <div
        v-if="sweep && saveOpen"
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

        <template v-if="sweep">
          <Button
            variant="outline"
            size="sm"
            class="shrink-0"
            :disabled="runDisabled || !batch.plannedTotal"
            @click="batch.previewPlan"
          >
            <Eye class="h-4 w-4" />
            预览 {{ batch.plannedTotal || 0 }} 张
          </Button>
          <Button
            size="lg"
            :disabled="!canGenerate"
            :class="
              cn(
                'h-12 min-w-[10rem] px-8 text-base font-semibold shadow-lg',
                'bg-primary hover:bg-primary/90 ring-2 ring-primary/40',
              )
            "
            @click="batch.startBatch"
          >
            <Layers class="h-5 w-5 shrink-0" />
            {{ batch.isBatchRunning ? '批量进行中…' : '开始批量' }}
          </Button>
          <Button
            variant="outline"
            size="sm"
            class="shrink-0 gap-1"
            :disabled="runDisabled || !batch.plannedTotal || saving"
            @click="openSave"
          >
            <BookmarkPlus class="h-4 w-4" />
            保存为任务
          </Button>
          <Button
            v-if="batch.isBatchRunning"
            variant="secondary"
            size="sm"
            class="shrink-0"
            @click="batch.cancelBatch"
          >
            取消批量
          </Button>
        </template>

        <template v-else>
          <span
            v-if="quotaHint"
            class="text-xs text-muted-foreground tabular-nums shrink-0"
          >
            {{ quotaHint }}
          </span>
          <Button
            size="lg"
            :disabled="!canGenerate"
            :title="
              !hasSingleQuotaLeft() && !allowsBatch()
                ? '本次登录单图额度已用尽'
                : app.isMasterWorkflow
                  ? '母版试跑；另存参数请在工作流配置页复制子工作流'
                  : undefined
            "
            :class="
              cn(
                'h-12 min-w-[11rem] px-10 text-base font-semibold shadow-lg',
                'bg-primary hover:bg-primary/90 ring-2 ring-primary/40',
              )
            "
            @click="app.queueWorkflow"
          >
            <Sparkles class="h-5 w-5 shrink-0" />
            {{ app.isGenerating ? '生成中…' : '生成一张' }}
          </Button>
          <Button
            v-if="app.isGenerating"
            variant="secondary"
            size="sm"
            class="shrink-0"
            @click="app.cancelWorkflow"
          >
            取消生成
          </Button>
        </template>
      </div>
    </div>
  </Teleport>
</template>
