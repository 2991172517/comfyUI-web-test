<script setup>
import { computed, onBeforeUnmount, ref } from 'vue'
import { Plus, ChevronUp, ChevronDown } from 'lucide-vue-next'
import { useAppStore } from '@/stores/useAppStore.js'
import { useBatchStore } from '@/stores/useBatchStore.js'
import { useCheckpointLoraCompat } from '@/composables/useCheckpointLoraCompat.js'
import { useConfirmDialog } from '@/composables/useConfirmDialog.js'
import Badge from '@/components/ui/Badge.vue'
import IconDeleteButton from '@/components/ui/IconDeleteButton.vue'
import Label from '@/components/ui/Label.vue'
import Switch from '@/components/ui/Switch.vue'
import Slider from '@/components/ui/Slider.vue'
import NumberStepper from '@/components/ui/NumberStepper.vue'
import DirectionToggle from '@/components/ui/DirectionToggle.vue'
import LoraStrengthControl from '@/components/models/LoraStrengthControl.vue'
import LoraModelPicker from '@/components/models/LoraModelPicker.vue'
import { cn } from '@/lib/utils'

const props = defineProps({
  batchMode: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  manageChain: { type: Boolean, default: false },
  reorderable: { type: Boolean, default: false },
  /** 生成页：仅本次运行，不写回工作流 JSON */
  sessionOnly: { type: Boolean, default: false },
  maxSlots: { type: Number, default: null },
})

const emit = defineEmits(['remove', 'add', 'reorder'])

const app = useAppStore()
const batch = useBatchStore()
const { confirmDelete } = useConfirmDialog()
const singleSyncPair = ref(true)
const pickOpen = ref(false)

const activeCheckpoint = computed(() => app.activeCheckpointName)
const loraCompat = useCheckpointLoraCompat(activeCheckpoint)

const loras = computed(() => {
  if (props.batchMode) return batch.loras
  if (props.sessionOnly) return app.lorasForRun
  return app.workflowLorasForUi
})

const canAdd = computed(
  () =>
    props.manageChain &&
    !props.disabled &&
    (props.maxSlots == null || loras.value.length < props.maxSlots),
)

const chainHint = computed(() => {
  if (!props.manageChain) return ''
  const n = loras.value.length
  if (props.sessionOnly) {
    return `${n} 个 · 本次生成临时生效，不修改工作流文件 · 用 ↑↓ 调整顺序`
  }
  if (props.maxSlots != null) return `${n} / ${props.maxSlots} · 选定模型后自动串接进链`
  return `${n} 个 · 用 ↑↓ 调整顺序 · 增删会写入当前子工作流`
})

function openPickDialog() {
  if (!canAdd.value) return
  pickOpen.value = true
}

onBeforeUnmount(() => {
  pickOpen.value = false
})

async function onPickLora(name) {
  pickOpen.value = false
  if (props.sessionOnly) {
    await app.sessionAddLora(name)
    if (props.batchMode) batch.syncLoraAxisState()
    return
  }
  emit('add', name)
}

async function onRemove(nodeId) {
  if (props.sessionOnly) {
    if (
      !(await confirmDelete({
        title: '移除 LoRA',
        message: '从本次生成的临时链中移除？不会修改工作流文件。',
      }))
    ) {
      return
    }
    app.sessionRemoveLora(nodeId)
    if (props.batchMode) batch.syncLoraAxisState()
    return
  }
  emit('remove', nodeId)
}

function onMove(nodeId, delta) {
  if (props.sessionOnly) {
    app.sessionMoveLora(nodeId, delta)
    return
  }
  const list = loras.value.map((l) => l.node_id)
  const idx = list.indexOf(nodeId)
  if (idx < 0) return
  const to = idx + delta
  if (to < 0 || to >= list.length) return
  const next = [...list]
  const [item] = next.splice(idx, 1)
  next.splice(to, 0, item)
  emit('reorder', next)
}

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
</script>

<template>
  <div class="space-y-4">
    <p v-if="manageChain && chainHint" class="text-[11px] text-muted-foreground">{{ chainHint }}</p>

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

    <p v-if="!manageChain && !loras.length" class="py-4 text-sm text-muted-foreground">
      当前工作流没有 LoRA 节点。
    </p>

    <div
      v-if="manageChain || loras.length"
      class="grid gap-4 items-stretch grid-cols-[repeat(auto-fill,minmax(min(100%,280px),1fr))]"
    >
      <article
        v-for="(l, chainIdx) in loras"
        :key="l.node_id"
        :class="
          cn(
            'lora-chain-card flex h-full min-w-0 flex-col gap-3 rounded-xl border p-4 transition-colors duration-150',
            batchMode && batch.loraAxisState[l.node_id]?.enabled
              ? 'border-primary/50 bg-primary/5'
              : 'border-border bg-muted/10',
            l.session_only && 'border-dashed border-primary/25',
          )
        "
      >
        <div class="flex min-h-[1.75rem] shrink-0 items-start justify-between gap-2">
          <div class="flex min-w-0 flex-1 items-start gap-1.5">
            <div
              v-if="reorderable"
              class="flex shrink-0 flex-col gap-0.5"
            >
              <button
                type="button"
                class="flex h-6 w-6 items-center justify-center rounded-md text-muted-foreground hover:bg-muted/60 hover:text-foreground disabled:opacity-30"
                :disabled="disabled || chainIdx === 0"
                aria-label="上移"
                @click="onMove(l.node_id, -1)"
              >
                <ChevronUp class="h-4 w-4" />
              </button>
              <button
                type="button"
                class="flex h-6 w-6 items-center justify-center rounded-md text-muted-foreground hover:bg-muted/60 hover:text-foreground disabled:opacity-30"
                :disabled="disabled || chainIdx === loras.length - 1"
                aria-label="下移"
                @click="onMove(l.node_id, 1)"
              >
                <ChevronDown class="h-4 w-4" />
              </button>
            </div>
            <div class="min-w-0 space-y-1">
              <div class="flex flex-wrap items-center gap-1.5">
                <span class="truncate text-sm font-semibold">
                  {{ l.session_only ? '临时' : `#${l.node_id}` }}
                </span>
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
          </div>
          <div class="flex shrink-0 items-center gap-1">
            <label v-if="batchMode" class="flex items-center gap-2 text-xs">
              <span class="text-muted-foreground">扫参</span>
              <Switch
                :model-value="!!batch.loraAxisState[l.node_id]?.enabled"
                size="sm"
                :disabled="disabled"
                @update:model-value="batch.toggleLoraSweep(l.node_id, $event)"
              />
            </label>
            <IconDeleteButton
              v-if="manageChain"
              size="sm"
              title="移除 LoRA"
              :disabled="disabled"
              @click="onRemove(l.node_id)"
            />
          </div>
        </div>

        <LoraModelPicker
          class="flex-1 min-h-0"
          block-class="h-full"
          :key="`lora-picker-${l.node_id}`"
          :show-label="false"
          :model-value="loraFileName(l)"
          :options="app.modelLists.loras"
          :catalog="app.modelLists.loraCatalog"
          :lora-compat-map="loraCompat.compatMap"
          :missing-value="
            !batchMode &&
            !l.session_only &&
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

      <button
        v-if="manageChain"
        type="button"
        class="lora-chain-card group flex min-h-[220px] w-full min-w-0 flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-border/90 bg-muted/5 p-4 text-center transition-colors duration-150 hover:border-primary/45 hover:bg-primary/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 disabled:pointer-events-none disabled:opacity-45"
        :disabled="!canAdd"
        aria-label="添加 LoRA"
        @click="openPickDialog"
      >
        <span
          class="flex h-14 w-14 items-center justify-center rounded-full border border-border/80 bg-background/80 text-muted-foreground transition-transform duration-150 group-hover:scale-105 group-hover:border-primary/40 group-hover:text-primary"
        >
          <Plus class="h-9 w-9 stroke-[1.75]" />
        </span>
        <span class="text-sm font-medium text-muted-foreground group-hover:text-foreground">
          添加 LoRA
        </span>
      </button>
    </div>

    <LoraModelPicker
      v-model:picker-open="pickOpen"
      dialog-only
      :show-label="false"
      :options="app.modelLists.loras"
      :catalog="app.modelLists.loraCatalog"
      :lora-compat-map="loraCompat.compatMap"
      :loading="app.modelsLoading"
      :disabled="app.modelsLoading"
      @picked="onPickLora"
    />
  </div>
</template>
