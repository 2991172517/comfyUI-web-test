<script setup>
import { computed } from 'vue'
import { useAppStore } from '@/stores/useAppStore.js'
import Badge from '@/components/ui/Badge.vue'
import LoraModelPicker from '@/components/models/LoraModelPicker.vue'

defineProps({ disabled: { type: Boolean, default: false } })

const app = useAppStore()

const styleLora = computed(() => (app.workflowLoras || []).find((l) => l.role === 'style'))
</script>

<template>
  <div v-if="!styleLora" class="text-sm text-muted-foreground py-6">本工作流无 Style LoRA 槽位。</div>
  <div v-else class="space-y-5 max-w-2xl">
    <p class="text-sm text-muted-foreground">
      关闭时运行绕过 Style 节点（负向 CLIP / model 改接角色 LoRA），不删除 JSON 节点。
    </p>
    <label class="flex items-center gap-3 text-base">
      <input
        type="checkbox"
        class="rounded border-input h-4 w-4"
        :checked="app.styleEnabled"
        :disabled="disabled || app.loading"
        @change="app.setStyleEnabled($event.target.checked)"
      />
      生成时启用 Style
      <Badge :variant="app.styleEnabled ? 'default' : 'secondary'">
        {{ app.styleEnabled ? '链上' : '已绕过' }}
      </Badge>
    </label>
    <LoraModelPicker
      label="Style LoRA"
      :model-value="String(app.fieldValue(styleLora.node_id, { key: 'lora_name', value: styleLora.lora_name }))"
      :options="app.modelLists.loras"
      :catalog="app.modelLists.loraCatalog"
      :disabled="disabled || app.modelsLoading"
      :loading="app.modelsLoading"
      @update:model-value="app.updateField(styleLora.node_id, 'lora_name', $event)"
    />
    <div class="grid grid-cols-2 gap-4 max-w-md">
      <div>
        <label class="text-xs text-muted-foreground">strength_model</label>
        <input
          type="number"
          step="0.05"
          class="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
          :value="app.fieldValue(styleLora.node_id, { key: 'strength_model', value: styleLora.strength_model })"
          @input="app.updateField(styleLora.node_id, 'strength_model', Number($event.target.value))"
        />
      </div>
      <div>
        <label class="text-xs text-muted-foreground">strength_clip</label>
        <input
          type="number"
          step="0.05"
          class="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
          :value="app.fieldValue(styleLora.node_id, { key: 'strength_clip', value: styleLora.strength_clip })"
          @input="app.updateField(styleLora.node_id, 'strength_clip', Number($event.target.value))"
        />
      </div>
    </div>
  </div>
</template>
