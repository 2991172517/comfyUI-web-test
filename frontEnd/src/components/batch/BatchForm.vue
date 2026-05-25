<script setup>
import { ref, watch } from 'vue'
import AnimatedCollapse from '@/components/ui/AnimatedCollapse.vue'
import { useAppStore } from '@/stores/useAppStore.js'
import { isAdmin } from '@/composables/useAuth.js'
import { useBatchStore } from '@/stores/useBatchStore.js'
import { PARAM_HINTS } from '@/api/client.js'
import Card from '@/components/ui/Card.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import CardTitle from '@/components/ui/CardTitle.vue'
import CardContent from '@/components/ui/CardContent.vue'
import Label from '@/components/ui/Label.vue'
import Input from '@/components/ui/Input.vue'
import SelectNative from '@/components/ui/SelectNative.vue'
import Button from '@/components/ui/Button.vue'
import Alert from '@/components/ui/Alert.vue'
import BatchCheckpointSelect from '@/components/batch/BatchCheckpointSelect.vue'
import BatchLoraSweep from '@/components/batch/BatchLoraSweep.vue'
import BatchPromptPanel from '@/components/prompt/BatchPromptPanel.vue'

defineProps({ disabled: { type: Boolean, default: false } })

const app = useAppStore()
const batch = useBatchStore()
const hintsOpen = ref(false)

watch(
  () => [app.selectedId, app.workflowLoras],
  () => batch.applyDefaultStrategy(),
  { immediate: true, deep: true },
)
</script>

<template>
  <div class="space-y-4">
    <BatchCheckpointSelect :disabled="disabled || batch.isBatchRunning" />

    <Alert v-if="!batch.loras.length" variant="destructive">
      当前工作流没有 LoRA 节点，无法批量扫参。
    </Alert>

    <BatchLoraSweep v-else :disabled="disabled || batch.isBatchRunning" />

    <BatchPromptPanel :disabled="disabled || batch.isBatchRunning" />

    <Card>
      <CardHeader class="pb-2">
        <CardTitle class="text-base">全局选项</CardTitle>
      </CardHeader>
      <CardContent class="space-y-4">
        <div class="grid gap-4 sm:grid-cols-3">
          <div class="space-y-1.5">
            <Label>Seed 模式</Label>
            <SelectNative v-model="batch.form.seedMode">
              <option value="fixed">固定（便于对比）</option>
              <option value="increment">固定 + 递增</option>
              <option value="random">每张随机</option>
            </SelectNative>
          </div>
          <div v-if="batch.form.seedMode !== 'random'" class="space-y-1.5">
            <Label>基础 Seed</Label>
            <Input v-model.number="batch.form.seed" type="number" />
          </div>
          <label class="flex items-end gap-2 pb-2 text-sm">
            <input v-model="batch.form.syncClip" type="checkbox" class="rounded border-input" />
            扫参时同步 strength_clip
          </label>
        </div>
        <div class="space-y-1.5">
          <Label>文件命名模板</Label>
          <Input v-model="batch.form.filenameTemplate" class="font-mono text-xs" />
        </div>
        <div class="flex flex-wrap gap-2">
          <Button
            :disabled="disabled || batch.isBatchRunning || !batch.plannedTotal"
            @click="batch.startBatch"
          >
            开始批量（{{ batch.plannedTotal }} 张）
          </Button>
          <Button variant="secondary" :disabled="!batch.isBatchRunning" @click="batch.cancelBatch">
            取消
          </Button>
          <Button
            v-if="isAdmin()"
            variant="destructive"
            :disabled="!batch.batch.batchId"
            @click="batch.deleteBatch"
          >
            删除本批输出
          </Button>
        </div>
      </CardContent>
    </Card>

    <div class="rounded-lg border border-border bg-card px-4 py-3 text-sm">
      <button
        type="button"
        class="font-medium text-primary hover:underline"
        @click="hintsOpen = !hintsOpen"
      >
        {{ hintsOpen ? '收起' : '展开' }}参数说明
      </button>
      <AnimatedCollapse v-model="hintsOpen">
        <ul class="mt-3 space-y-2 text-muted-foreground">
          <li v-for="(h, i) in PARAM_HINTS" :key="i">
            <span class="font-medium text-foreground">{{ h.group }}</span> — {{ h.affects }}
          </li>
        </ul>
      </AnimatedCollapse>
    </div>
  </div>
</template>
