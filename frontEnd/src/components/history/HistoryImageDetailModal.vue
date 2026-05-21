<script setup>
import { computed } from 'vue'
import HistoryMetaPanel from '@/components/history/HistoryMetaPanel.vue'
import Button from '@/components/ui/Button.vue'
import { X } from 'lucide-vue-next'

const props = defineProps({
  open: { type: Boolean, default: false },
  meta: { type: Object, default: null },
  title: { type: String, default: '生成参数详情' },
  imageUrl: { type: String, default: '' },
})

const emit = defineEmits(['close'])

const subtitle = computed(() => {
  const m = props.meta
  if (!m) return ''
  const parts = []
  if (m.index != null) parts.push(`#${m.index}`)
  if (m.ia != null && m.ib != null) parts.push(`A${m.ia}×B${m.ib}`)
  if (m.label) parts.push(m.label)
  return parts.join(' · ')
})

function onBackdrop(e) {
  if (e.target === e.currentTarget) emit('close')
}
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open && meta"
      class="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm"
      @click="onBackdrop"
    >
      <div
        class="flex max-h-[min(90vh,900px)] w-full max-w-2xl flex-col overflow-hidden rounded-xl border border-border bg-card shadow-xl"
        role="dialog"
        aria-modal="true"
        @click.stop
      >
        <header
          class="flex shrink-0 items-start justify-between gap-3 border-b border-border px-4 py-3"
        >
          <div class="min-w-0">
            <h2 class="text-base font-semibold">{{ title }}</h2>
            <p v-if="subtitle" class="mt-0.5 truncate text-xs text-muted-foreground">
              {{ subtitle }}
            </p>
          </div>
          <Button variant="ghost" size="sm" class="h-8 w-8 shrink-0 p-0" @click="emit('close')">
            <X class="h-4 w-4" />
          </Button>
        </header>

        <div class="min-h-0 flex-1 overflow-y-auto p-4 space-y-4">
          <div
            v-if="imageUrl"
            class="flex max-h-48 items-center justify-center rounded-lg border border-border bg-muted/20 p-2"
          >
            <img :src="imageUrl" class="max-h-44 max-w-full object-contain" alt="" />
          </div>

          <HistoryMetaPanel
            :meta="meta"
            :workflow-id="meta.workflow_id"
            :compact="false"
            prompts-open
          />
        </div>

        <footer class="shrink-0 border-t border-border px-4 py-3 text-right">
          <Button variant="outline" size="sm" @click="emit('close')">关闭</Button>
        </footer>
      </div>
    </div>
  </Teleport>
</template>
