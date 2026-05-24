<script setup>
import { ref } from 'vue'
import { X } from 'lucide-vue-next'
import { useModalMotion } from '@/composables/useModalMotion.js'
import WorkflowImportModal from '@/components/workflow/WorkflowImportModal.vue'
import Button from '@/components/ui/Button.vue'

const open = defineModel('open', { type: Boolean, default: false })

const emit = defineEmits(['imported'])

const backdropRef = ref(null)
const panelRef = ref(null)
useModalMotion(open, backdropRef, panelRef)

function close() {
  open.value = false
}

function onBackdrop(e) {
  if (e.target === e.currentTarget) close()
}

function onImported(res) {
  emit('imported', res)
  close()
}
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open"
      ref="backdropRef"
      class="fixed inset-0 z-[90] flex items-end justify-center bg-black/50 p-0 backdrop-blur-sm sm:items-center sm:p-4"
      @click="onBackdrop"
    >
      <div
        ref="panelRef"
        class="flex max-h-[min(92vh,720px)] w-full max-w-lg flex-col overflow-hidden rounded-t-xl border border-border bg-card shadow-xl sm:rounded-xl"
        role="dialog"
        aria-modal="true"
        aria-labelledby="workflow-import-title"
        @click.stop
      >
        <header class="flex shrink-0 items-center justify-between gap-3 border-b border-border px-4 py-3">
          <div>
            <h2 id="workflow-import-title" class="text-base font-semibold">导入工作流</h2>
            <p class="mt-0.5 text-[11px] text-muted-foreground">
              支持 ComfyUI API JSON，或带 prompt 元数据的 PNG 图片
            </p>
          </div>
          <Button variant="ghost" size="sm" class="h-8 w-8 shrink-0 p-0" aria-label="关闭" @click="close">
            <X class="h-4 w-4" />
          </Button>
        </header>
        <div class="min-h-0 flex-1 overflow-y-auto p-4">
          <WorkflowImportModal @imported="onImported" @close="close" />
        </div>
      </div>
    </div>
  </Teleport>
</template>
