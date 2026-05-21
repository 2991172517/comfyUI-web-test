<script setup>
import { onMounted, ref } from 'vue'
import { api } from '@/api/client.js'
import Label from '@/components/ui/Label.vue'
import SelectNative from '@/components/ui/SelectNative.vue'
import Button from '@/components/ui/Button.vue'
import Badge from '@/components/ui/Badge.vue'
import { openGlobalPromptModal } from '@/composables/useGlobalPromptModal.js'

const props = defineProps({
  disabled: { type: Boolean, default: false },
  label: { type: String, default: '导入提示词预设' },
})

const emit = defineEmits(['import'])

const presets = ref([])
const selectedId = ref('')
const loading = ref(false)

async function refresh() {
  loading.value = true
  try {
    const res = await api.listPromptPresets()
    presets.value = res.presets || []
    if (!selectedId.value && presets.value.length) {
      selectedId.value = presets.value[0].id
    }
  } finally {
    loading.value = false
  }
}

function doImport() {
  const p = presets.value.find((x) => x.id === selectedId.value)
  if (!p) return
  emit('import', {
    enabled: p.enabled !== false,
    positive: p.positive ?? '',
    negative: p.negative ?? '',
    fixed: p.fixed,
    random_groups: p.random_groups,
    merge: p.merge,
    preset_id: p.id,
    preset_name: p.name,
  })
}

onMounted(() => refresh().catch(() => {}))

defineExpose({ refresh })
</script>

<template>
  <div class="flex flex-wrap items-end gap-2 rounded-lg border border-dashed border-border bg-muted/30 px-3 py-2">
    <div class="flex-1 min-w-[160px] space-y-1">
      <Label class="text-xs">{{ label }}</Label>
      <SelectNative v-model="selectedId" :disabled="disabled || loading || !presets.length">
        <option value="" disabled>选择预设…</option>
        <option v-for="p in presets" :key="p.id" :value="p.id">
          {{ p.name }}（{{ p.random_group_count }} 随机组）
        </option>
      </SelectNative>
    </div>
    <Button
      variant="secondary"
      size="sm"
      :disabled="disabled || !selectedId"
      @click="doImport"
    >
      导入
    </Button>
    <Button variant="ghost" size="sm" :disabled="loading" @click="refresh">刷新</Button>
    <Badge v-if="!presets.length" variant="outline" class="text-[10px]">
      <button type="button" class="underline" @click="openGlobalPromptModal('presets')">
        去添加预设
      </button>
    </Badge>
  </div>
</template>
