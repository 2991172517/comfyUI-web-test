<script setup>
import { ref } from 'vue'
import { X } from 'lucide-vue-next'
import Button from '@/components/ui/Button.vue'
import ModelImportPanel from '@/components/models/ModelImportPanel.vue'
import { useModelImportModal } from '@/composables/useModelImportModal.js'
import { useModalMotion } from '@/composables/useModalMotion.js'

const { open, close, initialUrl } = useModelImportModal()
const backdropRef = ref(null)
const panelRef = ref(null)

useModalMotion(open, backdropRef, panelRef)

function onBackdrop(e) {
  if (e.target === e.currentTarget) close()
}
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open"
      ref="backdropRef"
      class="fixed inset-0 z-[90] flex items-end justify-center sm:items-center bg-black/50 p-0 sm:p-4 backdrop-blur-sm"
      @click="onBackdrop"
    >
      <div
        ref="panelRef"
        class="flex max-h-[min(92vh,860px)] w-full max-w-4xl flex-col overflow-hidden rounded-t-xl sm:rounded-xl border border-border bg-card shadow-xl"
        role="dialog"
        aria-modal="true"
        aria-labelledby="model-import-title"
        @click.stop
      >
        <header
          class="flex shrink-0 items-center justify-between gap-3 border-b border-border px-4 py-3 sm:px-5"
        >
          <div>
            <h2 id="model-import-title" class="text-base font-semibold text-foreground">
              模型下载
            </h2>
            <p class="text-[11px] text-muted-foreground mt-0.5">
              Civitai / Shakker 链接解析、下载模型并写入说明与参考图
            </p>
          </div>
          <Button variant="ghost" size="sm" class="h-8 w-8 p-0 shrink-0" aria-label="关闭" @click="close">
            <X class="h-4 w-4" />
          </Button>
        </header>

        <div class="min-h-0 flex-1 overflow-y-auto px-4 py-4 sm:px-5">
          <ModelImportPanel :initial-url="initialUrl" />
        </div>
      </div>
    </div>
  </Teleport>
</template>
