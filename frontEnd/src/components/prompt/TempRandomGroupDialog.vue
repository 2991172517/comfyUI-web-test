<script setup>
import { ref, toRef, watch } from 'vue'
import { X } from 'lucide-vue-next'
import { useAppStore } from '@/stores/useAppStore.js'
import { newRandomGroup } from '@/composables/usePromptConfig.js'
import { useModalMotion } from '@/composables/useModalMotion.js'
import Button from '@/components/ui/Button.vue'
import PromptConfigEditor from '@/components/prompt/PromptConfigEditor.vue'

const props = defineProps({
  open: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
})

const emit = defineEmits(['update:open', 'save-preset'])

const app = useAppStore()
const backdropRef = ref(null)
const panelRef = ref(null)

useModalMotion(toRef(() => props.open), backdropRef, panelRef)

function close() {
  emit('update:open', false)
}

function onBackdrop(e) {
  if (e.target === e.currentTarget) close()
}

function ensureGroup() {
  if (!app.sessionPrompts.random_groups.length) {
    app.sessionPrompts.random_groups.push(newRandomGroup())
  }
}

watch(
  () => props.open,
  (v) => {
    if (v) ensureGroup()
  },
)
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open"
      ref="backdropRef"
      class="fixed inset-0 z-[95] flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm"
      @click="onBackdrop"
    >
      <div
        ref="panelRef"
        class="flex max-h-[min(90vh,820px)] w-full max-w-2xl flex-col rounded-xl border border-border bg-card shadow-xl"
        role="dialog"
        aria-modal="true"
        aria-labelledby="temp-random-group-title"
        @click.stop
      >
        <header class="flex shrink-0 items-center justify-between gap-3 border-b border-border px-4 py-3">
          <div>
            <h2 id="temp-random-group-title" class="text-base font-semibold">临时随机组</h2>
            <p class="mt-0.5 text-xs text-muted-foreground">仅当次生成有效，无需导入预设</p>
          </div>
          <Button variant="ghost" size="sm" class="h-8 w-8 p-0" @click="close">
            <X class="h-4 w-4" />
          </Button>
        </header>

        <div class="min-h-0 flex-1 space-y-4 overflow-y-auto px-4 py-4">
          <PromptConfigEditor
            :fixed="app.sessionPrompts.fixed"
            :random-groups="app.sessionPrompts.random_groups"
            :disabled="disabled"
            compact
            :show-fixed="false"
            :show-random="true"
            @update:fixed="app.sessionPrompts.fixed = $event"
            @update:random-groups="app.sessionPrompts.random_groups = $event"
          />

          <div class="flex flex-wrap gap-3 text-sm">
            <label class="flex items-center gap-1.5">
              <input
                v-model="app.sessionPrompts.merge.global_before_workflow"
                type="checkbox"
                class="accent-primary"
                :disabled="disabled"
              />
              全局全文在工作流底稿前
            </label>
            <label class="flex items-center gap-1.5">
              <input
                v-model="app.sessionPrompts.merge.random_before_workflow"
                type="checkbox"
                class="accent-primary"
                :disabled="disabled"
              />
              随机词在工作流底稿前
            </label>
          </div>
        </div>

        <footer class="flex shrink-0 justify-end gap-2 border-t border-border px-4 py-3">
          <Button variant="outline" size="sm" :disabled="disabled" @click="emit('save-preset')">
            保存为预设…
          </Button>
          <Button size="sm" @click="close">完成</Button>
        </footer>
      </div>
    </div>
  </Teleport>
</template>
