<script setup>
import { computed, ref, watch } from 'vue'
import { ChevronDown, ChevronRight, GitBranch } from 'lucide-vue-next'
import Badge from '@/components/ui/Badge.vue'
import { WORKFLOW_CATEGORIES, normalizeCategory } from '@/lib/workflowCategories.js'
import { cn } from '@/lib/utils'

const props = defineProps({
  workflows: { type: Array, default: () => [] },
  selectedId: { type: String, default: '' },
})

const emit = defineEmits(['select'])

const expanded = ref(new Set(WORKFLOW_CATEGORIES.map((c) => c.id)))

const tree = computed(() => {
  const list = (props.workflows || []).filter((w) => w.format === 'api' && w.is_variant)
  return WORKFLOW_CATEGORIES.map((cat) => ({
    ...cat,
    children: list.filter((w) => normalizeCategory(w.category) === cat.id),
  })).filter((g) => g.children.length > 0)
})

watch(
  tree,
  (groups) => {
    const next = new Set(expanded.value)
    for (const g of groups) {
      if (g.children.length) next.add(g.id)
    }
    expanded.value = next
  },
  { immediate: true },
)

function toggleExpand(id) {
  const next = new Set(expanded.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  expanded.value = next
}

function pick(id) {
  if (!id) return
  emit('select', id)
}

function isExpanded(id) {
  return expanded.value.has(id)
}
</script>

<template>
  <nav class="space-y-1 text-sm" aria-label="工作流列表">
    <div v-for="group in tree" :key="group.id" class="space-y-0.5">
      <div class="flex items-stretch gap-0.5">
        <button
          type="button"
          class="flex h-9 w-7 shrink-0 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-foreground"
          :aria-label="isExpanded(group.id) ? '收起' : '展开'"
          @click.stop="toggleExpand(group.id)"
        >
          <ChevronDown v-if="isExpanded(group.id)" class="h-4 w-4" />
          <ChevronRight v-else class="h-4 w-4" />
        </button>
        <div
          class="flex min-w-0 flex-1 items-center gap-2 rounded-md border border-transparent px-2.5 py-2 font-medium text-muted-foreground"
        >
          {{ group.label }}
          <Badge variant="outline" class="shrink-0 text-[10px] tabular-nums">
            {{ group.children.length }}
          </Badge>
        </div>
      </div>

      <div v-if="isExpanded(group.id)" class="ml-3 space-y-0.5 border-l border-border/70 pl-2">
        <button
          v-for="w in group.children"
          :key="w.id"
          type="button"
          :class="
            cn(
              'flex w-full items-center gap-2 rounded-md border px-2.5 py-2 text-left transition-colors',
              selectedId === w.id
                ? 'border-primary bg-primary/10'
                : 'border-transparent hover:bg-accent/80',
            )
          "
          @click="pick(w.id)"
        >
          <GitBranch class="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
          <span class="min-w-0 flex-1 truncate">{{ w.display_name || w.name || w.id }}</span>
        </button>
        <p v-if="!group.children.length" class="px-2 py-1.5 text-xs text-muted-foreground">
          暂无工作流
        </p>
      </div>
    </div>

    <p v-if="!tree.length" class="px-2 py-6 text-center text-xs text-muted-foreground">
      暂无工作流，请新建或导入。
    </p>
  </nav>
</template>
