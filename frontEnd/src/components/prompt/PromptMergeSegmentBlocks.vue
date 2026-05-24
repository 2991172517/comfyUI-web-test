<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { staggerReveal } from '@/lib/gsap/motion.js'

const props = defineProps({
  segments: { type: Array, default: () => [] },
  emptyLabel: { type: String, default: '—' },
  /** positive | negative，用于吸入动画定位 */
  side: { type: String, default: '' },
})

const rootRef = ref(null)

const KIND_META = {
  global: {
    label: '全局',
    boxClass: 'border-amber-500/40 bg-amber-500/12',
    badgeClass: 'bg-amber-600/90 text-white',
  },
  random: {
    label: '随机',
    boxClass: 'border-emerald-500/40 bg-emerald-500/12',
    badgeClass: 'bg-emerald-600/90 text-white',
  },
  core: {
    label: '工作流与当次',
    boxClass: 'border-sky-500/35 bg-sky-500/10',
    badgeClass: 'bg-sky-600/90 text-white',
  },
}

const blocks = computed(() =>
  (props.segments || [])
    .map((seg) => {
      const kind = seg?.kind || 'core'
      const meta = KIND_META[kind] || KIND_META.core
      const text = String(seg?.text || '').trim()
      if (!text) return null
      return { kind, text, ...meta }
    })
    .filter(Boolean),
)

watch(
  () => blocks.value.length,
  async () => {
    await nextTick()
    const root = rootRef.value
    if (!root) return
    const items = root.querySelectorAll('[data-merge-block]')
    if (items.length) staggerReveal(items)
  },
)
</script>

<template>
  <div v-if="blocks.length" ref="rootRef" class="space-y-1.5">
    <div
      v-for="(block, idx) in blocks"
      :key="`${block.kind}-${idx}`"
      data-merge-block
      :data-merge-side="side || undefined"
      :data-merge-index="idx"
      :data-merge-kind="block.kind"
      class="rounded border px-2 py-1.5"
      :class="block.boxClass"
    >
      <span
        class="mb-1 inline-block rounded px-1.5 py-0.5 text-[11px] font-medium leading-none"
        :class="block.badgeClass"
      >
        {{ block.label }}
      </span>
      <pre class="whitespace-pre-wrap text-sm leading-relaxed text-foreground">{{ block.text }}</pre>
    </div>
  </div>
  <p v-else class="text-sm text-muted-foreground">{{ emptyLabel }}</p>
</template>
