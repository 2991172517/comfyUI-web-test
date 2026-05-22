<script setup>
import { computed } from 'vue'
import { cn } from '@/lib/utils'

const props = defineProps({
  modelValue: { type: Number, default: 0 },
  min: { type: Number, default: 0 },
  max: { type: Number, default: 1 },
  step: { type: Number, default: 0.05 },
  disabled: { type: Boolean, default: false },
  showValue: { type: Boolean, default: true },
  format: { type: Function, default: null },
})

const emit = defineEmits(['update:modelValue'])

const display = computed(() => {
  if (props.format) return props.format(props.modelValue)
  const step = props.step
  const decimals = step >= 1 ? 0 : step >= 0.1 ? 1 : 2
  return Number(props.modelValue).toFixed(decimals)
})

function onInput(e) {
  emit('update:modelValue', Number(e.target.value))
}
</script>

<template>
  <div class="flex items-center gap-3 min-w-0">
    <input
      type="range"
      class="slider-track h-2 flex-1 min-w-[6rem] cursor-pointer accent-primary disabled:cursor-not-allowed disabled:opacity-50"
      :min="min"
      :max="max"
      :step="step"
      :value="modelValue"
      :disabled="disabled"
      @input="onInput"
    />
    <span
      v-if="showValue"
      :class="
        cn(
          'tabular-nums text-xs text-muted-foreground shrink-0 w-10 text-right',
          disabled && 'opacity-50',
        )
      "
    >
      {{ display }}
    </span>
  </div>
</template>
