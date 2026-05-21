<script setup>
import { ref } from 'vue'
import { useAppStore } from '@/stores/useAppStore.js'
import { useBatchStore } from '@/stores/useBatchStore.js'
import { api } from '@/api/client.js'
import Label from '@/components/ui/Label.vue'
import Input from '@/components/ui/Input.vue'
import SelectNative from '@/components/ui/SelectNative.vue'
import Button from '@/components/ui/Button.vue'

defineProps({ disabled: { type: Boolean, default: false } })

const app = useAppStore()
const batch = useBatchStore()
const saveName = ref('')
const saveOpen = ref(false)
const saving = ref(false)

function openSave() {
  if (!batch.plannedTotal) {
    app.setMessage('请先配置扫参并确保计划张数 > 0', true)
    return
  }
  saveName.value = `${app.workflowMeta?.display_name || app.selectedId} · ${batch.plannedTotal}张`
  saveOpen.value = true
}

async function confirmSave() {
  if (!saveName.value.trim()) return
  saving.value = true
  try {
    const body = batch.buildBatchBody()
    await api.saveBatchTask({
      name: saveName.value.trim(),
      workflow_id: app.selectedId,
      workflow_display_name: app.workflowMeta?.display_name || app.selectedId,
      planned_total: batch.plannedTotal,
      batch_payload: body,
    })
    saveOpen.value = false
    app.setMessage('已保存为批量任务，可在任务计划中多选执行')
  } catch (e) {
    app.setMessage(e.message, true)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="rounded-lg border border-border bg-muted/30 p-4 space-y-4">
    <p class="text-sm font-medium">批量执行</p>
    <div class="grid gap-4 sm:grid-cols-3 max-w-3xl">
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
        <Input v-model.number="batch.form.seed" type="number" />
      </div>
      <label class="flex items-end gap-2 text-sm pb-2">
        <input v-model="batch.form.syncClip" type="checkbox" class="rounded border-input" />
        同步 strength_clip
      </label>
    </div>
    <div class="flex flex-wrap items-center gap-2">
      <Button variant="outline" :disabled="disabled || !batch.plannedTotal" @click="openSave">
        保存为任务
      </Button>
      <router-link to="/campaign" class="text-sm text-primary underline">任务计划 →</router-link>
      <p class="text-[11px] text-muted-foreground w-full sm:w-auto">
        预览与「开始批量」见页面底部悬浮栏
      </p>
    </div>

    <div v-if="saveOpen" class="rounded-md border border-dashed p-3 flex flex-wrap items-end gap-2 max-w-md">
      <div class="flex-1 space-y-1">
        <Label>任务名称</Label>
        <Input v-model="saveName" />
      </div>
      <Button size="sm" :disabled="saving" @click="confirmSave">保存</Button>
      <Button size="sm" variant="ghost" @click="saveOpen = false">取消</Button>
    </div>
  </div>
</template>
