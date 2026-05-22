<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { allowsBatch } from '@/composables/useAuth.js'
import { cn } from '@/lib/utils'

const route = useRoute()
const router = useRouter()

const mode = computed(() => (route.query.mode === 'sweep' ? 'sweep' : 'single'))

const tabs = [
  { id: 'single', label: '单张生成' },
  { id: 'sweep', label: '批量生成' },
]

function setMode(next) {
  const query = { ...route.query }
  if (next === 'sweep') query.mode = 'sweep'
  else delete query.mode
  router.replace({ path: '/generate', query })
}
</script>

<template>
  <div
    v-if="allowsBatch()"
    class="grid h-9 w-[12.5rem] shrink-0 grid-cols-2 rounded-lg border border-border bg-muted/40 p-0.5 text-sm"
    role="tablist"
    aria-label="生成模式"
  >
    <button
      v-for="tab in tabs"
      :key="tab.id"
      type="button"
      role="tab"
      :aria-selected="mode === tab.id"
      :class="
        cn(
          'min-w-0 w-full rounded-md text-[13px] leading-none transition-colors',
          mode === tab.id
            ? 'bg-background text-foreground shadow-sm font-medium'
            : 'text-muted-foreground hover:text-foreground',
        )
      "
      @click="setMode(tab.id)"
    >
      {{ tab.label }}
    </button>
  </div>
  <span v-else class="text-sm font-medium text-foreground">单张生成</span>
</template>
