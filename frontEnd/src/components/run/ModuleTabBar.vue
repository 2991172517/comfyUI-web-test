<script setup>
import { RUN_MODULES } from '@/composables/useRunModules.js'
import { cn } from '@/lib/utils'

const active = defineModel({ type: String, default: 'prompt' })
</script>

<template>
  <nav class="flex flex-wrap gap-1 rounded-lg border border-border bg-muted/40 p-1">
    <button
      v-for="tab in RUN_MODULES"
      :key="tab.id"
      type="button"
      :class="
        cn(
          'rounded-md px-4 py-2 text-sm font-medium transition-colors',
          active === tab.id
            ? 'bg-background text-foreground shadow-sm'
            : 'text-muted-foreground hover:text-foreground hover:bg-background/60',
        )
      "
      @click="active = tab.id"
    >
      {{ tab.label }}
    </button>
  </nav>
</template>
