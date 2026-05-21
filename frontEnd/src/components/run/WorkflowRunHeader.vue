<script setup>
import { computed, onMounted, ref } from 'vue'
import { useAppStore } from '@/stores/useAppStore.js'
import { useBatchStore } from '@/stores/useBatchStore.js'
import { useCheckpointField } from '@/composables/useCheckpointField.js'
import { modelDisplayTitle } from '@/lib/modelDisplay.js'
import Badge from '@/components/ui/Badge.vue'
import SelectNative from '@/components/ui/SelectNative.vue'
import Button from '@/components/ui/Button.vue'
import ModelVisualPicker from '@/components/models/ModelVisualPicker.vue'
import { ChevronDown, ChevronUp } from 'lucide-vue-next'

const app = useAppStore()
const batch = useBatchStore()
const collapsed = ref(false)

const { entry, ckptName, hasCheckpoint } = useCheckpointField()

const checkpointDisabled = computed(
  () => app.loading || app.modelsLoading || batch.isBatchRunning,
)

const selectedWorkflow = computed({
  get: () => app.selectedId || '',
  set: async (id) => {
    if (!id || id === app.selectedId) return
    await pickWorkflow(id)
  },
})

async function pickWorkflow(id) {
  if (id === app.selectedId && app.state.nodes.length) return
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

      <SelectNative
        v-model="selectedWorkflow"
        class="min-w-[10rem] flex-1 max-w-xs"
        :disabled="app.loading || !app.workflows.length"
      >
        <option v-if="!app.workflows.length" value="" disabled>无工作流</option>
        <option v-for="wf in app.workflows" :key="wf.id" :value="wf.id">
          {{ wf.display_name || wf.name || wf.id }}
        </option>
      </SelectNative>

      <span
        v-if="hasCheckpoint && ckptName && collapsed"
        class="text-xs text-muted-foreground truncate max-w-[14rem]"
        :title="ckptName"
      >
        {{ modelDisplayTitle(ckptName) }}
      </span>

      <Badge v-if="app.isMasterWorkflow" variant="outline" class="text-[10px] shrink-0">母版</Badge>

      <Button
        variant="ghost"
        size="sm"
        class="h-7 text-xs shrink-0 ml-auto"
        @click="collapsed = !collapsed"
      >
        {{ collapsed ? '展开' : '收起' }}
      </Button>
    </div>

    <div v-show="!collapsed && hasCheckpoint" class="px-3 pb-3 pt-2">
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
  </header>
</template>
