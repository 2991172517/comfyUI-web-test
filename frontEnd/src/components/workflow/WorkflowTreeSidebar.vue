<script setup>
import { computed, ref, watch } from 'vue'
import { ChevronDown, ChevronRight, GitBranch, Layers } from 'lucide-vue-next'
import Badge from '@/components/ui/Badge.vue'
import { cn } from '@/lib/utils'

const props = defineProps({
  workflows: { type: Array, default: () => [] },
  selectedId: { type: String, default: '' },
})

const emit = defineEmits(['select'])

const expanded = ref(new Set())

const tree = computed(() => {
  const list = (props.workflows || []).filter((w) => w.format === 'api')
  const masters = list.filter((w) => !w.is_variant)
  const variants = list.filter((w) => w.is_variant)
  const masterIds = new Set(masters.map((m) => m.id))

  const nodes = masters.map((m) => ({
    ...m,
    children: variants.filter((v) => v.template_id === m.id),
  }))

  const orphans = variants.filter((v) => !masterIds.has(v.template_id))
  if (orphans.length) {
    nodes.push({
      id: '__orphans__',
      display_name: '未关联母版',
      is_master: false,
      is_variant: false,
      is_group: true,
      children: orphans,
    })
  }

  return nodes
})

watch(
  tree,
  (nodes) => {
    const next = new Set(expanded.value)
    for (const n of nodes) {
      if (n.id !== '__orphans__') next.add(n.id)
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
  if (!id || id === '__orphans__') return
  emit('select', id)
}

function isExpanded(id) {
  return expanded.value.has(id)
}
</script>

<template>
  <nav class="space-y-1 text-sm" aria-label="工作流树">
    <div v-for="node in tree" :key="node.id" class="space-y-0.5">
      <div class="flex items-stretch gap-0.5">
        <button
          type="button"
          class="flex h-9 w-7 shrink-0 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-foreground"
          :aria-label="isExpanded(node.id) ? '收起' : '展开'"
          @click.stop="toggleExpand(node.id)"
        >
          <ChevronDown v-if="isExpanded(node.id)" class="h-4 w-4" />
          <ChevronRight v-else class="h-4 w-4" />
        </button>
        <button
          type="button"
          :class="
            cn(
              'flex min-w-0 flex-1 items-center gap-2 rounded-md border px-2.5 py-2 text-left transition-colors',
              selectedId === node.id
                ? 'border-primary bg-primary/10'
                : 'border-transparent hover:bg-accent/80',
            )
          "
          @click="pick(node.id)"
        >
          <Layers class="h-4 w-4 shrink-0 text-primary/80" />
          <span class="min-w-0 flex-1 truncate font-medium">
            {{ node.display_name || node.name || node.id }}
          </span>
          <Badge v-if="node.is_master" variant="secondary" class="shrink-0 text-[10px]">母版</Badge>
        </button>
      </div>

      <div v-if="isExpanded(node.id)" class="ml-3 space-y-0.5 border-l border-border/70 pl-2">
        <button
          v-for="child in node.children"
          :key="child.id"
          type="button"
          :class="
            cn(
              'flex w-full items-center gap-2 rounded-md border px-2.5 py-2 text-left transition-colors',
              selectedId === child.id
                ? 'border-primary bg-primary/10'
                : 'border-transparent hover:bg-accent/80',
            )
          "
          @click="pick(child.id)"
        >
          <GitBranch class="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
          <span class="min-w-0 flex-1 truncate">{{ child.display_name || child.name || child.id }}</span>
          <Badge variant="outline" class="shrink-0 text-[10px]">子</Badge>
        </button>
        <p
          v-if="!node.children?.length && !node.is_group"
          class="px-2 py-1.5 text-xs text-muted-foreground"
        >
          暂无子工作流
        </p>
      </div>
    </div>

    <p v-if="!tree.length" class="px-2 py-6 text-center text-xs text-muted-foreground">
      暂无工作流，请导入或新建。
    </p>
  </nav>
</template>
