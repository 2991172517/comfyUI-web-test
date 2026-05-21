<script setup>
import { computed, onMounted } from 'vue'
import { useAppStore } from '@/stores/useAppStore.js'
import Card from '@/components/ui/Card.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import CardTitle from '@/components/ui/CardTitle.vue'
import CardDescription from '@/components/ui/CardDescription.vue'
import CardContent from '@/components/ui/CardContent.vue'
import Button from '@/components/ui/Button.vue'
import ModelVisualPicker from '@/components/models/ModelVisualPicker.vue'

defineProps({ disabled: { type: Boolean, default: false } })

const app = useAppStore()

const checkpointEntries = computed(() => {
  const items = []
  for (const node of app.state.nodes) {
    for (const field of node.fields) {
      if (app.isModelSelectField(field) && app.modelFolderForField(field) === 'checkpoints') {
        items.push({ nodeId: node.id, nodeTitle: node.title, field })
      }
    }
  }
  return items
})

onMounted(() => {
  if (app.healthOk) app.loadModelLists()
})
</script>

<template>
  <Card v-if="checkpointEntries.length">
    <CardHeader class="pb-2">
      <div class="flex flex-wrap items-center justify-between gap-2">
        <div>
          <CardTitle class="text-base">Checkpoint</CardTitle>
          <CardDescription>点击卡片选择底模，与单张生成共用</CardDescription>
        </div>
        <Button
          variant="outline"
          size="sm"
          :disabled="app.modelsLoading || !app.healthOk"
          @click="app.loadModelLists"
        >
          {{ app.modelsLoading ? '刷新中…' : '刷新列表' }}
        </Button>
      </div>
    </CardHeader>
    <CardContent class="space-y-6">
      <ModelVisualPicker
        v-for="entry in checkpointEntries"
        :key="entry.nodeId"
        folder="checkpoints"
        :label="`${entry.field.label}（#${entry.nodeId} ${entry.nodeTitle}）`"
        :model-value="String(app.fieldValue(entry.nodeId, entry.field))"
        :options="app.modelOptions(entry.field)"
        :catalog="app.modelCatalogForFolder('checkpoints')"
        :missing-value="app.modelSelectMissing(entry.nodeId, entry.field)"
        :disabled="disabled || app.modelsLoading || !app.healthOk"
        :loading="app.modelsLoading"
        @update:model-value="app.updateField(entry.nodeId, entry.field.key, $event)"
      />
    </CardContent>
  </Card>
</template>
