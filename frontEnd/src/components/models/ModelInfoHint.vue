<script setup>
import { ref } from 'vue'
import { Info } from 'lucide-vue-next'
import { cn } from '@/lib/utils'

defineProps({
  summary: { type: Object, required: true },
})

const open = ref(false)
</script>

<template>
  <div class="relative shrink-0" @mouseenter="open = true" @mouseleave="open = false">
    <button
      type="button"
      :class="
        cn(
          'inline-flex h-7 w-7 items-center justify-center rounded-md border border-border',
          'text-muted-foreground hover:bg-accent hover:text-foreground transition-colors',
          open && 'bg-accent text-foreground',
        )
      "
      :title="summary.filename"
      aria-label="模型说明"
      @focusin="open = true"
      @focusout="open = false"
    >
      <Info class="h-3.5 w-3.5" />
    </button>
    <div
      v-show="open"
      class="absolute left-0 top-full z-50 mt-1 w-[min(22rem,calc(100vw-2rem))] rounded-lg border border-border bg-popover p-3 shadow-lg"
      role="tooltip"
    >
      <p class="text-xs font-medium text-foreground mb-1 truncate" :title="summary.filename">
        {{ summary.filename }}
      </p>
      <p v-if="summary.asset_dir" class="text-[10px] text-muted-foreground mb-2 font-mono truncate">
        {{ summary.asset_dir }}/
      </p>
      <pre
        class="max-h-48 overflow-auto text-xs text-muted-foreground whitespace-pre-wrap break-words leading-relaxed"
      >{{ summary.content }}</pre>
      <p v-if="summary.truncated" class="text-[10px] text-muted-foreground mt-2">（内容已截断）</p>
    </div>
  </div>
</template>
