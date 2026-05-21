<script setup>
import { cn } from '@/lib/utils'
defineProps({ class: { type: String, default: '' } })
</script>

<template>
  <label :class="cn('text-sm font-medium leading-none text-foreground', $props.class)">
    <slot />
  </label>
</template>
