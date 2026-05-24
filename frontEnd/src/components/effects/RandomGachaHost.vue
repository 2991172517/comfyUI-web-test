<script setup>
import { Sparkles, X } from 'lucide-vue-next'
import { useRandomGachaOverlay } from '@/composables/useRandomGachaOverlay.js'
import { useModalMotion } from '@/composables/useModalMotion.js'
import { ref } from 'vue'
import Button from '@/components/ui/Button.vue'
import '@/assets/random-gacha.css'

const {
  open,
  panelRef,
  gachaTitle,
  gachaSubtitle,
  manualClose,
  canClose,
  closeOverlay,
} = useRandomGachaOverlay()
const backdropRef = ref(null)
const cardRef = ref(null)

useModalMotion(open, backdropRef, cardRef)
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open"
      ref="backdropRef"
      class="random-gacha-backdrop fixed inset-0 z-[95] flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm"
      aria-hidden="true"
    >
      <div
        ref="cardRef"
        class="random-gacha-panel bg-card flex max-h-[min(85vh,640px)] w-full max-w-2xl flex-col overflow-hidden rounded-xl"
        role="dialog"
        aria-modal="true"
        aria-labelledby="random-gacha-title"
        @click.stop
      >
        <div
          class="random-gacha-panel__header bg-card flex shrink-0 items-center gap-2 border-b border-border/60 px-4 py-3"
        >
          <div
            class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary/15 text-primary"
          >
            <Sparkles class="h-4 w-4" />
          </div>
          <div class="min-w-0 flex-1">
            <h2 id="random-gacha-title" class="text-sm font-semibold text-foreground">
              {{ gachaTitle }}
            </h2>
            <p class="text-xs text-muted-foreground">{{ gachaSubtitle }}</p>
          </div>
          <Button
            v-if="manualClose"
            variant="ghost"
            size="sm"
            class="h-8 shrink-0 gap-1 px-2"
            :disabled="!canClose"
            @click="closeOverlay"
          >
            <X class="h-4 w-4" />
            关闭
          </Button>
        </div>

        <div
          ref="panelRef"
          class="random-gacha-body bg-card min-h-0 flex-1 overflow-y-auto overscroll-y-contain px-4 py-3"
          data-gacha-panel
        >
          <div class="random-gacha-well">
            <div data-gacha-rows class="flex flex-col gap-3" />
          </div>
        </div>

        <div
          v-if="manualClose && canClose"
          class="flex shrink-0 justify-end border-t border-border/60 bg-card px-4 py-3"
        >
          <Button size="sm" @click="closeOverlay">关闭</Button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
