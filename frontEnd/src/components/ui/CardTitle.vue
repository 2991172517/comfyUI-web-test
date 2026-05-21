<script setup>
import { cn } from '@/lib/utils'
defineProps({ class: { type: String, default: '' } })
</script>

<template>
  <h3
    :class="cn('text-lg font-semibold leading-none tracking-tight text-foreground', $props.class)"
  >
    <slot />
  </h3>
</template>
