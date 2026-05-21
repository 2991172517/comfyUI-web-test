<script setup>
import { cn } from '@/lib/utils'

defineProps({
  variant: { type: String, default: 'default' },
  class: { type: String, default: '' },
})
</script>

<template>
  <div
    role="alert"
    :class="
      cn(
        'relative w-full rounded-lg border px-4 py-3 text-sm',
        variant === 'destructive'
          ? 'border-destructive/50 text-red-200 bg-destructive/10'
          : 'border-border bg-card text-foreground',
        $props.class,
      )
    "
  >
    <slot />
  </div>
</template>
