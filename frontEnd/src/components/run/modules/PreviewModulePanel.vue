<script setup>
import { computed } from 'vue'
import { useAppStore } from '@/stores/useAppStore.js'
import Alert from '@/components/ui/Alert.vue'
import PipelineFlowStrip from '@/components/workflow/PipelineFlowStrip.vue'

const props = defineProps({
  disabled: { type: Boolean, default: false },
  persistMeta: { type: Boolean, default: false },
})

const app = useAppStore()

const pipeline = computed(() => {
  const list = app.pipelineNodesForUi
  return Array.isArray(list) ? list : []
})

const previewNodes = computed(() => pipeline.value.filter((n) => n.is_preview))

const enabledIds = computed(() => app.enabledPreviewNodeIdsForUi || [])

async function onTogglePreview(nodeId) {
  if (props.disabled) return
  const id = String(nodeId)
  const next = new Set(enabledIds.value.map(String))
  if (next.has(id)) next.delete(id)
  else next.add(id)
  app.setEnabledPreviewNodeIds([...next])
  if (props.persistMeta) {
    await app.savePreviewNodeSelection({ quiet: true })
  }
}

async function selectAllPreviews() {
  if (props.disabled || !previewNodes.value.length) return
  app.setEnabledPreviewNodeIds(previewNodes.value.map((n) => String(n.node_id)))
  if (props.persistMeta) await app.savePreviewNodeSelection()
}

async function clearAllPreviews() {
  if (props.disabled) return
  app.setEnabledPreviewNodeIds([])
  if (props.persistMeta) await app.savePreviewNodeSelection()
}
</script>

<template>
  <div class="space-y-4">
    <p class="text-sm text-muted-foreground leading-relaxed">
      横向为<strong>执行顺序</strong>（箭头连接）。仅
      <code class="text-xs">PreviewImage</code>
      可勾选；未勾选的不参与生成。勾选后预览图在「生成状态」对应节点下方「点击查看」，不在底部生成结果区。
    </p>

    <div class="flex flex-wrap items-center gap-2">
        <button
          type="button"
          class="text-xs text-primary hover:underline disabled:opacity-50"
          :disabled="disabled || !previewNodes.length"
          @click="selectAllPreviews"
        >
          全选预览
        </button>
        <button
          type="button"
          class="text-xs text-muted-foreground hover:underline disabled:opacity-50"
          :disabled="disabled"
          @click="clearAllPreviews"
        >
          预览全不选
        </button>
        <span class="text-xs text-muted-foreground">
          预览 {{ enabledIds.length }} / {{ previewNodes.length }} · 共
          {{ pipeline.length }} 节点 · 本次执行
          {{ app.executionPipelineNodesForUi.length }} 步
        </span>
      </div>

      <PipelineFlowStrip
        mode="config"
        :nodes="pipeline"
        :disabled="disabled"
        :enabled-preview-ids="enabledIds"
        @toggle-preview="onTogglePreview"
      />
  </div>
</template>
