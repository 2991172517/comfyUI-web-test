<script setup>
import { computed } from 'vue'
import { cn } from '@/lib/utils'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  size: { type: String, default: 'default' },
  id: { type: String, default: undefined },
  ariaLabel: { type: String, default: undefined },
})

const emit = defineEmits(['update:modelValue'])

const trackClass = computed(() =>
  cn(
    'relative inline-flex shrink-0 cursor-pointer items-center rounded-full border-2 transition-colors',
    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background',
    'disabled:cursor-not-allowed disabled:opacity-50',
    props.size === 'sm' ? 'h-5 w-9' : 'h-6 w-11',
    props.modelValue
      ? 'border-primary bg-primary'
      : 'border-border bg-muted hover:bg-accent',
  ),
)

const thumbClass = computed(() =>
  cn(
    'pointer-events-none block rounded-full bg-foreground shadow-md ring-1 ring-black/20 transition-transform',
    props.size === 'sm' ? 'h-4 w-4' : 'h-5 w-5',
    props.modelValue
      ? props.size === 'sm'
        ? 'translate-x-4'
        : 'translate-x-5'
      : 'translate-x-0',
  ),
)

function toggle() {
  if (props.disabled) return
  emit('update:modelValue', !props.modelValue)
}
</script>

<template>
  <button
    :id="id"
    type="button"
    role="switch"
    :aria-checked="modelValue"
    :aria-label="ariaLabel"
    :disabled="disabled"
    :class="trackClass"
    @click="toggle"
  >
    <span :class="thumbClass" />
  </button>
</template>
