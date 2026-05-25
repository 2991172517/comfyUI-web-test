<script setup>
import { Paintbrush } from 'lucide-vue-next'
import { useNavigateToInpaint } from '@/composables/useNavigateToInpaint.js'
import { cn } from '@/lib/utils'

const props = defineProps({
  /** @type {() => object | null} */
  getPayload: { type: Function, required: true },
  title: { type: String, default: '用此图局部重绘' },
  size: { type: String, default: 'sm' },
  class: { type: String, default: '' },
})

const { goInpaint } = useNavigateToInpaint()

const sizeClass =
  props.size === 'md'
    ? 'h-8 w-8'
    : 'h-7 w-7'

function onClick(ev) {
  ev.stopPropagation()
  const payload = props.getPayload?.()
  if (payload) goInpaint(payload)
}
</script>

<template>
  <button
    type="button"
    :title="title"
    :aria-label="title"
    :class="
      cn(
        'inline-flex items-center justify-center rounded-full border border-border/80 bg-background/90 text-primary shadow-sm transition-colors',
        'hover:bg-primary/15 hover:border-primary/40',
        sizeClass,
        props.class,
      )
    "
    @click="onClick"
  >
    <Paintbrush class="h-3.5 w-3.5" />
  </button>
</template>
