<script setup>
import { ref } from 'vue'
import { useAppStore } from '@/stores/useAppStore.js'
import Button from '@/components/ui/Button.vue'

const store = useAppStore()
const copyHint = ref('')

async function copyText(label, text) {
  const body = String(text || '').trim()
  if (!body) {
    copyHint.value = `${label}为空`
    return
  }
  try {
    await navigator.clipboard.writeText(body)
    copyHint.value = `已复制${label}`
  } catch {
    copyHint.value = `复制${label}失败，请手动选中复制`
  }
}
</script>

<template>
  <div
    v-if="store.lastQueuedPrompts?.positive || store.lastQueuedPrompts?.negative"
    class="rounded-md border border-border/70 bg-muted/20 px-3 py-2.5 space-y-2"
  >
    <div class="flex flex-wrap items-center gap-2">
      <p class="text-xs font-medium text-muted-foreground">
        本次入队最终提示词（前端已拼好，与 ComfyUI 一致）
      </p>
      <Button variant="outline" size="sm" class="h-7 text-xs" @click="copyText('正向', store.lastQueuedPrompts.positive)">
        复制正向
      </Button>
      <Button variant="outline" size="sm" class="h-7 text-xs" @click="copyText('负向', store.lastQueuedPrompts.negative)">
        复制负向
      </Button>
      <span v-if="copyHint" class="text-xs text-muted-foreground">{{ copyHint }}</span>
    </div>
    <details class="text-xs">
      <summary class="cursor-pointer text-muted-foreground hover:text-foreground">展开查看全文</summary>
      <div class="mt-2 space-y-2 max-h-48 overflow-y-auto">
        <div>
          <p class="font-medium text-foreground mb-0.5">正向</p>
          <pre class="whitespace-pre-wrap break-words text-muted-foreground">{{ store.lastQueuedPrompts.positive }}</pre>
        </div>
        <div>
          <p class="font-medium text-foreground mb-0.5">负向</p>
          <pre class="whitespace-pre-wrap break-words text-muted-foreground">{{ store.lastQueuedPrompts.negative }}</pre>
        </div>
      </div>
    </details>
  </div>
</template>
