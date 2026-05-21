<script setup>
import { useAppStore } from '@/stores/useAppStore.js'
import Card from '@/components/ui/Card.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import CardTitle from '@/components/ui/CardTitle.vue'
import CardContent from '@/components/ui/CardContent.vue'
import Label from '@/components/ui/Label.vue'
import Input from '@/components/ui/Input.vue'
import Textarea from '@/components/ui/Textarea.vue'
import PromptTextarea from '@/components/prompt/PromptTextarea.vue'
import { isPromptTextField } from '@/lib/promptFormatValidate.js'
import ModelVisualPicker from '@/components/models/ModelVisualPicker.vue'

const store = useAppStore()
</script>

<template>
  <section v-for="[group, nodes] in store.groupedNodes" :key="group" class="mb-6">
    <h3 class="text-sm font-medium text-muted-foreground">{{ group }}</h3>
    <p class="mb-3 text-xs text-muted-foreground">{{ store.groupHint(group) }}</p>
    <div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
      <Card v-for="node in nodes" :key="node.id">
        <CardHeader class="pb-2">
          <CardTitle class="text-base">{{ node.title }}</CardTitle>
        </CardHeader>
        <CardContent class="space-y-3">
          <div v-for="field in node.fields" :key="field.key" class="space-y-1.5">
            <ModelVisualPicker
              v-if="store.isModelSelectField(field)"
              :label="field.label"
              :folder="store.modelFolderForField(field)"
              :model-value="String(store.fieldValue(node.id, field))"
              :options="store.modelOptions(field)"
              :catalog="store.modelCatalogForFolder(store.modelFolderForField(field))"
              :missing-value="store.modelSelectMissing(node.id, field)"
              :disabled="store.isGenerating || store.modelsLoading"
              :loading="store.modelsLoading"
              @update:model-value="store.updateField(node.id, field.key, $event)"
            />
            <template v-else>
              <Label>{{ field.label }}</Label>
              <PromptTextarea
                v-if="
                  field.type === 'string' &&
                  isPromptTextField(field) &&
                  String(store.fieldValue(node.id, field)).length > 40
                "
                :model-value="store.fieldValue(node.id, field)"
                :rows="5"
                :disabled="store.isGenerating"
                @update:model-value="store.updateField(node.id, field.key, $event)"
              />
              <Textarea
                v-else-if="field.type === 'string' && String(store.fieldValue(node.id, field)).length > 40"
                :model-value="store.fieldValue(node.id, field)"
                rows="3"
                :disabled="store.isGenerating"
                @update:model-value="store.updateField(node.id, field.key, $event)"
              />
              <Input
                v-else-if="field.type === 'string'"
                :model-value="store.fieldValue(node.id, field)"
                :disabled="store.isGenerating"
                @update:model-value="store.updateField(node.id, field.key, $event)"
              />
              <Input
                v-else-if="field.type === 'integer' || field.type === 'number'"
                type="number"
                :step="field.type === 'integer' ? 1 : 0.01"
                :model-value="store.fieldValue(node.id, field)"
                :disabled="store.isGenerating"
                @update:model-value="
                  store.updateField(
                    node.id,
                    field.key,
                    field.type === 'integer' ? parseInt($event, 10) : parseFloat($event),
                  )
                "
              />
              <Input
                v-else
                :model-value="store.fieldValue(node.id, field)"
                :disabled="store.isGenerating"
                @update:model-value="store.updateField(node.id, field.key, $event)"
              />
            </template>
          </div>
        </CardContent>
      </Card>
    </div>
  </section>
  <p v-if="store.selectedId && !store.state.nodes.length" class="text-sm text-muted-foreground">
    未匹配到可编辑节点，请检查 backEnd/editable_config.json
  </p>
</template>
