<script setup>
import { computed } from 'vue'
import { useAppStore } from '@/stores/useAppStore.js'
import Card from '@/components/ui/Card.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import CardTitle from '@/components/ui/CardTitle.vue'
import CardDescription from '@/components/ui/CardDescription.vue'
import CardContent from '@/components/ui/CardContent.vue'
import Badge from '@/components/ui/Badge.vue'

const store = useAppStore()

const styleSlot = computed(() =>
  (store.workflowLoras || []).find((l) => l.role === 'style'),
)

const topologyNote = computed(() => {
  const kind = styleSlot.value?.kind || 'lora_chain'
  if (kind === 'lora_chain') {
    return '当前母版：Style 为链末 LoRA(#16)，关闭时 model/负向 CLIP 改接角色 LoRA(#15)。理想拓扑为 正向 CLIP → Style 节点 → KSampler①（预留 conditioning）。'
  }
  return 'Conditioning Style 节点（IPAdapter 等）将在后续模板中启用。'
})
</script>

<template>
  <Card v-if="styleSlot">
    <CardHeader class="pb-2">
      <CardTitle class="text-base">Style（{{ styleSlot.short_name }}）</CardTitle>
      <CardDescription>{{ topologyNote }}</CardDescription>
    </CardHeader>
    <CardContent class="flex flex-wrap items-center gap-3">
      <label class="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          class="rounded border-input"
          :checked="store.styleEnabled"
          :disabled="store.loading"
          @change="store.setStyleEnabled($event.target.checked)"
        />
        启用 Style LoRA
      </label>
      <Badge :variant="store.styleEnabled ? 'default' : 'secondary'">
        {{ store.styleEnabled ? '链上生效' : '已绕过 #16' }}
      </Badge>
      <Badge v-if="store.isMasterWorkflow" variant="outline">母版 · 参数另存子工作流</Badge>
    </CardContent>
  </Card>
</template>
