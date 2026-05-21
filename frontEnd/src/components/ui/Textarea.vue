<script setup>
import { cn } from '@/lib/utils'

const model = defineModel({ type: String, default: '' })
defineProps({
  rows: { type: Number, default: 3 },
  disabled: { type: Boolean, default: false },
  class: { type: String, default: '' },
})
</script>

<template>
  <textarea
    v-model="model"
    :rows="rows"
    :disabled="disabled"
    :class="
      cn(
        'flex min-h-[60px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50',
        $props.class,
      )
    "
  />
</template>
