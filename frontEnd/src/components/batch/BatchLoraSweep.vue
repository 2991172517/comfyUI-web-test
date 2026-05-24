<script setup>
import { watch } from 'vue'
import { useAppStore } from '@/stores/useAppStore.js'
import { useBatchStore } from '@/stores/useBatchStore.js'
import Card from '@/components/ui/Card.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import CardTitle from '@/components/ui/CardTitle.vue'
import CardDescription from '@/components/ui/CardDescription.vue'
import CardContent from '@/components/ui/CardContent.vue'
import Label from '@/components/ui/Label.vue'
import Input from '@/components/ui/Input.vue'
import SelectNative from '@/components/ui/SelectNative.vue'
import Badge from '@/components/ui/Badge.vue'
import ModelSelectField from '@/components/models/ModelSelectField.vue'
import { cn } from '@/lib/utils'

defineProps({ disabled: { type: Boolean, default: false } })

const app = useAppStore()
const batch = useBatchStore()

watch(
  () => [app.selectedId, app.workflowLoras],
  () => batch.syncLoraAxisState(),
  { immediate: true, deep: true },
)

</script>

<template>
  <Card v-if="batch.loras.length">
    <CardHeader>
      <CardTitle class="text-base">工作流 LoRA（{{ batch.loras.length }}）</CardTitle>
      <CardDescription>
        默认固定权重；勾选「参与扫参」最多 2 个组成 A×B 网格（当前计划
        <strong>{{ batch.plannedTotal }}</strong> 张）
      </CardDescription>
    </CardHeader>
    <CardContent class="grid gap-4 grid-cols-[repeat(auto-fill,minmax(min(100%,280px),1fr))]">
      <article
        v-for="(l, chainIdx) in batch.loras"
        :key="l.node_id"
        :class="
          cn(
            'flex h-full min-w-0 flex-col gap-3 rounded-lg border p-4',
            batch.loraAxisState[l.node_id]?.enabled
              ? 'border-primary/50 bg-primary/5'
              : 'border-border',
          )
        "
      >
        <div class="flex flex-wrap items-center justify-between gap-2">
          <div>
            <span class="font-medium">#{{ l.node_id }} {{ l.short_name }}</span>
            <Badge variant="outline" class="ml-2 text-[10px]">链 {{ chainIdx + 1 }}</Badge>
            <Badge
              v-if="batch.loraAxisState[l.node_id]?.enabled"
              variant="default"
              class="ml-1 text-[10px]"
            >
              扫参 {{ batch.loraAxisState[l.node_id]?.sweepRole || '?' }}
            </Badge>
          </div>
          <label class="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              class="rounded border-input"
              :checked="batch.loraAxisState[l.node_id]?.enabled"
              :disabled="disabled"
              @change="batch.toggleLoraSweep(l.node_id, $event.target.checked)"
            />
            参与扫参
          </label>
        </div>

        <ModelSelectField
          label="LoRA 模型文件"
          folder="loras"
          :model-value="batch.loraAxisState[l.node_id]?.loraName || l.lora_name"
          :options="app.modelLists.loras"
          :missing-value="!(app.modelLists.loras || []).includes(batch.loraAxisState[l.node_id]?.loraName)"
          :disabled="disabled || app.modelsLoading"
          :loading="app.modelsLoading"
          preview-size="sm"
          @update:model-value="
            (v) => {
              batch.loraAxisState[l.node_id].loraName = v
              app.updateField(l.node_id, 'lora_name', v)
            }
          "
        />

        <template v-if="batch.loraAxisState[l.node_id]?.enabled">
          <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div class="space-y-1.5">
              <Label>起始</Label>
              <Input v-model.number="batch.loraAxisState[l.node_id].start" type="number" step="0.01" />
            </div>
            <div class="space-y-1.5">
              <Label>步进</Label>
              <Input v-model.number="batch.loraAxisState[l.node_id].step" type="number" step="0.01" min="0.01" />
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
          <div class="grid grid-cols-2 gap-3">
            <div class="space-y-1.5">
              <Label>strength_model（固定）</Label>
              <Input v-model.number="batch.loraAxisState[l.node_id].fixedModel" type="number" step="0.01" />
            </div>
            <div class="space-y-1.5">
              <Label>strength_clip（固定）</Label>
              <Input v-model.number="batch.loraAxisState[l.node_id].fixedClip" type="number" step="0.01" />
            </div>
          </div>
        </template>
      </article>
    </CardContent>
  </Card>
</template>
