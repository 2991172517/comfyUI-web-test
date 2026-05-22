<script setup>
import { computed, ref, watch } from 'vue'
import { X } from 'lucide-vue-next'
import { api } from '@/api/client.js'
import { splitSourceUrl } from '@/lib/modelDescription.js'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import Label from '@/components/ui/Label.vue'
import Textarea from '@/components/ui/Textarea.vue'

const props = defineProps({
  open: { type: Boolean, default: false },
  folder: { type: String, required: true },
  name: { type: String, default: '' },
  initialSummary: { type: Object, default: null },
})

const emit = defineEmits(['update:open', 'saved'])

const sourceUrl = ref('')
const content = ref('')
const saving = ref(false)
const error = ref('')

const title = computed(() => props.name || '模型说明')

watch(
  () => [props.open, props.initialSummary, props.name],
  () => {
    if (!props.open) return
    error.value = ''
    const s = props.initialSummary
    if (s?.sourceUrl) {
      sourceUrl.value = s.sourceUrl
      content.value = s.content || ''
    } else if (s?.content) {
      const split = splitSourceUrl(s.content)
      sourceUrl.value = split.sourceUrl || ''
      content.value = split.content
    } else {
      sourceUrl.value = ''
      content.value = ''
    }
  },
  { immediate: true },
)

function close() {
  emit('update:open', false)
}

async function save() {
  if (!props.name) return
  saving.value = true
  error.value = ''
  try {
    await api.saveModelDescription(props.folder, {
      name: props.name,
      content: content.value,
      source_url: sourceUrl.value,
    })
    emit('saved')
    close()
  } catch (e) {
    error.value = e.message || '保存失败'
  } finally {
    saving.value = false
  }
}

function onBackdrop(e) {
  if (e.target === e.currentTarget) close()
}
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="fixed inset-0 z-[85] flex items-end sm:items-center justify-center bg-black/50 p-0 sm:p-4 backdrop-blur-sm"
      @click="onBackdrop"
    >
      <div
        class="flex max-h-[min(90vh,640px)] w-full max-w-lg flex-col overflow-hidden rounded-t-xl sm:rounded-xl border border-border bg-card shadow-xl"
        role="dialog"
        aria-modal="true"
        @click.stop
      >
        <header class="flex shrink-0 items-center justify-between gap-2 border-b border-border px-4 py-3">
          <div class="min-w-0">
            <h2 class="text-sm font-semibold truncate">编辑模型说明</h2>
            <p class="text-[10px] text-muted-foreground font-mono truncate" :title="name">{{ name }}</p>
          </div>
          <Button variant="ghost" size="sm" class="h-8 w-8 p-0" aria-label="关闭" @click="close">
            <X class="h-4 w-4" />
          </Button>
        </header>

        <div class="min-h-0 flex-1 overflow-y-auto px-4 py-4 space-y-3">
          <div class="space-y-1.5">
            <Label class="text-xs">访问链接（可选）</Label>
            <Input
              v-model="sourceUrl"
              class="text-xs"
              placeholder="https://..."
              :disabled="saving"
            />
          </div>
          <div class="space-y-1.5">
            <Label class="text-xs">说明正文</Label>
            <Textarea
              v-model="content"
              rows="12"
              class="text-xs font-mono leading-relaxed"
              placeholder="写入模型说明；保存到同名文件夹内的 模型说明.txt"
              :disabled="saving"
            />
          </div>
          <p v-if="error" class="text-sm text-destructive">{{ error }}</p>
          <p class="text-[10px] text-muted-foreground">
            保存路径：models/{{ folder }}/&lt;与模型 stem 同名&gt;/模型说明.txt
          </p>
        </div>

        <footer class="flex shrink-0 justify-end gap-2 border-t border-border px-4 py-3">
          <Button variant="outline" size="sm" :disabled="saving" @click="close">取消</Button>
          <Button size="sm" :disabled="saving || !name" @click="save">
            {{ saving ? '保存中…' : '保存说明' }}
          </Button>
        </footer>
      </div>
    </div>
  </Teleport>
</template>
