<script setup>
import { computed } from 'vue'
import { useBatchStore } from '@/stores/useBatchStore.js'
import Label from '@/components/ui/Label.vue'
import Input from '@/components/ui/Input.vue'
import SelectNative from '@/components/ui/SelectNative.vue'
import Switch from '@/components/ui/Switch.vue'
import Slider from '@/components/ui/Slider.vue'
import Badge from '@/components/ui/Badge.vue'

defineProps({
  disabled: { type: Boolean, default: false },
})

const batch = useBatchStore()

const countHint = computed(() => {
  if (batch.hasSweepEnabled) {
    return `LoRA 扫参 · 共 ${batch.plannedTotal} 张`
  }
  const n = batch.plannedTotal
  return n <= 1 ? '单张' : `${n} 张`
})
</script>

<template>
  <section
    class="rounded-xl border border-border bg-muted/20 p-4 space-y-4"
    aria-label="生成参数"
  >
    <div class="flex flex-wrap items-center justify-between gap-2">
      <div>
        <p class="text-sm font-medium">生成参数</p>
        <p class="text-[11px] text-muted-foreground mt-0.5">
          不扫参时按张数生成；开启 LoRA 扫参后张数由档位数决定。
        </p>
      </div>
      <Badge variant="outline" class="tabular-nums shrink-0">{{ countHint }}</Badge>
    </div>

    <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
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

      <div v-if="!batch.hasSweepEnabled" class="space-y-1.5 sm:col-span-2">
        <Label>生成张数</Label>
        <Slider
          v-model="batch.form.repeatCount"
          :min="1"
          :max="12"
          :step="1"
          :format="(v) => `${Math.round(v)} 张`"
          :disabled="disabled"
        />
      </div>

      <div v-else class="space-y-1.5 sm:col-span-2 flex flex-col justify-end">
        <Label class="text-muted-foreground">生成张数</Label>
        <p class="text-sm tabular-nums text-foreground py-1.5">
          {{ batch.plannedTotal }} 张
          <span class="text-[11px] text-muted-foreground ml-1">（由扫参档位数计算）</span>
        </p>
      </div>

      <div class="flex items-end gap-2 pb-0.5 lg:col-span-4">
        <Label class="text-sm text-muted-foreground mb-0 shrink-0">扫参时同步 clip</Label>
        <Switch v-model="batch.form.syncClip" size="sm" :disabled="disabled" />
      </div>
    </div>
  </section>
</template>
