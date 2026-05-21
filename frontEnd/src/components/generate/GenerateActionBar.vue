<script setup>
import { computed } from 'vue'
import { Sparkles, Layers, Eye } from 'lucide-vue-next'
import { useAppStore } from '@/stores/useAppStore.js'
import { useBatchStore } from '@/stores/useBatchStore.js'
import Button from '@/components/ui/Button.vue'
import { cn } from '@/lib/utils'

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
  if (props.sweep) return batch.plannedTotal > 0 && !batch.isBatchRunning
  return !app.isGenerating
})

const showMasterHint = computed(() => app.isMasterWorkflow)
</script>

<template>
  <Teleport to="body">
    <div
      class="fixed bottom-0 left-0 right-0 z-40 flex justify-center pointer-events-none px-4 pb-4 pt-2 max-w-[100vw]"
      aria-label="生成操作栏"
    >
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

        <p
          v-else-if="showMasterHint"
          class="text-[11px] text-muted-foreground max-w-[11rem] leading-snug text-center hidden sm:block"
        >
          母版仅试跑，请到「工作流配置」复制子工作流后再保存
        </p>

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
            v-if="batch.isBatchRunning"
            variant="secondary"
            size="sm"
            @click="batch.cancelBatch"
          >
            取消
          </Button>
        </template>

        <template v-else>
          <Button
            size="lg"
            :disabled="!canGenerate"
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
        </template>
      </div>
    </div>
  </Teleport>
</template>
