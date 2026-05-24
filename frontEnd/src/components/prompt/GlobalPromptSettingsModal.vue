<script setup>
import { ref } from 'vue'
import { X } from 'lucide-vue-next'
import Button from '@/components/ui/Button.vue'
import PromptSettingsPanel from '@/components/prompt/PromptSettingsPanel.vue'
import { useGlobalPromptModal } from '@/composables/useGlobalPromptModal.js'
import { useModalMotion } from '@/composables/useModalMotion.js'

const { open, activeTab, close } = useGlobalPromptModal()
const settingsPanelRef = ref(null)
const backdropRef = ref(null)
const dialogRef = ref(null)
const closing = ref(false)

useModalMotion(open, backdropRef, dialogRef)

async function requestClose() {
  if (closing.value) return
  closing.value = true
  try {
    await settingsPanelRef.value?.flushPendingSaves?.()
  } finally {
    closing.value = false
    close()
  }
}

function onBackdrop(e) {
  if (e.target === e.currentTarget) requestClose()
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
        ref="dialogRef"
        class="flex max-h-[min(92vh,800px)] w-full max-w-4xl flex-col overflow-hidden rounded-t-xl sm:rounded-xl border border-border bg-card shadow-xl"
        role="dialog"
        aria-modal="true"
        aria-labelledby="global-prompt-settings-title"
        @click.stop
      >
        <header
          class="flex shrink-0 items-center justify-between gap-3 border-b border-border px-4 py-3 sm:px-5"
        >
          <div>
            <h2 id="global-prompt-settings-title" class="text-base font-semibold text-foreground">
              提示词设置
            </h2>
            <p class="text-[11px] text-muted-foreground mt-0.5">
              全局提示词、随机池与预设库；停止编辑约 0.7 秒后自动保存，关闭前会提交未保存改动
            </p>
          </div>
          <Button
            variant="ghost"
            size="sm"
            class="h-8 w-8 p-0 shrink-0"
            aria-label="关闭"
            :disabled="closing"
            @click="requestClose"
          >
            <X class="h-4 w-4" />
          </Button>
        </header>

        <div class="min-h-0 flex-1 overflow-y-auto px-4 py-4 sm:px-5">
          <PromptSettingsPanel ref="settingsPanelRef" v-model="activeTab" compact />
        </div>
      </div>
    </div>
  </Teleport>
</template>
