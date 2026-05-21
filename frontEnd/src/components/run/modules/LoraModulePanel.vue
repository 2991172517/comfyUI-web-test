<script setup>
import { computed, watch } from 'vue'
import { useAppStore } from '@/stores/useAppStore.js'
import { useBatchStore } from '@/stores/useBatchStore.js'
import Label from '@/components/ui/Label.vue'
import Input from '@/components/ui/Input.vue'
import SelectNative from '@/components/ui/SelectNative.vue'
import Badge from '@/components/ui/Badge.vue'
import LoraModelPicker from '@/components/models/LoraModelPicker.vue'
import { cn } from '@/lib/utils'

const props = defineProps({
  batchMode: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
})

const app = useAppStore()
const batch = useBatchStore()

watch(
  () => [app.selectedId, app.workflowLoras],
  () => {
    if (props.batchMode) batch.syncLoraAxisState()
  },
  { immediate: true, deep: true },
)

const loras = computed(() =>
  props.batchMode ? batch.loras : app.workflowLorasForUi,
)

function loraFileName(l) {
  if (props.batchMode) {
    return batch.loraAxisState[l.node_id]?.loraName || l.lora_name || ''
  }
  return String(app.fieldValue(l.node_id, { key: 'lora_name', value: l.lora_name }))
}
</script>

<template>
  <div v-if="!loras.length" class="text-sm text-muted-foreground py-6">
    当前工作流没有 LoRA 节点。
  </div>
  <div v-else class="space-y-4">
    <p v-if="batchMode" class="text-sm text-muted-foreground">
      勾选最多 2 个参与 A×B 扫参；当前计划
      <strong class="text-foreground">{{ batch.plannedTotal }}</strong> 张
    </p>

    <article
      v-for="(l, chainIdx) in loras"
      :key="l.node_id"
      :class="
        cn(
          'rounded-xl border p-5 md:p-6 space-y-4 w-full',
          batchMode && batch.loraAxisState[l.node_id]?.enabled
            ? 'border-primary/50 bg-primary/5'
            : 'border-border bg-muted/10',
        )
      "
    >
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div class="flex flex-wrap items-center gap-2">
          <span class="text-base font-semibold">#{{ l.node_id }} {{ l.short_name }}</span>
          <Badge v-if="l.role" variant="secondary">
            {{ l.role === 'style' ? 'Style' : l.role === 'character' ? '角色' : l.role }}
          </Badge>
          <Badge variant="outline">链 {{ chainIdx + 1 }}</Badge>
          <Badge
            v-if="batchMode && batch.loraAxisState[l.node_id]?.enabled"
            variant="default"
          >
            扫参 {{ batch.loraAxisState[l.node_id]?.sweepRole || '?' }}
          </Badge>
        </div>
        <label v-if="batchMode" class="flex items-center gap-2 text-sm shrink-0">
          <input
            type="checkbox"
            class="rounded border-input h-4 w-4"
            :checked="batch.loraAxisState[l.node_id]?.enabled"
            :disabled="disabled"
            @change="batch.toggleLoraSweep(l.node_id, $event.target.checked)"
          />
          参与扫参
        </label>
      </div>

      <LoraModelPicker
        :key="`lora-picker-${l.node_id}-${app.restoreEpoch}`"
        label="LoRA 模型"
        :model-value="loraFileName(l)"
        :options="app.modelLists.loras"
        :catalog="app.modelLists.loraCatalog"
        :missing-value="
          !batchMode &&
          app.modelSelectMissing(l.node_id, { key: 'lora_name', value: l.lora_name })
        "
        :disabled="disabled || app.modelsLoading"
        :loading="app.modelsLoading"
        @update:model-value="
          async (v) => {
            if (batchMode) {
              batch.loraAxisState[l.node_id].loraName = v
              app.updateField(l.node_id, 'lora_name', v)
            } else {
              app.updateField(l.node_id, 'lora_name', v)
              await app.applyLoraSlotDefaults(l.node_id, v)
            }
          }
        "
      />

      <template v-if="batchMode && batch.loraAxisState[l.node_id]?.enabled">
        <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div class="space-y-1.5">
            <Label>起始权重</Label>
            <Input v-model.number="batch.loraAxisState[l.node_id].start" type="number" step="0.05" />
          </div>
          <div class="space-y-1.5">
            <Label>步进</Label>
            <Input v-model.number="batch.loraAxisState[l.node_id].step" type="number" step="0.05" min="0.01" />
          </div>
          <div class="space-y-1.5">
            <Label>方向</Label>
            <SelectNative v-model="batch.loraAxisState[l.node_id].direction" :disabled="disabled">
              <option value="up">累加 ↑</option>
              <option value="down">累减 ↓</option>
            </SelectNative>
          </div>
          <div class="space-y-1.5">
            <Label>档位数</Label>
            <Input v-model.number="batch.loraAxisState[l.node_id].count" type="number" min="1" max="20" />
          </div>
        </div>
      </template>
      <template v-else>
        <div class="grid gap-4 sm:grid-cols-2 max-w-xl">
          <div class="space-y-1.5">
            <Label>strength_model</Label>
            <Input
              type="number"
              step="0.05"
              :model-value="app.fieldValue(l.node_id, { key: 'strength_model', value: l.strength_model })"
              :disabled="disabled"
              @update:model-value="app.updateField(l.node_id, 'strength_model', Number($event))"
            />
          </div>
          <div class="space-y-1.5">
            <Label>strength_clip</Label>
            <Input
              type="number"
              step="0.05"
              :model-value="app.fieldValue(l.node_id, { key: 'strength_clip', value: l.strength_clip })"
              :disabled="disabled"
              @update:model-value="app.updateField(l.node_id, 'strength_clip', Number($event))"
            />
          </div>
        </div>
      </template>
    </article>
  </div>
</template>
