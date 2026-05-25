<script setup>
import { TrendingDown, TrendingUp } from 'lucide-vue-next'
import { cn } from '@/lib/utils'

defineProps({
  modelValue: { type: String, default: 'up' },
  disabled: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue'])

const options = [
  {
    value: 'up',
    label: '累加',
    icon: TrendingUp,
    active:
      'bg-emerald-500/20 text-emerald-800 dark:text-emerald-300 ring-1 ring-emerald-500/35 shadow-sm',
    idle: 'text-muted-foreground hover:bg-emerald-500/10 hover:text-emerald-700 dark:hover:text-emerald-400',
  },
  {
    value: 'down',
    label: '累减',
    icon: TrendingDown,
    active:
      'bg-amber-500/20 text-amber-900 dark:text-amber-200 ring-1 ring-amber-500/35 shadow-sm',
    idle: 'text-muted-foreground hover:bg-amber-500/10 hover:text-amber-800 dark:hover:text-amber-300',
  },
]
</script>

<template>
  <div
    class="grid h-9 grid-cols-2 gap-0.5 rounded-lg border border-border bg-muted/30 p-0.5"
    role="group"
    aria-label="扫参方向"
  >
    <button
      v-for="opt in options"
      :key="opt.value"
      type="button"
      :class="
        cn(
          'inline-flex items-center justify-center gap-1 rounded-md px-2 text-xs font-medium transition-colors',
          modelValue === opt.value ? opt.active : opt.idle,
          disabled && 'pointer-events-none opacity-50',
        )
      "
      :aria-pressed="modelValue === opt.value"
      :disabled="disabled"
      @click="emit('update:modelValue', opt.value)"
    >
      <component :is="opt.icon" class="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
      {{ opt.label }}
    </button>
  </div>
</template>
