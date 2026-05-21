<script setup>
import { cn } from '@/lib/utils'

defineProps({
  value: { type: Number, default: 0 },
  class: { type: String, default: '' },
})
</script>

<template>
  <div
    role="progressbar"
    :aria-valuenow="value"
    :class="cn('relative h-2 w-full overflow-hidden rounded-full bg-secondary', $props.class)"
  >
    <div
      class="h-full bg-primary transition-all duration-300 ease-out"
      :style="{ width: `${Math.min(100, Math.max(0, value))}%` }"
    />
  </div>
</template>
