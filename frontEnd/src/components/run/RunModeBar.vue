<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { cn } from '@/lib/utils'

const route = useRoute()
const router = useRouter()

const mode = computed(() => (route.query.mode === 'sweep' ? 'sweep' : 'single'))

function setMode(next) {
  const query = { ...route.query }
  if (next === 'sweep') query.mode = 'sweep'
  else delete query.mode
  router.replace({ path: '/generate', query })
}
</script>

<template>
  <div
    class="inline-flex rounded-lg border border-border bg-muted/40 p-0.5 text-sm"
    role="tablist"
    aria-label="生成模式"
  >
    <button
      type="button"
      role="tab"
      :aria-selected="mode === 'single'"
      :class="
        cn(
          'rounded-md px-4 py-1.5 transition-colors',
          mode === 'single'
            ? 'bg-background text-foreground shadow-sm font-medium'
            : 'text-muted-foreground hover:text-foreground',
        )
      "
      @click="setMode('single')"
    >
      单张
    </button>
    <button
      type="button"
      role="tab"
      :aria-selected="mode === 'sweep'"
      :class="
        cn(
          'rounded-md px-4 py-1.5 transition-colors',
          mode === 'sweep'
            ? 'bg-background text-foreground shadow-sm font-medium'
            : 'text-muted-foreground hover:text-foreground',
        )
      "
      @click="setMode('sweep')"
    >
      LoRA 扫参
    </button>
  </div>
</template>
