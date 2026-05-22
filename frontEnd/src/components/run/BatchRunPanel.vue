<script setup>
import { useBatchStore } from '@/stores/useBatchStore.js'
import Label from '@/components/ui/Label.vue'
import Input from '@/components/ui/Input.vue'
import SelectNative from '@/components/ui/SelectNative.vue'
import Switch from '@/components/ui/Switch.vue'
import Slider from '@/components/ui/Slider.vue'

defineProps({ disabled: { type: Boolean, default: false } })

const batch = useBatchStore()
</script>

<template>
  <div class="rounded-lg border border-border bg-muted/30 p-4 space-y-4">
    <p class="text-sm font-medium">批量执行</p>
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
      <div v-if="!batch.hasSweepEnabled" class="space-y-1.5 sm:col-span-2">
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
    <p class="text-[11px] text-muted-foreground">
      预览与「开始批量」「保存为任务」见页面底部悬浮栏
    </p>
  </div>
</template>
