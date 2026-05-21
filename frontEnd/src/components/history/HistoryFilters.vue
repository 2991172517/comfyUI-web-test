<script setup>
import { onMounted } from 'vue'
import { useHistoryStore } from '@/stores/useHistoryStore.js'
import { useAppStore } from '@/stores/useAppStore.js'
import ModelFilterPicker from '@/components/models/ModelFilterPicker.vue'
import Button from '@/components/ui/Button.vue'
import Label from '@/components/ui/Label.vue'
import SelectNative from '@/components/ui/SelectNative.vue'

const history = useHistoryStore()
const app = useAppStore()

function onLoraChange(name) {
  history.filters.lora_name = name
  history.filters.lora_weight = ''
  history.filters.lora_node = ''
}

function apply() {
  history.refresh()
}

onMounted(() => {
  if (app.healthOk && !app.modelLists.checkpoints.length) {
    app.loadModelLists().catch(() => {})
  }
})
</script>

<template>
  <div
    class="flex flex-wrap items-end gap-3 rounded-lg border border-border bg-card p-4"
  >
    <div class="space-y-1">
      <Label class="text-xs">类型</Label>
      <SelectNative v-model="history.filters.type" class="min-w-[7rem]">
        <option value="">全部</option>
        <option value="single">单抽</option>
        <option value="batch">批量</option>
      </SelectNative>
    </div>

    <ModelFilterPicker
      v-model="history.filters.checkpoint"
      folder="checkpoints"
      label="Checkpoint"
      :options="history.filterOptions.checkpoints"
      :catalog="app.modelLists.checkpointCatalog"
      :loading="app.modelsLoading"
      trigger-class="min-w-[12rem]"
    />

    <ModelFilterPicker
      :model-value="history.filters.lora_name"
      folder="loras"
      label="LoRA"
      :lora-rows="history.filterOptions.loras"
      :catalog="app.modelLists.loraCatalog"
      :loading="app.modelsLoading"
      trigger-class="min-w-[12rem]"
      @update:model-value="onLoraChange"
    />

    <div v-if="history.filters.lora_name" class="space-y-1">
      <Label class="text-xs">LoRA 权重</Label>
      <SelectNative v-model="history.filters.lora_weight" class="min-w-[6rem]">
        <option value="">全部</option>
        <option
          v-for="w in history.loraWeightsForName(history.filters.lora_name)"
          :key="w"
          :value="String(w)"
        >
          {{ w }}
        </option>
      </SelectNative>
    </div>

    <Button size="sm" :disabled="history.loading" @click="apply">筛选</Button>
    <Button variant="outline" size="sm" :disabled="history.loading" @click="history.resetFilters">
      重置
    </Button>
    <Button variant="ghost" size="sm" :disabled="history.loading" @click="history.refresh">
      {{ history.loading ? '加载中…' : '刷新' }}
    </Button>
  </div>
</template>
