<script setup>
import { computed } from 'vue'
import { Minus, Plus } from 'lucide-vue-next'
import { cn } from '@/lib/utils'

const props = defineProps({
  modelValue: { type: Number, default: 1 },
  min: { type: Number, default: 1 },
  max: { type: Number, default: 20 },
  step: { type: Number, default: 1 },
  disabled: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue'])

const value = computed(() => {
  const n = Math.round(Number(props.modelValue) || props.min)
  return Math.max(props.min, Math.min(props.max, n))
})

function setValue(next) {
  const n = Math.max(props.min, Math.min(props.max, Math.round(next)))
  emit('update:modelValue', n)
}

function dec() {
  if (props.disabled || value.value <= props.min) return
  setValue(value.value - props.step)
}

function inc() {
  if (props.disabled || value.value >= props.max) return
  setValue(value.value + props.step)
}
</script>

<template>
  <div
    class="flex h-9 items-stretch overflow-hidden rounded-lg border border-border bg-muted/40"
    role="group"
  >
    <button
      type="button"
      class="flex w-10 shrink-0 items-center justify-center text-muted-foreground transition-colors hover:bg-accent hover:text-foreground disabled:pointer-events-none disabled:opacity-40"
      :disabled="disabled || value <= min"
      aria-label="减少"
      @click="dec"
    >
      <Minus class="h-4 w-4" />
    </button>
    <div
      :class="
        cn(
          'flex min-w-[2.5rem] flex-1 items-center justify-center border-x border-border/70 tabular-nums text-sm font-medium',
          disabled && 'opacity-50',
        )
      "
      aria-live="polite"
    >
      {{ value }}
    </div>
    <button
      type="button"
      class="flex w-10 shrink-0 items-center justify-center text-muted-foreground transition-colors hover:bg-accent hover:text-foreground disabled:pointer-events-none disabled:opacity-40"
      :disabled="disabled || value >= max"
      aria-label="增加"
      @click="inc"
    >
      <Plus class="h-4 w-4" />
    </button>
  </div>
</template>
