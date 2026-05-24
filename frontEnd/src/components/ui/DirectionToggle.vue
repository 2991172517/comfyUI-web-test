<script setup>
import { cn } from '@/lib/utils'

const props = defineProps({
  modelValue: { type: String, default: 'up' },
  disabled: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue'])

const options = [
  { value: 'up', label: '累加' },
  { value: 'down', label: '累减' },
]
</script>

<template>
  <div
    class="grid h-9 grid-cols-2 rounded-lg border border-border bg-muted/40 p-0.5"
    role="group"
    aria-label="扫参方向"
  >
    <button
      v-for="opt in options"
      :key="opt.value"
      type="button"
      :class="
        cn(
          'rounded-md text-xs font-medium transition-colors',
          modelValue === opt.value
            ? 'bg-background text-foreground shadow-sm'
            : 'text-muted-foreground hover:text-foreground',
          disabled && 'pointer-events-none opacity-50',
        )
      "
      :aria-pressed="modelValue === opt.value"
      :disabled="disabled"
      @click="emit('update:modelValue', opt.value)"
    >
      {{ opt.label }}
    </button>
  </div>
</template>
