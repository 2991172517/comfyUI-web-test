<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { openGlobalPromptModal } from '@/composables/useGlobalPromptModal.js'
import { onClickOutside } from '@vueuse/core'
import {
  Menu,
  X,
  FileText,
  Download,
  FolderOpen,
  ChevronRight,
  Copy,
} from 'lucide-vue-next'
import Button from '@/components/ui/Button.vue'
import { api } from '@/api/client.js'
import { useAppStore } from '@/stores/useAppStore.js'
import { cn } from '@/lib/utils'

const open = ref(false)
const subOpen = ref(false)
const folderPaths = ref({ checkpoints: '', loras: '' })
const opening = ref(null)
const rootRef = ref(null)
const router = useRouter()
const app = useAppStore()
const toast = ref('')
let toastTimer = null

function showToast(text, isError = false) {
  toast.value = text
  app.setMessage(text, isError)
  if (toastTimer) clearTimeout(toastTimer)
  toastTimer = setTimeout(() => {
    toast.value = ''
  }, 3200)
}

onClickOutside(rootRef, () => {
  open.value = false
  subOpen.value = false
})

function toggle() {
  open.value = !open.value
  if (!open.value) subOpen.value = false
}

function close() {
  open.value = false
  subOpen.value = false
}

function navTo(path) {
  close()
  router.push(path)
}

async function ensurePaths() {
  if (folderPaths.value.checkpoints) return
  try {
    const res = await api.getModelFolderPaths()
    folderPaths.value = res.paths || {}
  } catch {
    folderPaths.value = {}
  }
}

async function toggleFolders() {
  if (!open.value) return
  subOpen.value = !subOpen.value
  if (subOpen.value) await ensurePaths()
}

async function openFolder(folder) {
  opening.value = folder
  try {
    const res = await api.openModelFolder(folder)
    if (res.ok && res.opened) {
      const label = folder === 'checkpoints' ? 'Checkpoint' : 'LoRA'
      const behind =
        res.method && !String(res.method).includes('foreground')
          ? '（若被浏览器挡住，请看任务栏闪烁或按 Alt+Tab）'
          : ''
      showToast(`已打开 ${label} 文件夹${behind}`)
      close()
    } else {
      const detail = res.error || res.path || '未知错误'
      showToast(`无法打开文件夹：${detail}`, true)
    }
  } catch (e) {
    showToast(e.message || '打开文件夹失败', true)
  } finally {
    opening.value = null
  }
}

async function copyPath(folder) {
  await ensurePaths()
  const p = folderPaths.value[folder]
  if (!p) {
    showToast('路径不可用', true)
    return
  }
  try {
    await navigator.clipboard.writeText(p)
    showToast('路径已复制到剪贴板')
  } catch {
    showToast(p)
  }
}

const menuItemClass =
  'flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm text-foreground transition-colors hover:bg-accent text-left'
</script>

<template>
  <Teleport to="body">
    <div ref="rootRef" class="fixed bottom-6 right-6 z-50 flex flex-col items-end gap-2">
      <p
        v-if="toast"
        class="max-w-[14rem] rounded-md border border-border bg-card px-3 py-1.5 text-xs text-foreground shadow-lg text-right"
      >
        {{ toast }}
      </p>
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
          提示词设置
        </button>
        <button type="button" :class="menuItemClass" role="menuitem" @click="navTo('/models/import')">
          <Download class="h-4 w-4 shrink-0 text-primary" />
          模型下载
        </button>

        <div class="my-1 border-t border-border" />

        <button
          type="button"
          :class="cn(menuItemClass, 'justify-between')"
          role="menuitem"
          aria-expanded="subOpen"
          @click="toggleFolders"
        >
          <span class="inline-flex items-center gap-2">
            <FolderOpen class="h-4 w-4 shrink-0 text-primary" />
            打开模型目录
          </span>
          <ChevronRight
            class="h-4 w-4 shrink-0 text-muted-foreground transition-transform"
            :class="subOpen ? 'rotate-90' : ''"
          />
        </button>

        <div v-if="subOpen" class="border-t border-border/60 bg-muted/20 py-1">
          <div
            v-for="item in [
              { id: 'checkpoints', label: 'Checkpoint 文件夹' },
              { id: 'loras', label: 'LoRA 文件夹' },
            ]"
            :key="item.id"
            class="flex items-center gap-0.5 pr-1"
          >
            <button
              type="button"
              :class="cn(menuItemClass, 'pl-8 text-xs flex-1')"
              :disabled="opening === item.id"
              @click="openFolder(item.id)"
            >
              {{ item.label }}
            </button>
            <button
              type="button"
              class="rounded p-1.5 text-muted-foreground hover:bg-background hover:text-foreground shrink-0"
              title="复制路径"
              @click="copyPath(item.id)"
            >
              <Copy class="h-3.5 w-3.5" />
            </button>
          </div>
          <p class="px-3 py-1.5 text-[10px] leading-snug text-muted-foreground">
            在本机打开 ComfyUI/models 下对应目录（需后端跑在本机 Windows）。
          </p>
        </div>
      </div>

      <Button
        type="button"
        variant="default"
        size="icon"
        class="h-12 w-12 rounded-full shadow-lg"
        :title="open ? '关闭菜单' : '快捷菜单'"
        aria-label="快捷菜单"
        aria-expanded="open"
        @click="toggle"
      >
        <X v-if="open" class="h-5 w-5" />
        <Menu v-else class="h-5 w-5" />
      </Button>
    </div>
  </Teleport>
</template>
