<script setup>
import { computed, ref, watch } from 'vue'
import { useAppStore } from '@/stores/useAppStore.js'
import { useBatchStore } from '@/stores/useBatchStore.js'
import { useCheckpointLoraCompat } from '@/composables/useCheckpointLoraCompat.js'
import Label from '@/components/ui/Label.vue'
import Input from '@/components/ui/Input.vue'
import SelectNative from '@/components/ui/SelectNative.vue'
import Badge from '@/components/ui/Badge.vue'
import Switch from '@/components/ui/Switch.vue'
import Slider from '@/components/ui/Slider.vue'
import LoraStrengthControl from '@/components/models/LoraStrengthControl.vue'
import LoraModelPicker from '@/components/models/LoraModelPicker.vue'
import { cn } from '@/lib/utils'

const props = defineProps({
  batchMode: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
})

const app = useAppStore()
const batch = useBatchStore()
const singleSyncPair = ref(true)

const activeCheckpoint = computed(() => app.activeCheckpointName)
const loraCompat = useCheckpointLoraCompat(activeCheckpoint)

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

function axisState(nodeId) {
  return batch.loraAxisState[nodeId]
}

function patchFixed(nodeId, key, val) {
  const st = axisState(nodeId)
  if (!st) return
  st[key] = val
  if (key === 'fixedModel' && st.syncPair) st.fixedClip = val
  if (key === 'fixedClip' && st.syncPair) st.fixedModel = val
  app.updateField(nodeId, key === 'fixedModel' ? 'strength_model' : 'strength_clip', val)
  if (st.syncPair) {
    app.updateField(nodeId, 'strength_model', st.fixedModel)
    app.updateField(nodeId, 'strength_clip', st.fixedClip)
  }
}

function patchSingle(nodeId, key, val) {
  app.updateField(nodeId, key, val)
  if (singleSyncPair.value && (key === 'strength_model' || key === 'strength_clip')) {
    const other = key === 'strength_model' ? 'strength_clip' : 'strength_model'
    app.updateField(nodeId, other, val)
  }
}

function singleModel(nodeId, l) {
  return app.fieldValue(nodeId, { key: 'strength_model', value: l.strength_model })
}

function singleClip(nodeId, l) {
  return app.fieldValue(nodeId, { key: 'strength_clip', value: l.strength_clip })
}
</script>

<template>
  <div v-if="!loras.length" class="text-sm text-muted-foreground py-6">
    当前工作流没有 LoRA 节点。
  </div>
  <div v-else class="space-y-4">
    <p
      v-if="activeCheckpoint"
      class="text-[11px] text-muted-foreground rounded-md border border-border/70 bg-muted/15 px-3 py-2"
    >
      当前 Checkpoint：
      <span class="font-mono text-foreground">{{ activeCheckpoint }}</span>
      <span v-if="loraCompat.loading"> · 加载适配…</span>
      <span v-else> · LoRA 列表按推荐/不推荐标记（灰字仍可点选）</span>
    </p>
    <p v-else class="text-[11px] text-amber-600 dark:text-amber-400 px-1">
      请先在「其他」模块中选择 Checkpoint，再配置 LoRA 时将显示适配提示。
    </p>
    <p v-if="batchMode" class="text-sm text-muted-foreground">
      <template v-if="batch.hasSweepEnabled">
        最多 2 个 LoRA 参与 A×B 扫参；当前计划
        <strong class="text-foreground">{{ batch.plannedTotal }}</strong> 张
      </template>
      <template v-else>
        未开启扫参，将按固定权重连续生成
        <strong class="text-foreground">{{ batch.plannedTotal }}</strong> 张（最多 12）
      </template>
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
        <div v-if="batchMode" class="flex items-center gap-2 shrink-0">
          <Label class="text-sm text-muted-foreground mb-0">参与扫参</Label>
          <Switch
            :model-value="!!batch.loraAxisState[l.node_id]?.enabled"
            size="sm"
            :disabled="disabled"
            :aria-label="`LoRA ${l.node_id} 参与扫参`"
            @update:model-value="batch.toggleLoraSweep(l.node_id, $event)"
          />
        </div>
      </div>

      <LoraModelPicker
        :key="`lora-picker-${l.node_id}-${app.restoreEpoch}-${activeCheckpoint}`"
        label="LoRA 模型"
        :model-value="loraFileName(l)"
        :options="app.modelLists.loras"
        :catalog="app.modelLists.loraCatalog"
        :lora-compat-map="loraCompat.compatMap"
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
        <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <div class="space-y-1.5 sm:col-span-2 lg:col-span-1">
            <Label>起始权重</Label>
            <Slider
              v-model="batch.loraAxisState[l.node_id].start"
              :min="0"
              :max="2"
              :step="0.05"
              :disabled="disabled"
            />
          </div>
          <div class="space-y-1.5">
            <Label>步进</Label>
            <Slider
              v-model="batch.loraAxisState[l.node_id].step"
              :min="0.01"
              :max="0.5"
              :step="0.01"
              :disabled="disabled"
            />
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
            <Input
              v-model.number="batch.loraAxisState[l.node_id].count"
              type="number"
              min="1"
              max="20"
              :disabled="disabled"
            />
          </div>
        </div>
      </template>

      <template v-else-if="batchMode">
        <LoraStrengthControl
          :model="batch.loraAxisState[l.node_id].fixedModel"
          :clip="batch.loraAxisState[l.node_id].fixedClip"
          :sync="batch.loraAxisState[l.node_id].syncPair"
          :disabled="disabled"
          @update:sync="batch.loraAxisState[l.node_id].syncPair = $event"
          @update:model="patchFixed(l.node_id, 'fixedModel', $event)"
          @update:clip="patchFixed(l.node_id, 'fixedClip', $event)"
        />
      </template>

      <template v-else>
        <LoraStrengthControl
          :model="singleModel(l.node_id, l)"
          :clip="singleClip(l.node_id, l)"
          :sync="singleSyncPair"
          :disabled="disabled"
          @update:sync="singleSyncPair = $event"
          @update:model="patchSingle(l.node_id, 'strength_model', $event)"
          @update:clip="patchSingle(l.node_id, 'strength_clip', $event)"
        />
      </template>
    </article>
  </div>
</template>
