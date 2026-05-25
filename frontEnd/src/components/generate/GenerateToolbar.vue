<script setup>
import { useAppStore } from '@/stores/useAppStore.js'
import Button from '@/components/ui/Button.vue'

const store = useAppStore()
</script>

<template>
  <div class="mb-4 flex flex-wrap gap-2">
    <Button
      variant="outline"
      :disabled="!store.healthOk || store.modelsLoading"
      @click="store.loadModelLists"
    >
      {{ store.modelsLoading ? '刷新模型…' : '刷新模型列表' }}
    </Button>
    <Button
      variant="secondary"
      :disabled="store.loading || !store.selectedId"
      @click="store.saveWorkflow"
    >
      保存参数
    </Button>
    <Button
      :disabled="store.loading || !store.selectedId || !store.healthOk || store.isGenerating"
      @click="store.queueWorkflow"
    >
      {{ store.isGenerating ? '生成中…' : '生成一张' }}
    </Button>
  </div>
</template>
