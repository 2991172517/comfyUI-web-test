<script setup>
import { ref, watch } from 'vue'
import { X } from 'lucide-vue-next'
import { useModalMotion } from '@/composables/useModalMotion.js'
import { useAppStore } from '@/stores/useAppStore.js'
import { useCheckpointLoraCompat } from '@/composables/useCheckpointLoraCompat.js'
import LoraModelPicker from '@/components/models/LoraModelPicker.vue'
import Button from '@/components/ui/Button.vue'

const open = defineModel('open', { type: Boolean, default: false })

const emit = defineEmits(['pick'])

const app = useAppStore()
const picked = ref('')
const backdropRef = ref(null)
const panelRef = ref(null)

const loraCompat = useCheckpointLoraCompat(() => app.activeCheckpointName)

useModalMotion(open, backdropRef, panelRef)

watch(open, (v) => {
  if (v) picked.value = ''
})

function close() {
  open.value = false
}

function onBackdrop(e) {
  if (e.target === e.currentTarget) close()
}

function confirm() {
  const name = picked.value?.trim()
  if (!name || name === 'None') return
  emit('pick', name)
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
        class="flex max-h-[min(88vh,640px)] w-full max-w-lg flex-col overflow-hidden rounded-t-xl border border-border bg-card shadow-xl sm:rounded-xl"
        role="dialog"
        aria-modal="true"
        aria-labelledby="lora-pick-title"
        @click.stop
      >
        <header class="flex shrink-0 items-center justify-between gap-3 border-b border-border px-4 py-3">
          <div>
            <h2 id="lora-pick-title" class="text-base font-semibold">选择 LoRA</h2>
            <p class="mt-0.5 text-[11px] text-muted-foreground">选定后将加入工作流 LoRA 链</p>
          </div>
          <Button variant="ghost" size="sm" class="h-8 w-8 shrink-0 p-0" aria-label="关闭" @click="close">
            <X class="h-4 w-4" />
          </Button>
        </header>
        <div class="min-h-0 flex-1 overflow-y-auto p-4">
          <LoraModelPicker
            v-model="picked"
            label="LoRA 模型"
            :options="app.modelLists.loras"
            :catalog="app.modelLists.loraCatalog"
            :lora-compat-map="loraCompat.compatMap"
            :loading="app.modelsLoading"
            :disabled="app.modelsLoading"
          />
        </div>
        <footer class="flex shrink-0 justify-end gap-2 border-t border-border px-4 py-3">
          <Button variant="ghost" size="sm" @click="close">取消</Button>
          <Button size="sm" :disabled="!picked || picked === 'None'" @click="confirm">添加</Button>
        </footer>
      </div>
    </div>
  </Teleport>
</template>
