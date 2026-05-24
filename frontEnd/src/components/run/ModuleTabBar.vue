<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { RUN_MODULES } from '@/composables/useRunModules.js'
import { cn } from '@/lib/utils'
import { moveTabIndicator } from '@/lib/gsap/tabIndicator.js'

const props = defineProps({
  tabs: { type: Array, default: null },
})

const active = defineModel({ type: String, default: 'prompt' })

const moduleTabs = computed(() => props.tabs || RUN_MODULES)

const navRef = ref(null)
const indicatorRef = ref(null)

function syncIndicator() {
  nextTick(() => {
    const nav = navRef.value
    const indicator = indicatorRef.value
    if (!nav || !indicator) return
    const tab = nav.querySelector(`[data-tab-id="${active.value}"]`)
    if (tab) moveTabIndicator(indicator, tab, nav)
  })
}

onMounted(syncIndicator)
watch(active, syncIndicator)
watch(moduleTabs, syncIndicator)
</script>

<template>
  <nav
    ref="navRef"
    class="relative flex flex-wrap gap-1 rounded-lg border border-border bg-muted/40 p-1"
  >
    <span
      ref="indicatorRef"
      class="pointer-events-none absolute top-1 bottom-1 left-0 rounded-md bg-background shadow-sm opacity-0"
      aria-hidden="true"
    />
    <button
      v-for="tab in moduleTabs"
      :key="tab.id"
      type="button"
      :data-tab-id="tab.id"
      :class="
        cn(
          'relative z-[1] rounded-md px-4 py-2 text-sm font-medium transition-colors',
          active === tab.id
            ? 'text-foreground'
            : 'text-muted-foreground hover:text-foreground hover:bg-background/40',
        )
      "
      @click="active = tab.id"
    >
      {{ tab.label }}
    </button>
  </nav>
</template>
