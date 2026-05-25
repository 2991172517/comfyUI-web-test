<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { ChevronDown, GitBranch } from 'lucide-vue-next'
import { getWorkflowPipelineGuide } from '@/lib/workflowPipelineGuides.js'
import { cn } from '@/lib/utils'

const props = defineProps({
  workflowId: { type: String, default: '' },
  defaultOpen: { type: Boolean, default: true },
})

const guide = computed(() => getWorkflowPipelineGuide(props.workflowId))
</script>

<template>
  <details
    v-if="guide"
    :open="defaultOpen"
    :class="
      cn(
        'group rounded-lg border border-primary/20 bg-primary/5',
      )
    "
  >
    <summary
      class="flex cursor-pointer list-none items-center gap-2 px-4 py-3 text-sm font-medium text-foreground [&::-webkit-details-marker]:hidden"
    >
      <GitBranch class="h-4 w-4 shrink-0 text-primary" />
      <span class="flex-1">{{ guide.title }}</span>
      <ChevronDown
        class="h-4 w-4 shrink-0 text-muted-foreground transition-transform group-open:rotate-180"
      />
    </summary>

    <div class="space-y-3 border-t border-primary/15 px-4 pb-4 pt-2">
      <ol class="space-y-2.5">
        <li
          v-for="(step, i) in guide.steps"
          :key="i"
          class="text-sm leading-relaxed"
        >
          <span class="font-medium text-foreground">{{ step.label }}</span>
          <span class="text-muted-foreground"> — {{ step.text }}</span>
        </li>
      </ol>

      <ul
        v-if="guide.notes?.length"
        class="space-y-1.5 rounded-md border border-border/60 bg-background/60 px-3 py-2 text-xs text-muted-foreground leading-relaxed"
      >
        <li v-for="(note, j) in guide.notes" :key="j">· {{ note }}</li>
      </ul>

      <RouterLink
        v-if="guide.link"
        :to="guide.link.to"
        class="inline-block text-xs font-medium text-primary hover:underline"
      >
        {{ guide.link.label }} →
      </RouterLink>
    </div>
  </details>
</template>
