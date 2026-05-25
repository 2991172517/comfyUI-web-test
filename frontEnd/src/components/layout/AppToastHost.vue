<script setup>
import { onUnmounted, ref, watch } from 'vue'
import { X } from 'lucide-vue-next'
import { useAppStore } from '@/stores/useAppStore.js'
import { cn } from '@/lib/utils'

const store = useAppStore()
let dismissTimer = null

function clearDismissTimer() {
  if (dismissTimer) {
    clearTimeout(dismissTimer)
    dismissTimer = null
  }
}

function dismiss() {
  clearDismissTimer()
  store.message = ''
  store.error = ''
}

function scheduleDismiss(isError) {
  clearDismissTimer()
  if (!store.message) return
  const ms = isError ? 12_000 : 5_500
  dismissTimer = setTimeout(dismiss, ms)
}

watch(
  () => store.message,
  (msg) => {
    clearDismissTimer()
    if (!msg) return
    scheduleDismiss(!!store.error)
  },
)

onUnmounted(clearDismissTimer)
</script>

<template>
  <Teleport to="body">
    <Transition
      enter-active-class="transition duration-200 ease-out"
      enter-from-class="opacity-0 -translate-y-2"
      enter-to-class="opacity-100 translate-y-0"
      leave-active-class="transition duration-150 ease-in"
      leave-from-class="opacity-100 translate-y-0"
      leave-to-class="opacity-0 -translate-y-2"
    >
      <div
        v-if="store.message"
        class="fixed left-1/2 top-16 z-[200] w-[min(92vw,28rem)] -translate-x-1/2 pointer-events-none"
        role="status"
        aria-live="polite"
      >
        <div
          :class="
            cn(
              'pointer-events-auto flex items-start gap-3 rounded-lg border px-4 py-3 shadow-lg backdrop-blur-md',
              store.error
                ? 'border-destructive/50 bg-destructive/95 text-destructive-foreground'
                : 'border-border/80 bg-card/95 text-foreground',
            )
          "
        >
          <p class="flex-1 text-sm leading-snug break-words">{{ store.message }}</p>
          <button
            type="button"
            class="shrink-0 rounded-md p-1 opacity-80 hover:opacity-100"
            aria-label="关闭提示"
            @click="dismiss"
          >
            <X class="h-4 w-4" />
          </button>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
