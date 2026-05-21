<script setup>
import { computed } from 'vue'
import { useAppStore } from '@/stores/useAppStore.js'
import Card from '@/components/ui/Card.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import CardTitle from '@/components/ui/CardTitle.vue'
import CardDescription from '@/components/ui/CardDescription.vue'
import CardContent from '@/components/ui/CardContent.vue'
import Badge from '@/components/ui/Badge.vue'
import { cn } from '@/lib/utils'

const props = defineProps({
  /** 完整卡片 / 紧凑条 */
  compact: { type: Boolean, default: false },
  title: { type: String, default: '工作流' },
  description: { type: String, default: '' },
})

const store = useAppStore()

const defaultDescription = computed(() => {
  if (props.description) return props.description
  return '选择后加载节点参数、LoRA 链与 Checkpoint；与抽卡页共用同一份配置。'
})

const currentMeta = computed(() => {
  const wf = store.workflows.find((w) => w.id === store.selectedId)
  if (!wf) return null
  return {
    name: wf.name,
    format: wf.format,
    loraCount: store.workflowLoras?.length ?? 0,
    nodeCount: store.state.nodes?.length ?? 0,
  }
})

async function selectWorkflow(id) {
  if (id === store.selectedId && store.state.nodes.length) return
  await store.loadWorkflow(id)
}
</script>

<template>
  <Card v-if="!compact" class="mb-4">
    <CardHeader class="pb-2">
      <CardTitle class="text-base">{{ title }}</CardTitle>
      <CardDescription>{{ defaultDescription }}</CardDescription>
    </CardHeader>
    <CardContent class="space-y-3">
      <div class="flex flex-wrap items-center gap-2">
        <button
          v-for="wf in store.workflows"
          :key="wf.id"
          type="button"
          :disabled="store.loading"
          :class="
            cn(
              'rounded-md border px-3 py-1.5 text-sm transition-colors disabled:opacity-50',
              wf.id === store.selectedId
                ? 'border-primary bg-primary/10 text-foreground font-medium'
                : 'border-border bg-background hover:bg-accent',
            )
          "
          @click="selectWorkflow(wf.id)"
        >
          {{ wf.display_name || wf.name }}
          <Badge v-if="wf.is_master" variant="secondary" class="ml-1 text-[10px]">母版</Badge>
          <Badge v-else-if="wf.is_variant" variant="outline" class="ml-1 text-[10px]">子</Badge>
          <Badge variant="outline" class="ml-1.5 text-[10px]">{{ wf.format }}</Badge>
        </button>
      </div>
      <p v-if="!store.workflows.length" class="text-sm text-muted-foreground">
        将 Export (API) 的 json 放入 CustomProject/workflows/
      </p>
      <p v-else-if="store.loading" class="text-sm text-muted-foreground">正在加载工作流…</p>
      <p v-else-if="currentMeta" class="text-xs text-muted-foreground">
        当前：<strong class="text-foreground">{{ currentMeta.name }}</strong>
        · {{ currentMeta.format }}
        · {{ currentMeta.loraCount }} 个 LoRA
        · {{ currentMeta.nodeCount }} 个可编辑节点
      </p>
    </CardContent>
  </Card>

  <div v-else class="rounded-lg border border-border bg-card px-3 py-2">
    <div class="mb-2 flex flex-wrap items-center gap-2">
      <span class="text-xs font-medium text-muted-foreground">{{ title }}</span>
      <button
        v-for="wf in store.workflows"
        :key="wf.id"
        type="button"
        :disabled="store.loading"
        :class="
          cn(
            'rounded-md px-2.5 py-1 text-xs transition-colors disabled:opacity-50',
            wf.id === store.selectedId
              ? 'bg-primary text-primary-foreground'
              : 'text-muted-foreground hover:bg-accent hover:text-foreground',
          )
        "
        @click="selectWorkflow(wf.id)"
      >
        {{ wf.display_name || wf.name }}
      </button>
    </div>
    <p v-if="currentMeta && !store.loading" class="text-[10px] text-muted-foreground">
      {{ currentMeta.name }} · {{ currentMeta.loraCount }} LoRA · {{ currentMeta.format }}
    </p>
  </div>
</template>
