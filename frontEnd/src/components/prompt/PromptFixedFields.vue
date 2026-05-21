<script setup>
import Label from '@/components/ui/Label.vue'
import PromptTextarea from '@/components/prompt/PromptTextarea.vue'

defineProps({
  modelValue: { type: Object, required: true },
  disabled: { type: Boolean, default: false },
  compact: { type: Boolean, default: false },
})

defineEmits(['update:modelValue'])
</script>

<template>
  <div :class="compact ? 'space-y-3' : 'space-y-4'">
    <div class="grid gap-4 md:grid-cols-2">
      <div class="space-y-3 rounded-lg border border-border p-3">
        <p class="text-sm font-medium">正向（追加到 #3）</p>
        <div class="space-y-2">
          <Label class="text-xs">prefix</Label>
          <PromptTextarea
            :model-value="modelValue.positive?.prefix ?? ''"
            :rows="compact ? 4 : 5"
            :disabled="disabled"
            placeholder="批量/全局：追加在正向最前"
            @update:model-value="
              $emit('update:modelValue', {
                ...modelValue,
                positive: { ...modelValue.positive, prefix: $event },
              })
            "
          />
        </div>
        <div class="space-y-2">
          <Label class="text-xs">suffix</Label>
          <PromptTextarea
            :model-value="modelValue.positive?.suffix ?? ''"
            :rows="compact ? 4 : 5"
            :disabled="disabled"
            placeholder="追加在正向最后"
            @update:model-value="
              $emit('update:modelValue', {
                ...modelValue,
                positive: { ...modelValue.positive, suffix: $event },
              })
            "
          />
        </div>
      </div>
      <div class="space-y-3 rounded-lg border border-border p-3">
        <p class="text-sm font-medium">负向（追加到 #4）</p>
        <div class="space-y-2">
          <Label class="text-xs">prefix</Label>
          <PromptTextarea
            :model-value="modelValue.negative?.prefix ?? ''"
            :rows="compact ? 4 : 4"
            :disabled="disabled"
            @update:model-value="
              $emit('update:modelValue', {
                ...modelValue,
                negative: { ...modelValue.negative, prefix: $event },
              })
            "
          />
        </div>
        <div class="space-y-2">
          <Label class="text-xs">suffix</Label>
          <PromptTextarea
            :model-value="modelValue.negative?.suffix ?? ''"
            :rows="compact ? 4 : 4"
            :disabled="disabled"
            @update:model-value="
              $emit('update:modelValue', {
                ...modelValue,
                negative: { ...modelValue.negative, suffix: $event },
              })
            "
          />
        </div>
      </div>
    </div>
  </div>
</template>
