<script setup>
import {
  PROMPT_EDITOR_MODE_OPTIONS,
  usePromptEditorMode,
} from '@/composables/usePromptEditorMode.js'
import { cn } from '@/lib/utils'

defineProps({
  compact: { type: Boolean, default: false },
})

const { mode: editorMode } = usePromptEditorMode()
</script>

<template>
  <div
    :class="
      cn(
        'rounded-md border border-border/70 bg-muted/15',
        compact ? 'px-2 py-1.5' : 'px-3 py-2',
      )
    "
  >
    <p v-if="!compact" class="mb-1.5 text-xs font-medium text-foreground">提示词输入格式</p>
    <div class="flex flex-wrap gap-1.5">
      <label
        v-for="opt in PROMPT_EDITOR_MODE_OPTIONS"
        :key="opt.id"
        :class="
          cn(
            'flex cursor-pointer items-center gap-1.5 rounded border px-2 py-1 text-[11px] transition-colors',
            editorMode === opt.id
              ? 'border-primary bg-primary/10 text-foreground'
              : 'border-border text-muted-foreground hover:bg-muted/40',
          )
        "
        :title="opt.desc"
      >
        <input v-model="editorMode" type="radio" class="sr-only" :value="opt.id" />
        <span class="font-medium">{{ opt.label }}</span>
      </label>
    </div>
  </div>
</template>
