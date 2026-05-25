<script setup>
import { computed, onMounted } from 'vue'
import { useHistoryStore } from '@/stores/useHistoryStore.js'
import { useAppStore } from '@/stores/useAppStore.js'
import { isAdmin } from '@/composables/useAuth.js'
import { useConfirmDialog } from '@/composables/useConfirmDialog.js'
import ModelFilterPicker from '@/components/models/ModelFilterPicker.vue'
import Button from '@/components/ui/Button.vue'
import Label from '@/components/ui/Label.vue'
import SelectNative from '@/components/ui/SelectNative.vue'
import MediaCardLayoutControls from '@/components/shared/MediaCardLayoutControls.vue'

const history = useHistoryStore()
const app = useAppStore()
const { confirmDelete } = useConfirmDialog()

function onLoraChange(name) {
  history.filters.lora_name = name
  history.filters.lora_weight = ''
  history.filters.lora_node = ''
}

const selectedCount = computed(() => history.selectedKeys.size)

function apply() {
  history.refresh()
}

async function onBulkDelete() {
  const n = selectedCount.value
  if (!n) {
    app.setMessage('请先勾选要删除的记录', true)
    return
  }
  if (
    !(await confirmDelete({
      message: `确定删除已选 ${n} 条历史记录？相关图片文件将一并移除。`,
    }))
  )
    return
  try {
    const res = await history.deleteSelected()
    if (res.ok) app.setMessage(res.message)
    else app.setMessage(res.message, true)
  } catch (e) {
    app.setMessage(e.message, true)
  }
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

    <template v-if="isAdmin()">
      <span class="hidden sm:block w-px h-6 bg-border self-center" aria-hidden="true" />
      <Button
        :variant="history.bulkSelectMode ? 'default' : 'outline'"
        size="sm"
        :disabled="history.loading"
        @click="history.toggleBulkSelectMode()"
      >
        {{ history.bulkSelectMode ? '取消多选' : '多选' }}
      </Button>
      <template v-if="history.bulkSelectMode">
        <Button
          variant="outline"
          size="sm"
          :disabled="history.loading || !history.records.length"
          @click="history.selectAllVisible"
        >
          全选
        </Button>
        <Button
          variant="outline"
          size="sm"
          :disabled="!selectedCount"
          @click="history.clearBulkSelection"
        >
          取消勾选
        </Button>
        <Button
          variant="destructive"
          size="sm"
          :disabled="!selectedCount || history.bulkDeleting"
          @click="onBulkDelete"
        >
          {{ history.bulkDeleting ? '删除中…' : `删除选中${selectedCount ? ` (${selectedCount})` : ''}` }}
        </Button>
      </template>
    </template>

    <span class="hidden lg:block w-px h-6 bg-border self-center" aria-hidden="true" />

    <MediaCardLayoutControls class="w-full lg:w-auto lg:ml-auto" />
  </div>
</template>
