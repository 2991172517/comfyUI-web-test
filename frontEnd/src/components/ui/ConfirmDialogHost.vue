<script setup>
import { AlertTriangle } from 'lucide-vue-next'
import { useConfirmDialog } from '@/composables/useConfirmDialog.js'
import { useModalMotion } from '@/composables/useModalMotion.js'
import Button from '@/components/ui/Button.vue'
import { cn } from '@/lib/utils'
import { ref } from 'vue'

const { open, options, accept, dismiss } = useConfirmDialog()
const backdropRef = ref(null)
const dialogRef = ref(null)

useModalMotion(open, backdropRef, dialogRef)

function onBackdrop(e) {
  if (e.target === e.currentTarget) dismiss()
}
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open"
      ref="backdropRef"
      class="fixed inset-0 z-[100] flex items-center justify-center bg-black/55 p-4 backdrop-blur-sm"
      @click="onBackdrop"
    >
      <div
        ref="dialogRef"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="confirm-dialog-title"
        aria-describedby="confirm-dialog-desc"
        class="w-full max-w-md overflow-hidden rounded-xl border border-border bg-card shadow-2xl"
        @click.stop
      >
        <div class="flex gap-3 px-5 pt-5">
          <div
            :class="
              cn(
                'flex h-10 w-10 shrink-0 items-center justify-center rounded-full',
                options.variant === 'destructive'
                  ? 'bg-destructive/15 text-destructive'
                  : 'bg-primary/15 text-primary',
              )
            "
          >
            <AlertTriangle class="h-5 w-5" />
          </div>
          <div class="min-w-0 space-y-1.5 pb-1">
            <h2 id="confirm-dialog-title" class="text-base font-semibold text-foreground">
              {{ options.title }}
            </h2>
            <p
              v-if="options.message"
              id="confirm-dialog-desc"
              class="text-sm leading-relaxed text-muted-foreground whitespace-pre-wrap"
            >
              {{ options.message }}
            </p>
          </div>
        </div>

        <div class="flex flex-wrap justify-end gap-2 border-t border-border bg-muted/20 px-5 py-4">
          <Button variant="outline" size="sm" @click="dismiss">
            {{ options.cancelText }}
          </Button>
          <Button
            size="sm"
            :variant="options.variant === 'destructive' ? 'destructive' : 'default'"
            @click="accept"
          >
            {{ options.confirmText }}
          </Button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
