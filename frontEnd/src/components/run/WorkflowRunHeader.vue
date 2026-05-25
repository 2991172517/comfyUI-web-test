<script setup>
import { computed, onMounted, ref } from 'vue'
import { useAppStore } from '@/stores/useAppStore.js'
import { useBatchStore } from '@/stores/useBatchStore.js'
import { useCheckpointField } from '@/composables/useCheckpointField.js'
import { useWorkflowRunCategory } from '@/composables/useWorkflowRunCategory.js'
import { modelDisplayTitle } from '@/lib/modelDisplay.js'
import Badge from '@/components/ui/Badge.vue'
import SelectNative from '@/components/ui/SelectNative.vue'
import Button from '@/components/ui/Button.vue'
import ModelVisualPicker from '@/components/models/ModelVisualPicker.vue'
import AnimatedCollapse from '@/components/ui/AnimatedCollapse.vue'
import { ChevronDown, ChevronUp } from 'lucide-vue-next'

const app = useAppStore()
const batch = useBatchStore()
const { categoryLabel, isGenerateLike } = useWorkflowRunCategory()
const collapsed = ref(false)
const headerExpanded = computed({
  get: () => !collapsed.value,
  set: (v) => {
    collapsed.value = !v
  },
})

const { entry, ckptName, hasCheckpoint } = useCheckpointField()

const checkpointDisabled = computed(
  () => app.loading || app.modelsLoading || batch.isBatchRunning,
)

const selectedEntry = computed(() =>
  app.workflows.find((w) => w.id === app.selectedId),
)

function workflowOptionLabel(wf) {
  const name = wf.display_name || wf.name || wf.id
  if (wf.id === app.selectedId && app.temporaryWorkflowActive) {
    return `临时 · ${name}`
  }
  return name
}

const selectedWorkflow = computed({
  get: () => app.selectedId || '',
  set: async (id) => {
    if (!id || id === app.selectedId) return
    await pickWorkflow(id)
  },
})

async function pickWorkflow(id) {
  if (id === app.selectedId && app.state.nodes.length) return
  app.clearTemporaryWorkflow()
  await app.loadWorkflow(id)
}

onMounted(() => {
  if (app.healthOk && !app.modelLists.checkpoints.length) {
    app.loadModelLists().catch(() => {})
  }
})
</script>

<template>
  <header class="rounded-lg border border-border bg-card overflow-hidden">
    <div
      class="flex flex-wrap items-center gap-2 px-3 py-2.5 border-b border-border/60 bg-muted/20"
    >
      <button
        type="button"
        class="flex items-center gap-1 text-sm font-medium shrink-0 hover:text-primary transition-colors"
        @click="collapsed = !collapsed"
      >
        <component :is="collapsed ? ChevronDown : ChevronUp" class="h-4 w-4 text-muted-foreground" />
        当前工作流
      </button>

      <Badge variant="outline" class="text-[10px] shrink-0">
        {{ categoryLabel }}
      </Badge>
      <Badge
        v-if="app.temporaryWorkflowActive"
        variant="secondary"
        class="text-[10px] shrink-0 border-amber-500/40 bg-amber-500/10 text-amber-800 dark:text-amber-200"
        :title="app.temporaryWorkflowHint || undefined"
      >
        临时工作流
      </Badge>

      <SelectNative
        v-model="selectedWorkflow"
        class="min-w-[10rem] flex-1 max-w-xs"
        :disabled="app.loading || !app.workflows.length"
      >
        <option v-if="!app.workflows.length" value="" disabled>无工作流</option>
        <option v-for="wf in app.workflows" :key="wf.id" :value="wf.id">
          {{ workflowOptionLabel(wf) }}
        </option>
      </SelectNative>

      <span
        v-if="hasCheckpoint && ckptName && collapsed && isGenerateLike"
        class="text-xs text-muted-foreground truncate max-w-[14rem]"
        :title="ckptName"
      >
        {{ modelDisplayTitle(ckptName) }}
      </span>
      <span
        v-else-if="selectedEntry && collapsed && !isGenerateLike"
        class="text-xs text-muted-foreground truncate max-w-[14rem]"
        :title="selectedEntry.id"
      >
        {{ selectedEntry.display_name || selectedEntry.id }}
      </span>

      <Button
        variant="ghost"
        size="sm"
        class="h-7 text-xs shrink-0 ml-auto"
        @click="collapsed = !collapsed"
      >
        {{ collapsed ? '展开' : '收起' }}
      </Button>
    </div>

    <p
      v-if="app.temporaryWorkflowActive"
      class="px-3 py-1.5 text-[11px] text-muted-foreground border-b border-border/50 bg-amber-500/5"
    >
      由图片或历史记录恢复的临时工作流，未在本地库中匹配到原 ID
      <template v-if="app.temporaryWorkflowHint">
        （原：{{ app.temporaryWorkflowHint }}）
      </template>
      。可在工作流配置中另存为正式子工作流。
    </p>

    <AnimatedCollapse v-model="headerExpanded">
      <div v-if="hasCheckpoint && isGenerateLike" class="px-3 pb-3 pt-2">
        <ModelVisualPicker
          v-model="ckptName"
          folder="checkpoints"
          label="Checkpoint"
          :options="app.modelLists.checkpoints"
          :catalog="app.modelLists.checkpointCatalog"
          :missing-value="entry && app.modelSelectMissing(entry.nodeId, entry.field)"
          :disabled="checkpointDisabled"
          :loading="app.modelsLoading"
        />
      </div>
    </AnimatedCollapse>
  </header>
</template>
