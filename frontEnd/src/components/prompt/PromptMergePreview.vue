<script setup>
import { ref, watch } from 'vue'
import { ChevronDown } from 'lucide-vue-next'
import { api } from '@/api/client.js'
import { globalPromptRevision } from '@/composables/useGlobalPromptQuick.js'
import { serializePromptConfig } from '@/composables/usePromptConfig.js'
import Label from '@/components/ui/Label.vue'
import Button from '@/components/ui/Button.vue'
import PromptMergeSegmentBlocks from '@/components/prompt/PromptMergeSegmentBlocks.vue'
import { cn } from '@/lib/utils'

const props = defineProps({
  workflowId: { type: String, required: true },
  overrides: { type: Object, default: () => ({}) },
  promptConfig: { type: Object, default: null },
  styleEnabled: { type: Boolean, default: null },
  promptSeed: { type: Number, default: null },
  defaultExpanded: { type: Boolean, default: false },
})

const expanded = ref(props.defaultExpanded)
const loading = ref(false)
const positive = ref('')
const negative = ref('')
const segments = ref({ positive: [], negative: [] })
const debug = ref(null)
const hasLoaded = ref(false)

async function refresh() {
  if (!props.workflowId) return
  loading.value = true
  try {
    const res = await api.previewPromptMerge({
      workflow_id: props.workflowId,
      overrides: props.overrides,
      style_enabled: props.styleEnabled,
      batch_prompts: props.promptConfig ? serializePromptConfig(props.promptConfig) : null,
      prompt_seed: props.promptSeed,
      prompt_global_priority: props.promptConfig?.merge?.random_before_workflow ?? false,
    })
    positive.value = res.positive || ''
    negative.value = res.negative || ''
    segments.value = res.segments || { positive: [], negative: [] }
    debug.value = res.merge_debug || null
    hasLoaded.value = true
  } catch {
    positive.value = ''
    negative.value = ''
    segments.value = { positive: [], negative: [] }
  } finally {
    loading.value = false
  }
}

function toggleExpanded() {
  expanded.value = !expanded.value
  if (expanded.value && !hasLoaded.value && !loading.value) {
    refresh()
  }
}

watch(
  () => [
    props.workflowId,
    props.overrides,
    props.promptConfig,
    props.styleEnabled,
    props.promptSeed,
    globalPromptRevision.value,
  ],
  () => {
    if (expanded.value) refresh()
    else hasLoaded.value = false
  },
  { deep: true },
)

defineExpose({ refresh })
</script>

<template>
  <div class="rounded-lg border border-dashed border-primary/35 bg-primary/5 overflow-hidden">
    <button
      type="button"
      class="flex w-full items-center justify-between gap-2 px-3 py-2.5 text-left hover:bg-primary/10 transition-colors"
      :aria-expanded="expanded"
      @click="toggleExpanded"
    >
      <div class="min-w-0">
        <Label class="text-xs font-medium pointer-events-none">合并预览（将提交给 ComfyUI）</Label>
        <p v-if="!expanded" class="text-[10px] text-muted-foreground mt-0.5 truncate">
          点击展开查看全局 / 随机 / 工作流合并结果
        </p>
      </div>
      <ChevronDown
        :class="
          cn(
            'h-4 w-4 shrink-0 text-muted-foreground transition-transform',
            expanded && 'rotate-180',
          )
        "
      />
    </button>

    <div v-show="expanded" class="space-y-2 border-t border-primary/20 px-3 pb-3 pt-2">
      <div class="flex items-center justify-end">
        <Button variant="outline" size="sm" class="h-7 text-[10px]" :disabled="loading" @click="refresh">
          {{ loading ? '刷新中…' : '刷新预览' }}
        </Button>
      </div>

      <div class="flex flex-wrap items-center gap-2 text-[10px] text-muted-foreground">
        <span class="inline-flex items-center gap-1">
          <span class="h-2.5 w-2.5 rounded border border-amber-500/50 bg-amber-500/20" />
          全局
        </span>
        <span class="inline-flex items-center gap-1">
          <span class="h-2.5 w-2.5 rounded border border-emerald-500/50 bg-emerald-500/20" />
          随机
        </span>
        <span class="inline-flex items-center gap-1">
          <span class="h-2.5 w-2.5 rounded border border-sky-500/50 bg-sky-500/20" />
          工作流与当次
        </span>
        <span class="text-muted-foreground/80">· 色块顺序即拼接顺序；提交前会去重</span>
      </div>

      <p v-if="debug" class="text-[10px] text-muted-foreground">
        全局 {{ debug.global_enabled }} · 全局在前 {{ debug.global_before_workflow }} · 随机在前
        {{ debug.random_before_workflow }}
        · 全局随机组 {{ debug.global_random_groups ?? '?' }} · 当次随机组
        {{ debug.runtime_random_groups ?? '?' }} · 合计 {{ debug.random_groups_total ?? '?' }} · 抽取
        {{ debug.random_picks_count ?? '?' }}
        <template v-if="debug.random_placement_positive">
          · 随机词位置 {{ debug.random_placement_positive }}
        </template>
        <template v-if="debug.dedupe_tokens === 'true'">
          · 去重开
          <template v-if="Number(debug.dedupe_removed_positive) > 0">
            · 正向去重 {{ debug.dedupe_removed_positive }}
          </template>
        </template>
      </p>

      <div v-if="loading && !hasLoaded" class="text-xs text-muted-foreground py-4 text-center">
        加载预览…
      </div>

      <div v-else class="grid gap-2 lg:grid-cols-2">
        <div>
          <p class="mb-1 text-[10px] text-muted-foreground">正向</p>
          <div class="max-h-48 space-y-2 overflow-auto rounded bg-background/50 p-1.5">
            <PromptMergeSegmentBlocks :segments="segments.positive" />
          </div>
          <details v-if="positive" class="mt-1">
            <summary class="cursor-pointer text-[10px] text-muted-foreground hover:text-foreground">
              查看去重后完整正向
            </summary>
            <pre
              class="mt-1 max-h-28 overflow-auto whitespace-pre-wrap rounded border border-input/60 bg-background/90 p-2 text-[10px] leading-relaxed"
              >{{ positive }}</pre
            >
          </details>
        </div>
        <div>
          <p class="mb-1 text-[10px] text-muted-foreground">负向</p>
          <div class="max-h-40 space-y-2 overflow-auto rounded bg-background/50 p-1.5">
            <PromptMergeSegmentBlocks :segments="segments.negative" />
          </div>
          <details v-if="negative" class="mt-1">
            <summary class="cursor-pointer text-[10px] text-muted-foreground hover:text-foreground">
              查看去重后完整负向
            </summary>
            <pre
              class="mt-1 max-h-24 overflow-auto whitespace-pre-wrap rounded border border-input/60 bg-background/90 p-2 text-[10px] leading-relaxed"
              >{{ negative }}</pre
            >
          </details>
        </div>
      </div>
    </div>
  </div>
</template>
