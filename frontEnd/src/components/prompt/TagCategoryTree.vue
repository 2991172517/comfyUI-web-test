<script setup>
import { cn } from '@/lib/utils'
import { ChevronRight, Trash2 } from 'lucide-vue-next'

const props = defineProps({
  nodes: { type: Array, default: () => [] },
  selectedId: { type: String, default: '' },
  depth: { type: Number, default: 0 },
  /** 显示删除分类按钮 */
  manageable: { type: Boolean, default: false },
  /** 已展开的分类 id */
  expandedIds: { type: Object, default: () => ({}) },
})

const emit = defineEmits(['select', 'delete', 'toggle-expand'])

function hasChildren(node) {
  return (node.children?.length ?? 0) > 0
}

function isExpanded(id) {
  return props.expandedIds[id] === true
}

function onToggleExpand(node, event) {
  event.stopPropagation()
  emit('toggle-expand', node.id)
}

function onSelect(node) {
  emit('select', node.id)
  if (hasChildren(node) && !isExpanded(node.id)) {
    emit('toggle-expand', node.id)
  }
}
</script>

<template>
  <ul :class="depth ? 'ml-3 border-l border-border/50 pl-2' : 'space-y-0.5'">
    <li v-for="node in nodes" :key="node.id">
      <div class="group flex items-center gap-0.5">
        <button
          v-if="hasChildren(node)"
          type="button"
          class="inline-flex h-6 w-5 shrink-0 items-center justify-center rounded text-muted-foreground hover:bg-muted/60 hover:text-foreground"
          :aria-label="isExpanded(node.id) ? '收起' : '展开'"
          @click="onToggleExpand(node, $event)"
        >
          <ChevronRight
            class="h-3.5 w-3.5 transition-transform duration-150"
            :class="isExpanded(node.id) ? 'rotate-90' : ''"
          />
        </button>
        <span
          v-else
          class="inline-block h-6 w-5 shrink-0"
          aria-hidden="true"
        />

        <button
          type="button"
          class="min-w-0 flex-1 rounded px-2 py-1 text-left text-xs transition-colors truncate"
          :class="
            cn(
              selectedId === node.id
                ? 'bg-primary/15 text-primary font-medium'
                : 'text-foreground hover:bg-muted/50',
            )
          "
          :title="node.name"
          @click="onSelect(node)"
        >
          {{ node.name }}
        </button>

        <button
          v-if="manageable"
          type="button"
          class="inline-flex h-6 w-6 shrink-0 items-center justify-center rounded text-muted-foreground opacity-0 transition-opacity hover:bg-destructive/10 hover:text-destructive group-hover:opacity-100 focus:opacity-100"
          :title="`删除分类「${node.name}」`"
          aria-label="删除分类"
          @click.stop="emit('delete', node)"
        >
          <Trash2 class="h-3 w-3" />
        </button>
      </div>

      <TagCategoryTree
        v-if="hasChildren(node) && isExpanded(node.id)"
        :nodes="node.children"
        :selected-id="selectedId"
        :depth="depth + 1"
        :manageable="manageable"
        :expanded-ids="expandedIds"
        @select="emit('select', $event)"
        @delete="emit('delete', $event)"
        @toggle-expand="emit('toggle-expand', $event)"
      />
    </li>
  </ul>
</template>
