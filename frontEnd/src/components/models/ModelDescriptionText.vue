<script setup>
import { computed } from 'vue'

const props = defineProps({
  text: { type: String, default: '' },
  /** pre 风格保留换行 */
  pre: { type: Boolean, default: true },
})

const URL_RE = /https?:\/\/[^\s<>"')\]]+/g

const parts = computed(() => {
  const raw = props.text || ''
  if (!raw) return []
  const segments = []
  let last = 0
  for (const m of raw.matchAll(URL_RE)) {
    const idx = m.index ?? 0
    if (idx > last) segments.push({ type: 'text', value: raw.slice(last, idx) })
    segments.push({ type: 'link', value: m[0] })
    last = idx + m[0].length
  }
  if (last < raw.length) segments.push({ type: 'text', value: raw.slice(last) })
  return segments.length ? segments : [{ type: 'text', value: raw }]
})
</script>

<template>
  <component
    :is="pre ? 'pre' : 'span'"
    :class="
      pre
        ? 'whitespace-pre-wrap break-words text-[11px] text-muted-foreground leading-relaxed'
        : 'whitespace-pre-wrap break-words'
    "
  >
    <template v-for="(part, i) in parts" :key="i">
      <a
        v-if="part.type === 'link'"
        :href="part.value"
        target="_blank"
        rel="noopener noreferrer"
        class="text-primary hover:underline break-all font-medium"
        @click.stop
      >
        {{ part.value }}
      </a>
      <template v-else>{{ part.value }}</template>
    </template>
  </component>
</template>
