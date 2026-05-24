<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { allowsBatch } from '@/composables/useAuth.js'
import { cn } from '@/lib/utils'
import { moveTabIndicator } from '@/lib/gsap/tabIndicator.js'

const route = useRoute()
const router = useRouter()

const mode = computed(() => (route.query.mode === 'sweep' ? 'sweep' : 'single'))

const tabs = [
  { id: 'single', label: '单张生成' },
  { id: 'sweep', label: '批量生成' },
]

const navRef = ref(null)
const indicatorRef = ref(null)

function setMode(next) {
  const query = { ...route.query }
  if (next === 'sweep') query.mode = 'sweep'
  else delete query.mode
  router.replace({ path: '/generate', query })
}

function syncIndicator() {
  nextTick(() => {
    const nav = navRef.value
    const indicator = indicatorRef.value
    if (!nav || !indicator) return
    const tab = nav.querySelector(`[data-mode-id="${mode.value}"]`)
    if (tab) moveTabIndicator(indicator, tab, nav)
  })
}

onMounted(syncIndicator)
watch(mode, syncIndicator)
</script>

<template>
  <div
    v-if="allowsBatch()"
    ref="navRef"
    class="relative grid h-9 w-[12.5rem] shrink-0 grid-cols-2 rounded-lg border border-border bg-muted/40 p-0.5 text-sm"
    role="tablist"
    aria-label="生成模式"
  >
    <span
      ref="indicatorRef"
      class="pointer-events-none absolute top-0.5 bottom-0.5 left-0.5 rounded-md bg-background shadow-sm opacity-0"
      aria-hidden="true"
    />
    <button
      v-for="tab in tabs"
      :key="tab.id"
      type="button"
      role="tab"
      :data-mode-id="tab.id"
      :aria-selected="mode === tab.id"
      :class="
        cn(
          'relative z-[1] min-w-0 w-full rounded-md text-[13px] leading-none transition-colors',
          mode === tab.id
            ? 'text-foreground font-medium'
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
