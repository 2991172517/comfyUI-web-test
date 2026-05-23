<script setup>
import { Teleport, nextTick, ref, watch } from 'vue'

const props = defineProps({
  open: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
  items: { type: Array, default: () => [] },
  selectedIndex: { type: Number, default: 0 },
  position: { type: Object, default: () => ({ top: 0, left: 0 }) },
})

const emit = defineEmits(['select', 'close'])

const listRef = ref(null)

async function scrollSelectedIntoView() {
  await nextTick()
  const container = listRef.value
  if (!container) return
  const selected = container.querySelector('[aria-selected="true"]')
  selected?.scrollIntoView({ block: 'nearest', inline: 'nearest' })
}

watch(
  () => props.selectedIndex,
  () => {
    if (props.open) scrollSelectedIntoView()
  },
)

watch(
  () => [props.open, props.items.length],
  ([isOpen]) => {
    if (isOpen) scrollSelectedIntoView()
  },
)
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open"
      ref="listRef"
      data-prompt-autocomplete
      class="fixed z-[9999] w-80 max-h-56 overflow-y-auto rounded-md border border-border bg-popover text-popover-foreground shadow-lg"
      :style="{ top: `${position.top}px`, left: `${position.left}px` }"
      role="listbox"
      @mousedown.prevent
    >
      <div
        v-if="loading && items.length === 0"
        class="px-3 py-2 text-xs text-muted-foreground"
      >
        匹配中…
      </div>
      <template v-else-if="items.length">
        <button
          v-for="(item, index) in items"
          :key="`${item.insertText || item.insert_text}-${index}`"
          type="button"
          role="option"
          class="flex w-full flex-col items-start gap-0.5 px-3 py-2 text-left text-xs hover:bg-accent"
          :class="index === selectedIndex ? 'bg-accent' : ''"
          :aria-selected="index === selectedIndex"
          @click="emit('select', index)"
        >
          <span class="font-mono text-foreground">{{ item.insertText || item.insert_text }}</span>
          <span
            v-if="item.label && item.label !== (item.insertText || item.insert_text)"
            class="text-muted-foreground"
          >
            {{ item.label }}
            <span v-if="item.category" class="ml-1 opacity-70">· {{ item.category }}</span>
          </span>
        </button>
      </template>
      <div v-else class="px-3 py-2 text-xs text-muted-foreground">无匹配</div>
    </div>
  </Teleport>
</template>
