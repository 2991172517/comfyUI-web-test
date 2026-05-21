<script setup>
import { onMounted, ref, watch } from 'vue'
import { api } from '@/api/client.js'
import { openGlobalPromptModal } from '@/composables/useGlobalPromptModal.js'
import { normalizePromptConfig } from '@/composables/usePromptConfig.js'
import Button from '@/components/ui/Button.vue'
import Label from '@/components/ui/Label.vue'
import SelectNative from '@/components/ui/SelectNative.vue'
import { X } from 'lucide-vue-next'

const props = defineProps({
  open: { type: Boolean, default: false },
})

const emit = defineEmits(['update:open', 'import'])

const presets = ref([])
const selectedId = ref('')
const loading = ref(false)

async function refresh() {
  loading.value = true
  try {
    const res = await api.listPromptPresets()
    presets.value = res.presets || []
    if (selectedId.value && !presets.value.some((p) => p.id === selectedId.value)) {
      selectedId.value = ''
    }
    if (!selectedId.value && presets.value.length) {
      selectedId.value = presets.value[0].id
    }
  } finally {
    loading.value = false
  }
}

function close() {
  emit('update:open', false)
}

function onBackdrop(e) {
  if (e.target === e.currentTarget) close()
}

async function confirm() {
  const row = presets.value.find((p) => p.id === selectedId.value)
  if (!row) return
  let p = row
  try {
    const res = await api.getPromptPreset(selectedId.value)
    if (res.preset) p = res.preset
  } catch {
    /* 列表已含完整配置时仍可导入 */
  }
  const cfg = normalizePromptConfig(p)
  emit('import', {
    ...cfg,
    preset_id: p.id,
    preset_name: p.name,
  })
  close()
}

watch(
  () => props.open,
  (v) => {
    if (v) refresh().catch(() => {})
  },
)

onMounted(() => {
  if (props.open) refresh().catch(() => {})
})
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="fixed inset-0 z-[95] flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm"
      @click="onBackdrop"
    >
      <div
        class="w-full max-w-md rounded-xl border border-border bg-card shadow-xl"
        role="dialog"
        aria-modal="true"
        @click.stop
      >
        <header class="flex items-center justify-between gap-3 border-b border-border px-4 py-3">
          <h2 class="text-base font-semibold">选择提示词预设</h2>
          <Button variant="ghost" size="sm" class="h-8 w-8 p-0" @click="close">
            <X class="h-4 w-4" />
          </Button>
        </header>

        <div class="p-4 space-y-4">
          <p class="text-xs text-muted-foreground leading-relaxed">
            预设包含随机组与可选的固定前后缀、正/负全文。导入后可在本页展开微调；完整编辑请前往
            <button
              type="button"
              class="text-primary underline"
              @click="
                openGlobalPromptModal('presets');
                close();
              "
            >
              提示词设置
            </button>
          </p>

          <div v-if="loading" class="text-sm text-muted-foreground">加载预设列表…</div>
          <div v-else-if="!presets.length" class="text-sm text-muted-foreground">
            暂无预设，请先在设置页创建。
          </div>
          <div v-else class="space-y-1.5">
            <Label class="text-xs">预设</Label>
            <SelectNative v-model="selectedId" class="w-full">
              <option v-for="p in presets" :key="p.id" :value="p.id">
                {{ p.name }}（{{ p.random_group_count }} 随机组）
              </option>
            </SelectNative>
            <p
              v-if="selectedId"
              class="text-[10px] text-muted-foreground"
            >
              {{
                presets.find((x) => x.id === selectedId)?.description || '无说明'
              }}
            </p>
          </div>
        </div>

        <footer class="flex justify-end gap-2 border-t border-border px-4 py-3">
          <Button variant="outline" size="sm" @click="close">取消</Button>
          <Button size="sm" :disabled="!selectedId || loading" @click="confirm">
            导入
          </Button>
        </footer>
      </div>
    </div>
  </Teleport>
</template>
