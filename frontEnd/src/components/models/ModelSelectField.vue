<script setup>
import { computed, toRef } from 'vue'
import Label from '@/components/ui/Label.vue'
import SelectNative from '@/components/ui/SelectNative.vue'
import ModelPreviewPanel from '@/components/models/ModelPreviewPanel.vue'
import ModelInfoHint from '@/components/models/ModelInfoHint.vue'
import { useModelAssets } from '@/composables/useModelAssets.js'

const props = defineProps({
  label: { type: String, default: '' },
  folder: { type: String, required: true },
  modelValue: { type: String, default: '' },
  options: { type: Array, default: () => [] },
  missingValue: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
  hint: { type: String, default: '' },
  showPreview: { type: Boolean, default: true },
  previewSize: { type: String, default: 'md' },
})

const emit = defineEmits(['update:modelValue'])

const value = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const { previews, summary, loading: assetsLoading, previewIndex } = useModelAssets(
  props.folder,
  toRef(props, 'modelValue'),
)
</script>

<template>
  <div class="grid gap-3 lg:grid-cols-[1fr,min(300px,42%)]">
    <div class="space-y-1.5">
      <Label v-if="label">{{ label }}</Label>
      <slot name="label-extra" />
      <div class="flex items-stretch gap-1.5">
        <SelectNative v-model="value" class="flex-1 min-w-0" :disabled="disabled || loading">
          <option v-if="!options.length" value="" disabled>
            {{ loading ? '加载中…' : '无可用模型' }}
          </option>
          <option v-if="missingValue" :value="modelValue">{{ modelValue }}（当前工作流）</option>
          <option v-for="name in options" :key="name" :value="name">{{ name }}</option>
        </SelectNative>
        <ModelInfoHint v-if="summary" :summary="summary" />
      </div>
      <p v-if="hint" class="text-xs text-muted-foreground">{{ hint }}</p>
      <p v-else-if="summary" class="text-[10px] text-muted-foreground">
        悬停 <span class="inline-flex align-middle">ⓘ</span> 查看模型说明（{{ summary.filename }}）
      </p>
    </div>
    <ModelPreviewPanel
      v-if="showPreview"
      :folder="folder"
      :model-name="modelValue"
      :previews="previews"
      :loading="assetsLoading"
      v-model:index="previewIndex"
      :size="previewSize"
    />
  </div>
</template>
