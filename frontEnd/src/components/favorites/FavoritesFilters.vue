<script setup>
import { onMounted } from 'vue'
import { useFavoritesPageStore } from '@/stores/useFavoritesPageStore.js'
import { useAppStore } from '@/stores/useAppStore.js'
import ModelFilterPicker from '@/components/models/ModelFilterPicker.vue'
import Button from '@/components/ui/Button.vue'
import Label from '@/components/ui/Label.vue'
import SelectNative from '@/components/ui/SelectNative.vue'

const fav = useFavoritesPageStore()
const app = useAppStore()

function onLoraChange(name) {
  fav.filters.lora_name = name
  fav.filters.lora_weight = ''
}

onMounted(() => {
  if (app.healthOk && !app.modelLists.checkpoints.length) {
    app.loadModelLists().catch(() => {})
  }
})
</script>

<template>
  <div class="flex flex-wrap items-end gap-3 rounded-lg border border-border bg-card p-4">
    <div class="space-y-1">
      <Label class="text-xs">工作流</Label>
      <SelectNative v-model="fav.filters.workflow_id" class="min-w-[10rem] max-w-xs">
        <option value="">全部</option>
        <option v-for="w in fav.filterOptions.workflows" :key="w" :value="w">{{ w }}</option>
      </SelectNative>
    </div>

    <ModelFilterPicker
      v-model="fav.filters.checkpoint"
      folder="checkpoints"
      label="Checkpoint"
      :options="fav.filterOptions.checkpoints"
      :catalog="app.modelLists.checkpointCatalog"
      :loading="app.modelsLoading"
      trigger-class="min-w-[12rem]"
    />

    <ModelFilterPicker
      :model-value="fav.filters.lora_name"
      folder="loras"
      label="LoRA"
      :lora-rows="fav.filterOptions.loras"
      :catalog="app.modelLists.loraCatalog"
      :loading="app.modelsLoading"
      trigger-class="min-w-[12rem]"
      @update:model-value="onLoraChange"
    />

    <div v-if="fav.filters.lora_name" class="space-y-1">
      <Label class="text-xs">LoRA 权重</Label>
      <SelectNative v-model="fav.filters.lora_weight" class="min-w-[6rem]">
        <option value="">全部</option>
        <option
          v-for="w in fav.loraWeightsForName(fav.filters.lora_name)"
          :key="w"
          :value="String(w)"
        >
          {{ w }}
        </option>
      </SelectNative>
    </div>

    <Button variant="ghost" size="sm" :disabled="fav.loading" @click="fav.refresh">
      {{ fav.loading ? '加载中…' : '刷新' }}
    </Button>
    <Button variant="outline" size="sm" :disabled="fav.loading" @click="fav.resetFilters">
      重置
    </Button>
    <span class="text-[11px] text-muted-foreground pb-2 ml-auto">
      共 {{ fav.records.length }} 条收藏
    </span>
  </div>
</template>
