<script setup>
import { computed, watch } from 'vue'
import { useAppStore } from '@/stores/useAppStore.js'
import { useBatchStore } from '@/stores/useBatchStore.js'
import Label from '@/components/ui/Label.vue'
import Input from '@/components/ui/Input.vue'
import SelectNative from '@/components/ui/SelectNative.vue'
import Switch from '@/components/ui/Switch.vue'
import Slider from '@/components/ui/Slider.vue'
import Badge from '@/components/ui/Badge.vue'
import LoraStrengthControl from '@/components/models/LoraStrengthControl.vue'
import { cn } from '@/lib/utils'

defineProps({ disabled: { type: Boolean, default: false } })

const app = useAppStore()
const batch = useBatchStore()

const loras = computed(() => batch.loras)

watch(
  () => [app.selectedId, app.workflowLoras],
  () => batch.syncLoraAxisState(),
  { immediate: true, deep: true },
)

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
</script>

<template>
  <div class="rounded-lg border border-border bg-muted/30 p-4 space-y-5">
    <div>
      <p class="text-sm font-medium">批量执行</p>
      <p class="text-[11px] text-muted-foreground mt-0.5">
        Seed 与 LoRA 权重/扫参在此统一调整；LoRA 模块页仅选择模型文件。
      </p>
    </div>

    <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 max-w-3xl">
      <div class="space-y-1.5">
        <Label>Seed</Label>
        <SelectNative v-model="batch.form.seedMode" :disabled="disabled">
          <option value="fixed">固定</option>
          <option value="increment">递增</option>
          <option value="random">随机</option>
        </SelectNative>
      </div>
      <div v-if="batch.form.seedMode !== 'random'" class="space-y-1.5">
        <Label>基础 Seed</Label>
        <Input v-model.number="batch.form.seed" type="number" :disabled="disabled" />
      </div>
      <div v-if="!batch.hasSweepEnabled" class="space-y-1.5 sm:col-span-2 lg:col-span-1">
        <Label>生成张数（无扫参，最多 12）</Label>
        <Slider
          v-model="batch.form.repeatCount"
          :min="1"
          :max="12"
          :step="1"
          :format="(v) => `${Math.round(v)} 张`"
          :disabled="disabled"
        />
      </div>
      <div class="flex items-end gap-2 pb-0.5">
        <Label class="text-sm text-muted-foreground mb-0 shrink-0">扫参时同步 clip</Label>
        <Switch v-model="batch.form.syncClip" size="sm" :disabled="disabled" />
      </div>
    </div>

    <div
      v-if="loras.length"
      class="grid gap-4 border-t border-border/70 pt-4 grid-cols-[repeat(auto-fill,minmax(min(100%,280px),1fr))]"
    >
      <div class="flex flex-wrap items-center gap-2">
        <p class="text-sm font-medium">LoRA 执行参数</p>
        <Badge v-if="batch.hasSweepEnabled" variant="default">
          扫参 {{ batch.plannedTotal }} 张
        </Badge>
      </div>

      <article
        v-for="(l, chainIdx) in loras"
        :key="l.node_id"
        :class="
          cn(
            'flex h-full min-w-0 flex-col gap-3 rounded-lg border p-4',
            batch.loraAxisState[l.node_id]?.enabled
              ? 'border-primary/50 bg-primary/5'
              : 'border-border bg-background/40',
          )
        "
      >
        <div class="flex flex-wrap items-center justify-between gap-2">
          <div class="flex flex-wrap items-center gap-2">
            <span class="text-sm font-medium">#{{ l.node_id }} {{ l.short_name }}</span>
            <Badge variant="outline" class="text-[10px]">链 {{ chainIdx + 1 }}</Badge>
            <Badge
              v-if="batch.loraAxisState[l.node_id]?.enabled"
              variant="default"
              class="text-[10px]"
            >
              扫参 {{ batch.loraAxisState[l.node_id]?.sweepRole || '?' }}
            </Badge>
          </div>
          <label class="flex items-center gap-2 text-sm shrink-0">
            <span class="text-muted-foreground">参与扫参</span>
            <Switch
              :model-value="!!batch.loraAxisState[l.node_id]?.enabled"
              size="sm"
              :disabled="disabled"
              @update:model-value="batch.toggleLoraSweep(l.node_id, $event)"
            />
          </label>
        </div>

        <template v-if="batch.loraAxisState[l.node_id]?.enabled">
          <div class="grid gap-4 sm:grid-cols-2">
            <div class="space-y-1.5">
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

        <template v-else>
          <LoraStrengthControl
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
      </article>
    </div>

    <p class="text-[11px] text-muted-foreground">
      预览与「开始批量」「保存为任务」见页面底部悬浮栏
    </p>
  </div>
</template>
