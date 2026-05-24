<script setup>
import { ref } from 'vue'
import { X } from 'lucide-vue-next'
import { useModalMotion } from '@/composables/useModalMotion.js'
import { api } from '@/api/client.js'
import { useAppStore } from '@/stores/useAppStore.js'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import Label from '@/components/ui/Label.vue'

const open = defineModel('open', { type: Boolean, default: false })

const emit = defineEmits(['created'])

const app = useAppStore()
const name = ref('')
const busy = ref(false)

const backdropRef = ref(null)
const panelRef = ref(null)
useModalMotion(open, backdropRef, panelRef)

function close() {
  open.value = false
}

function onBackdrop(e) {
  if (e.target === e.currentTarget) close()
}

async function submit() {
  busy.value = true
  try {
    const res = await api.createWorkflowVariant({
      display_name: name.value.trim() || undefined,
    })
    name.value = ''
    emit('created', res)
    close()
    app.setMessage('已从母版复制，可在右侧编辑 Checkpoint / LoRA')
  } catch (e) {
    app.setMessage(e.message, true)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open"
      ref="backdropRef"
      class="fixed inset-0 z-[90] flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm"
      @click="onBackdrop"
    >
      <div
        ref="panelRef"
        class="w-full max-w-md rounded-xl border border-border bg-card shadow-xl"
        role="dialog"
        aria-modal="true"
        @click.stop
      >
        <header class="flex items-center justify-between gap-3 border-b border-border px-4 py-3">
          <div>
            <h2 class="text-base font-semibold">从母版复制新建</h2>
            <p class="mt-0.5 text-[11px] text-muted-foreground">复制 First_api 结构，适合在标准模板上微调 LoRA 链</p>
          </div>
          <Button variant="ghost" size="sm" class="h-8 w-8 shrink-0 p-0" aria-label="关闭" @click="close">
            <X class="h-4 w-4" />
          </Button>
        </header>
        <div class="space-y-4 p-4">
          <div class="space-y-1">
            <Label for="create-vname">显示名（可选）</Label>
            <Input id="create-vname" v-model="name" placeholder="修女 Style 测试" @keyup.enter="submit" />
            <p class="text-[11px] text-muted-foreground">不填则使用后台自动生成的 ID 作为显示名。</p>
          </div>
          <div class="flex justify-end gap-2">
            <Button variant="ghost" size="sm" @click="close">取消</Button>
            <Button size="sm" :disabled="busy" @click="submit">{{ busy ? '创建中…' : '创建' }}</Button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>
