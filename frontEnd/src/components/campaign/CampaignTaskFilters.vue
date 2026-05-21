<script setup>
import Label from '@/components/ui/Label.vue'
import Input from '@/components/ui/Input.vue'
import SelectNative from '@/components/ui/SelectNative.vue'
import Button from '@/components/ui/Button.vue'

const filters = defineModel('filters', {
  type: Object,
  required: true,
})

defineProps({
  workflowOptions: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  resultCount: { type: Number, default: 0 },
  totalCount: { type: Number, default: 0 },
})

const emit = defineEmits(['reset'])

const defaultFilters = () => ({
  search: '',
  status: '',
  workflow: '',
  hasPrompts: '',
  sort: 'created_desc',
})

function reset() {
  Object.assign(filters.value, defaultFilters())
  emit('reset')
}
</script>

<template>
  <div class="rounded-lg border border-border bg-card p-4 space-y-3">
    <div class="flex flex-wrap items-center justify-between gap-2">
      <p class="text-sm font-medium">筛选</p>
      <p class="text-[11px] text-muted-foreground">
        显示 <strong class="text-foreground">{{ resultCount }}</strong> / {{ totalCount }} 个任务
      </p>
    </div>
    <div class="flex flex-wrap items-end gap-3">
      <div class="space-y-1 flex-1 min-w-[12rem]">
        <Label class="text-xs">搜索</Label>
        <Input
          v-model="filters.search"
          placeholder="任务名、工作流、ID…"
          class="h-9"
          autocomplete="off"
        />
      </div>
      <div class="space-y-1">
        <Label class="text-xs">状态</Label>
        <SelectNative v-model="filters.status" class="min-w-[7.5rem]">
          <option value="">全部</option>
          <option value="pending">待执行</option>
          <option value="running">执行中</option>
          <option value="completed">已执行</option>
          <option value="failed">失败</option>
        </SelectNative>
      </div>
      <div class="space-y-1">
        <Label class="text-xs">工作流</Label>
        <SelectNative v-model="filters.workflow" class="min-w-[11rem] max-w-xs">
          <option value="">全部</option>
          <option v-for="w in workflowOptions" :key="w" :value="w">{{ w }}</option>
        </SelectNative>
      </div>
      <div class="space-y-1">
        <Label class="text-xs">提示词</Label>
        <SelectNative v-model="filters.hasPrompts" class="min-w-[6.5rem]">
          <option value="">不限</option>
          <option value="yes">含当次提示词</option>
          <option value="no">无附加提示词</option>
        </SelectNative>
      </div>
      <div class="space-y-1">
        <Label class="text-xs">排序</Label>
        <SelectNative v-model="filters.sort" class="min-w-[9rem]">
          <option value="created_desc">创建时间 ↓</option>
          <option value="created_asc">创建时间 ↑</option>
          <option value="planned_desc">计划张数 ↓</option>
          <option value="name_asc">名称 A→Z</option>
        </SelectNative>
      </div>
      <Button variant="outline" size="sm" :disabled="loading" @click="reset">重置</Button>
    </div>
  </div>
</template>
