<script setup>
import { nextTick, ref, watch } from 'vue'
import { gsap, prefersReducedMotion } from '@/lib/gsap/motion.js'
import PageAlert from '@/components/layout/PageAlert.vue'
import WorkflowRunHeader from '@/components/run/WorkflowRunHeader.vue'
import GlobalPromptBar from '@/components/run/GlobalPromptBar.vue'
import ModuleTabBar from '@/components/run/ModuleTabBar.vue'

defineProps({
  loading: { type: Boolean, default: false },
})

const activeModule = ref('prompt')
const panelRef = ref(null)

watch(activeModule, async () => {
  await nextTick()
  const el = panelRef.value
  if (!el || prefersReducedMotion()) return
  gsap.fromTo(
    el,
    { opacity: 0 },
    { opacity: 1, duration: 0.18, ease: 'power1.out', clearProps: 'opacity' },
  )
})
</script>

<template>
  <div class="space-y-4 w-full">
    <PageAlert />
    <WorkflowRunHeader />
    <GlobalPromptBar />
    <ModuleTabBar v-model="activeModule" />

    <div v-if="loading" class="text-sm text-muted-foreground py-8 text-center">加载工作流…</div>
    <div
      v-else
      ref="panelRef"
      class="rounded-lg border border-border bg-card p-4 md:p-6 min-h-[360px]"
    >
      <slot :active-module="activeModule" />
    </div>

    <footer v-if="$slots.footer" class="space-y-4">
      <slot name="footer" :active-module="activeModule" />
    </footer>
  </div>
</template>
