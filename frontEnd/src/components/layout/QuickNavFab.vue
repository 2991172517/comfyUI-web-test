<script setup>
import { ref } from 'vue'
import { openGlobalPromptModal } from '@/composables/useGlobalPromptModal.js'
import { openModelImportModal } from '@/composables/useModelImportModal.js'
import { onClickOutside } from '@vueuse/core'
import { Menu, X, FileText, Download, Settings2 } from 'lucide-vue-next'
import Button from '@/components/ui/Button.vue'
import { useRouter } from 'vue-router'

const open = ref(false)
const rootRef = ref(null)
const router = useRouter()

onClickOutside(rootRef, () => {
  open.value = false
})

function toggle() {
  open.value = !open.value
}

function close() {
  open.value = false
}

const menuItemClass =
  'flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm text-foreground transition-colors hover:bg-accent text-left'
</script>

<template>
  <Teleport to="body">
    <div ref="rootRef" class="fixed bottom-6 right-6 z-50 flex flex-col items-end gap-2">
      <div
        v-if="open"
        class="w-56 rounded-lg border border-border bg-card shadow-xl py-1"
        role="menu"
      >
        <button
          type="button"
          :class="menuItemClass"
          role="menuitem"
          @click="
            openGlobalPromptModal('global');
            close();
          "
        >
          <FileText class="h-4 w-4 shrink-0 text-primary" />
          全局提示词设置
        </button>
        <button
          type="button"
          :class="menuItemClass"
          role="menuitem"
          @click="
            openModelImportModal();
            close();
          "
        >
          <Download class="h-4 w-4 shrink-0 text-primary" />
          粘贴链接导入
        </button>
        <button
          type="button"
          :class="menuItemClass"
          role="menuitem"
          @click="
            router.push('/settings/magnifier');
            close();
          "
        >
          <Settings2 class="h-4 w-4 shrink-0 text-primary" />
          全局配置
        </button>
      </div>

      <Button
        type="button"
        variant="default"
        size="icon"
        class="h-12 w-12 rounded-full shadow-lg"
        :title="open ? '关闭菜单' : '快捷菜单'"
        aria-label="快捷菜单"
        :aria-expanded="open"
        @click="toggle"
      >
        <X v-if="open" class="h-5 w-5" />
        <Menu v-else class="h-5 w-5" />
      </Button>
    </div>
  </Teleport>
</template>
