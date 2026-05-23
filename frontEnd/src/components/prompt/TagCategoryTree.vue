<script setup>
import { cn } from '@/lib/utils'

defineProps({
  nodes: { type: Array, default: () => [] },
  selectedId: { type: String, default: '' },
  depth: { type: Number, default: 0 },
})

const emit = defineEmits(['select'])
</script>

<template>
  <ul :class="depth ? 'ml-3 border-l border-border/50 pl-2' : 'space-y-0.5'">
    <li v-for="node in nodes" :key="node.id">
      <button
        type="button"
        class="w-full rounded px-2 py-1 text-left text-xs transition-colors truncate"
        :class="
          cn(
            selectedId === node.id
              ? 'bg-primary/15 text-primary font-medium'
              : 'text-foreground hover:bg-muted/50',
          )
        "
        :title="node.name"
        @click="emit('select', node.id)"
      >
        {{ node.name }}
      </button>
      <TagCategoryTree
        v-if="node.children?.length"
        :nodes="node.children"
        :selected-id="selectedId"
        :depth="depth + 1"
        @select="emit('select', $event)"
      />
    </li>
  </ul>
</template>
