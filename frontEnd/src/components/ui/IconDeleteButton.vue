<script setup>
import { Trash2 } from 'lucide-vue-next'
import { cn } from '@/lib/utils'

defineProps({
  size: { type: String, default: 'md' },
  disabled: { type: Boolean, default: false },
  title: { type: String, default: '删除' },
})

const emit = defineEmits(['click'])

function onClick(e) {
  e.stopPropagation()
  emit('click', e)
}
</script>

<template>
  <button
    type="button"
    :title="title"
    :aria-label="title"
    :disabled="disabled"
    :class="
      cn(
        'inline-flex shrink-0 items-center justify-center rounded-md border transition-colors',
        'border-destructive/45 bg-destructive/15 text-destructive',
        'hover:bg-destructive/30 hover:border-destructive/70',
        'disabled:opacity-40 disabled:pointer-events-none',
        size === 'sm' ? 'h-7 w-7' : 'h-8 w-8',
      )
    "
    @click="onClick"
  >
    <Trash2 :class="size === 'sm' ? 'h-3.5 w-3.5' : 'h-4 w-4'" :stroke-width="2.25" />
  </button>
</template>
