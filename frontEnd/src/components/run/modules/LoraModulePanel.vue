<script setup>
import { computed, ref, watch } from 'vue'
import { Plus } from 'lucide-vue-next'
import { useAppStore } from '@/stores/useAppStore.js'
import { useBatchStore } from '@/stores/useBatchStore.js'
import { useCheckpointLoraCompat } from '@/composables/useCheckpointLoraCompat.js'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Label from '@/components/ui/Label.vue'
import Switch from '@/components/ui/Switch.vue'
import Slider from '@/components/ui/Slider.vue'
import NumberStepper from '@/components/ui/NumberStepper.vue'
import DirectionToggle from '@/components/ui/DirectionToggle.vue'
import LoraStrengthControl from '@/components/models/LoraStrengthControl.vue'
import LoraModelPicker from '@/components/models/LoraModelPicker.vue'
import LoraPickDialog from '@/components/models/LoraPickDialog.vue'
import { cn } from '@/lib/utils'

const props = defineProps({
  batchMode: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  manageChain: { type: Boolean, default: false },
  maxSlots: { type: Number, default: 5 },
})

const emit = defineEmits(['remove', 'add'])

const app = useAppStore()
const batch = useBatchStore()
const singleSyncPair = ref(true)
const pickOpen = ref(false)

const activeCheckpoint = computed(() => app.activeCheckpointName)
const loraCompat = useCheckpointLoraCompat(activeCheckpoint)

const loras = computed(() =>
  props.batchMode ? batch.loras : app.workflowLorasForUi,
)

const canAdd = computed(
  () => props.manageChain && !props.batchMode && loras.value.length < props.maxSlots,
)

watch(
  () => [app.selectedId, app.workflowLoras],
  () => {
    if (props.batchMode) batch.syncLoraAxisState()
  },
  { immediate: true, deep: true },
)

function loraFileName(l) {
  if (props.batchMode) {
    return batch.loraAxisState[l.node_id]?.loraName || l.lora_name || ''
  }
  return String(app.fieldValue(l.node_id, { key: 'lora_name', value: l.lora_name }))
}

function patchSingle(nodeId, key, val) {
  app.updateField(nodeId, key, val)
  if (singleSyncPair.value && (key === 'strength_model' || key === 'strength_clip')) {
    const other = key === 'strength_model' ? 'strength_clip' : 'strength_model'
    app.updateField(nodeId, other, val)
  }
}

function patchFixed(nodeId, key, val) {
  const st = batch.loraAxisState[nodeId]
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

function singleModel(nodeId, l) {
  return app.fieldValue(nodeId, { key: 'strength_model', value: l.strength_model })
}

function singleClip(nodeId, l) {
  return app.fieldValue(nodeId, { key: 'strength_clip', value: l.strength_clip })
}

function onPickLora(name) {
  emit('add', name)
}
</script>

<template>
  <div class="space-y-4">
    <div
      v-if="manageChain"
      class="flex flex-wrap items-center justify-between gap-2 border-b border-border/70 pb-3"
    >
      <Button size="sm" class="gap-1.5" :disabled="disabled || !canAdd" @click="pickOpen = true">
        <Plus class="h-4 w-4" />
        添加 LoRA
      </Button>
      <span class="text-[11px] text-muted-foreground">
        {{ loras.length }} / {{ maxSlots }} · 选定模型后自动串接进链
      </span>
    </div>

    <p
      v-if="activeCheckpoint"
      class="text-[11px] text-muted-foreground rounded-md border border-border/70 bg-muted/15 px-3 py-2"
    >
      当前 Checkpoint：
      <span class="font-mono text-foreground">{{ activeCheckpoint }}</span>
      <span v-if="loraCompat.loading"> · 加载适配…</span>
      <span v-else> · LoRA 列表按推荐/不推荐标记（灰字仍可点选）</span>
    </p>
    <p v-else-if="loras.length || !manageChain" class="text-[11px] text-amber-600 dark:text-amber-400 px-1">
      请先在 Checkpoint 模块选择底模，配置 LoRA 时将显示适配提示。
    </p>

    <p v-if="!loras.length" class="py-4 text-sm text-muted-foreground">
      {{
        manageChain
          ? '链上暂无 LoRA，点击上方「添加 LoRA」从弹窗选择。'
          : '当前工作流没有 LoRA 节点。'
      }}
    </p>

    <div
      v-else
      class="grid gap-4 items-stretch grid-cols-[repeat(auto-fill,minmax(min(100%,280px),1fr))]"
    >
      <article
        v-for="(l, chainIdx) in loras"
        :key="l.node_id"
        :class="
          cn(
            'flex h-full min-w-0 flex-col gap-3 rounded-xl border p-4',
            batchMode && batch.loraAxisState[l.node_id]?.enabled
              ? 'border-primary/50 bg-primary/5'
              : 'border-border bg-muted/10',
          )
        "
      >
        <div class="flex min-h-[1.75rem] shrink-0 items-start justify-between gap-2">
          <div class="min-w-0 space-y-1">
            <div class="flex flex-wrap items-center gap-1.5">
              <span class="truncate text-sm font-semibold">#{{ l.node_id }}</span>
              <Badge variant="outline" class="text-[10px]">链 {{ chainIdx + 1 }}</Badge>
              <Badge
                v-if="batchMode && batch.loraAxisState[l.node_id]?.enabled"
                variant="default"
                class="text-[10px]"
              >
                扫参 {{ batch.loraAxisState[l.node_id]?.sweepRole || '?' }}
              </Badge>
            </div>
          </div>
          <label v-if="batchMode" class="flex shrink-0 items-center gap-2 text-xs">
            <span class="text-muted-foreground">扫参</span>
            <Switch
              :model-value="!!batch.loraAxisState[l.node_id]?.enabled"
              size="sm"
              :disabled="disabled"
              @update:model-value="batch.toggleLoraSweep(l.node_id, $event)"
            />
          </label>
          <Button
            v-else-if="manageChain"
            variant="ghost"
            size="sm"
            class="h-7 shrink-0 px-2 text-xs text-destructive hover:text-destructive"
            :disabled="disabled"
            @click="$emit('remove', l.node_id)"
          >
            移除
          </Button>
        </div>

        <LoraModelPicker
          class="flex-1 min-h-0"
          block-class="h-full"
          :key="`lora-picker-${l.node_id}-${app.restoreEpoch}`"
          :show-label="false"
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

        <template v-if="batchMode">
          <template v-if="batch.loraAxisState[l.node_id]?.enabled">
            <div class="mt-auto space-y-3">
              <div class="space-y-1.5">
                <Label class="text-xs">起始权重</Label>
                <Slider
                  v-model="batch.loraAxisState[l.node_id].start"
                  :min="0"
                  :max="2"
                  :step="0.05"
                  :disabled="disabled"
                />
              </div>
              <div class="space-y-1.5">
                <Label class="text-xs">步进</Label>
                <Slider
                  v-model="batch.loraAxisState[l.node_id].step"
                  :min="0.01"
                  :max="0.5"
                  :step="0.01"
                  :disabled="disabled"
                />
              </div>
              <div class="space-y-1.5">
                <Label class="text-xs">方向</Label>
                <DirectionToggle
                  v-model="batch.loraAxisState[l.node_id].direction"
                  :disabled="disabled"
                />
              </div>
              <div class="space-y-1.5">
                <Label class="text-xs">档位数</Label>
                <NumberStepper
                  v-model="batch.loraAxisState[l.node_id].count"
                  :min="1"
                  :max="20"
                  :disabled="disabled"
                />
              </div>
            </div>
          </template>
          <LoraStrengthControl
            v-else
            class="mt-auto"
            :model="batch.loraAxisState[l.node_id].fixedModel"
            :clip="batch.loraAxisState[l.node_id].fixedClip"
            :sync="batch.loraAxisState[l.node_id].syncPair"
            :disabled="disabled"
            compact
            @update:sync="batch.loraAxisState[l.node_id].syncPair = $event"
            @update:model="patchFixed(l.node_id, 'fixedModel', $event)"
            @update:clip="patchFixed(l.node_id, 'fixedClip', $event)"
          />
        </template>

        <LoraStrengthControl
          v-else
          class="mt-auto"
          :model="singleModel(l.node_id, l)"
          :clip="singleClip(l.node_id, l)"
          :sync="singleSyncPair"
          :disabled="disabled"
          @update:sync="singleSyncPair = $event"
          @update:model="patchSingle(l.node_id, 'strength_model', $event)"
          @update:clip="patchSingle(l.node_id, 'strength_clip', $event)"
        />
      </article>
    </div>

    <LoraPickDialog v-model:open="pickOpen" @pick="onPickLora" />
  </div>
</template>
