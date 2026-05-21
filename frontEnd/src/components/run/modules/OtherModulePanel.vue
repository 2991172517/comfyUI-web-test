<script setup>
import { computed } from 'vue'
import { useAppStore } from '@/stores/useAppStore.js'
import { otherNodeGroups } from '@/composables/useRunModules.js'
import Card from '@/components/ui/Card.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import CardTitle from '@/components/ui/CardTitle.vue'
import CardContent from '@/components/ui/CardContent.vue'
import Label from '@/components/ui/Label.vue'
import Input from '@/components/ui/Input.vue'
import Textarea from '@/components/ui/Textarea.vue'
import PromptTextarea from '@/components/prompt/PromptTextarea.vue'
import { isPromptTextField } from '@/lib/promptFormatValidate.js'

defineProps({ disabled: { type: Boolean, default: false } })

const app = useAppStore()
const groups = computed(() => otherNodeGroups(app.groupedNodes))
</script>

<template>
  <div class="space-y-6">
    <section v-for="[group, nodes] in groups" :key="group">
      <h3 class="text-sm font-medium text-muted-foreground mb-3">{{ group }}</h3>
      <div class="grid gap-4 md:grid-cols-2">
        <Card v-for="node in nodes" :key="node.id">
          <CardHeader class="pb-2">
            <CardTitle class="text-sm">{{ node.title }}</CardTitle>
          </CardHeader>
          <CardContent class="space-y-3">
            <div v-for="field in node.fields" :key="field.key" class="space-y-1">
              <Label class="text-xs">{{ field.label }}</Label>
              <PromptTextarea
                v-if="
                  field.type === 'string' &&
                  isPromptTextField(field) &&
                  String(app.fieldValue(node.id, field)).length > 30
                "
                :model-value="app.fieldValue(node.id, field)"
                :rows="4"
                :disabled="disabled"
                @update:model-value="app.updateField(node.id, field.key, $event)"
              />
              <Textarea
                v-else-if="field.type === 'string' && String(app.fieldValue(node.id, field)).length > 30"
                :model-value="app.fieldValue(node.id, field)"
                rows="2"
                :disabled="disabled"
                @update:model-value="app.updateField(node.id, field.key, $event)"
              />
              <Input
                v-else
                :type="field.type === 'integer' || field.type === 'number' ? 'number' : 'text'"
                :step="field.type === 'integer' ? 1 : 0.01"
                :model-value="app.fieldValue(node.id, field)"
                :disabled="disabled"
                @update:model-value="app.updateField(node.id, field.key, $event)"
              />
            </div>
          </CardContent>
        </Card>
      </div>
    </section>
    <p v-if="!groups.length" class="text-sm text-muted-foreground">无其他可编辑节点</p>
  </div>
</template>
